"""
Grid Search 파라미터 최적화 엔진.

전략 파라미터(레버리지, TP/SL, 지표 파라미터)의 데카르트 곱 조합을
ThreadPoolExecutor로 병렬 백테스트하고 상위 N개 결과를 반환한다.
"""

import copy
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import islice, product
from typing import Any, Dict, List, Optional

from .data_loader import OhlcvBar
from .engine import FuturesBacktestEngine
from .types import FuturesConfig

logger = logging.getLogger(__name__)

# 목적 함수 이름 → BacktestMetrics 필드 매핑 ("_composite"는 가중 복합 점수)
_OBJECTIVE_MAP: Dict[str, str] = {
    "sharpe": "sharpe_ratio",
    "calmar": "calmar_ratio",
    "profit_factor": "profit_factor",
    "total_return": "total_return",
    "composite": "_composite",
}

# 복합 점수 가중치: Sharpe 50% + Calmar 30% + Profit Factor 20%
_COMPOSITE_WEIGHTS = {"sharpe_ratio": 0.50, "calmar_ratio": 0.30, "profit_factor": 0.20}


def _apply_overrides(strategy: dict, overrides: Dict[str, Any]) -> dict:
    """
    전략 딕셔너리에 파라미터 오버라이드를 적용한다 (deepcopy 후 반환).

    키 형식:
      "leverage"                   → strategy["leverage"]
      "exit.take_profit.value"     → strategy["exit"]["take_profit"]["value"]
      "indicators.<name>.<field>"  → 해당 인디케이터의 params[<field>]
    """
    result = copy.deepcopy(strategy)
    for key, value in overrides.items():
        parts = key.split(".")
        if len(parts) == 1:
            result[parts[0]] = value
            continue
        if parts[0] == "indicators" and len(parts) >= 3:
            # indicators.<indicator_name>.<param_field>
            for ind in result.get("indicators", []):
                if ind.get("name") == parts[1] or ind.get("type") == parts[1]:
                    ind.setdefault("params", {})[".".join(parts[2:])] = value
            continue
        # 일반 중첩 경로 (exit.take_profit.value 등)
        node = result
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return result


def _score(metrics: dict, objective: str) -> float:
    """목적 함수 점수를 계산한다. 거래 없는 결과는 -inf로 처리."""
    if metrics.get("total_trades", 0) < 1:
        return float("-inf")
    if objective == "_composite":
        return sum(
            w * min(metrics.get(f, 0.0), 10.0)  # profit_factor 무한대 보정
            for f, w in _COMPOSITE_WEIGHTS.items()
        )
    raw = metrics.get(objective, float("-inf"))
    return min(float(raw), 10.0) if raw == float("inf") else float(raw)


def _run_one(
    strategy: dict, overrides: Dict[str, Any], bars: List[OhlcvBar], objective: str
) -> Optional[Dict[str, Any]]:
    """단일 파라미터 조합 백테스트. 예외 시 None 반환."""
    try:
        modified = _apply_overrides(strategy, overrides)
        config = FuturesConfig.from_strategy_json(modified)
        metrics = FuturesBacktestEngine(config).run(bars, modified).to_dict()
        return {"params": overrides, "score": _score(metrics, objective), "metrics": metrics}
    except Exception as exc:  # pylint: disable=broad-except
        logger.debug("조합 실패 %s: %s", overrides, exc)
        return None


def run_grid_search(
    strategy: Dict[str, Any],
    param_ranges: Dict[str, List[Any]],
    bars: List[OhlcvBar],
    objective: str = "composite",
    max_combinations: int = 200,
    top_n: int = 10,
    max_workers: int = 0,
) -> List[Dict[str, Any]]:
    """
    Grid Search 파라미터 최적화를 실행한다.

    Args:
        strategy:        기본 전략 딕셔너리 (내부에서 deepcopy, 원본 불변)
        param_ranges:    파라미터 이름 → 탐색 값 목록 매핑
        bars:            백테스트용 OHLCV 데이터
        objective:       최적화 기준
        max_combinations: 탐색 최대 조합 수
        top_n:           반환할 상위 결과 수
        max_workers:     병렬 스레드 수
    """
    if not param_ranges:
        raise ValueError("param_ranges가 비어 있습니다.")
    if not bars:
        raise ValueError("bars 데이터가 없습니다.")

    obj_key = objective.lower()
    if obj_key not in _OBJECTIVE_MAP:
        raise ValueError(
            f"지원하지 않는 objective '{objective}'. 사용 가능: {list(_OBJECTIVE_MAP)}"
        )
    resolved_obj = _OBJECTIVE_MAP[obj_key]

    keys = list(param_ranges.keys())
    combos: List[Dict[str, Any]] = [
        dict(zip(keys, combo))
        for combo in islice(product(*[param_ranges[k] for k in keys]), max_combinations)
    ]
    logger.info("파라미터 조합 %d개 생성 (max=%d)", len(combos), max_combinations)

    if not combos:
        return []

    return _parallel_evaluate(strategy, combos, bars, resolved_obj, top_n, max_workers)


def run_random_search(
    strategy: Dict[str, Any],
    param_ranges: Dict[str, List[Any]],
    bars: List[OhlcvBar],
    objective: str = "composite",
    max_combinations: int = 80,
    top_n: int = 10,
    max_workers: int = 0,
    patience: int = 30,
) -> List[Dict[str, Any]]:
    """
    Random Search + Early Stopping 파라미터 최적화.

    Grid Search보다 같은 예산으로 더 넓은 탐색 공간을 커버한다.
    patience 조합 연속으로 최고 점수 개선이 없으면 조기 종료한다.

    Args:
        patience: 개선 없이 허용되는 연속 조합 수 (기본 30)
    """
    import random

    if not param_ranges:
        raise ValueError("param_ranges가 비어 있습니다.")
    if not bars:
        raise ValueError("bars 데이터가 없습니다.")

    obj_key = objective.lower()
    if obj_key not in _OBJECTIVE_MAP:
        raise ValueError(
            f"지원하지 않는 objective '{objective}'. 사용 가능: {list(_OBJECTIVE_MAP)}"
        )
    resolved_obj = _OBJECTIVE_MAP[obj_key]

    # 전체 조합 수 계산
    keys = list(param_ranges.keys())
    total_possible = 1
    for v in param_ranges.values():
        if isinstance(v, list):
            total_possible *= len(v)

    # 전체 조합이 max_combinations 이하면 그냥 grid search
    if total_possible <= max_combinations:
        logger.info("전체 조합(%d) <= 예산(%d): Grid Search로 전환", total_possible, max_combinations)
        return run_grid_search(
            strategy=strategy, param_ranges=param_ranges, bars=bars,
            objective=objective, max_combinations=total_possible,
            top_n=top_n, max_workers=max_workers,
        )

    # 랜덤 샘플링 (중복 제거)
    all_values = [param_ranges[k] for k in keys]
    seen = set()
    combos: List[Dict[str, Any]] = []
    attempts = 0
    max_attempts = max_combinations * 3  # 중복 방지를 위한 여유

    while len(combos) < max_combinations and attempts < max_attempts:
        combo_tuple = tuple(random.choice(vals) for vals in all_values)
        if combo_tuple not in seen:
            seen.add(combo_tuple)
            combos.append(dict(zip(keys, combo_tuple)))
        attempts += 1

    logger.info(
        "Random Search: %d개 샘플 (전체 가능: %d, patience=%d)",
        len(combos), total_possible, patience,
    )

    if not combos:
        return []

    # 배치 단위로 실행 + Early Stopping
    batch_size = min(20, len(combos))
    all_results: List[Dict[str, Any]] = []
    best_score = float("-inf")
    no_improve_count = 0

    for batch_start in range(0, len(combos), batch_size):
        batch = combos[batch_start:batch_start + batch_size]
        batch_results = _parallel_evaluate(
            strategy, batch, bars, resolved_obj, top_n=len(batch), max_workers=max_workers,
        )
        all_results.extend(batch_results)

        # 현재 배치 최고 점수 확인
        batch_best = max((r["score"] for r in batch_results), default=float("-inf"))
        if batch_best > best_score:
            best_score = batch_best
            no_improve_count = 0
        else:
            no_improve_count += len(batch)

        tested = batch_start + len(batch)
        logger.info(
            "Random Search 진행: %d/%d 완료, 최고=%.4f, 연속미개선=%d",
            tested, len(combos), best_score, no_improve_count,
        )

        # Early Stopping
        if no_improve_count >= patience:
            logger.info(
                "Early Stopping: %d개 연속 미개선 (patience=%d). %d/%d에서 중단.",
                no_improve_count, patience, tested, len(combos),
            )
            break

    # 정렬 후 상위 N개
    all_results.sort(key=lambda r: r["score"], reverse=True)
    return [
        {
            "rank": idx + 1,
            "score": round(entry["score"], 6),
            "params": entry["params"],
            "metrics": entry["metrics"],
        }
        for idx, entry in enumerate(all_results[:top_n])
    ]


def _parallel_evaluate(
    strategy: dict,
    combos: List[Dict[str, Any]],
    bars: List[OhlcvBar],
    resolved_obj: str,
    top_n: int,
    max_workers: int = 0,
) -> List[Dict[str, Any]]:
    """조합 목록을 병렬로 백테스트하고 상위 결과 반환."""
    import os
    effective_workers = max_workers if max_workers > 0 else min(os.cpu_count() or 4, 8)
    results: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=effective_workers) as pool:
        futures = {
            pool.submit(_run_one, strategy, combo, bars, resolved_obj): combo
            for combo in combos
        }
        for done, fut in enumerate(as_completed(futures), start=1):
            result = fut.result()
            if result is not None and result["score"] != float("-inf"):
                results.append(result)
            if done % 50 == 0:
                logger.info("진행: %d/%d 완료, 유효 %d개", done, len(combos), len(results))

    results.sort(key=lambda r: r["score"], reverse=True)
    return [
        {
            "rank": idx + 1,
            "score": round(entry["score"], 6),
            "params": entry["params"],
            "metrics": entry["metrics"],
        }
        for idx, entry in enumerate(results[:top_n])
    ]


# 라우터 호환 별칭
def run_optimization(
    bars: list,
    strategy: dict,
    param_ranges: dict,
    objective: str = "sharpe",
    max_combinations: int = 80,
    top_n: int = 10,
    search_method: str = "random",
) -> list:
    """최적화 진입점. search_method로 grid/random 선택."""
    if search_method == "grid":
        return run_grid_search(
            strategy=strategy, param_ranges=param_ranges, bars=bars,
            objective=objective, max_combinations=max_combinations, top_n=top_n,
        )
    return run_random_search(
        strategy=strategy, param_ranges=param_ranges, bars=bars,
        objective=objective, max_combinations=max_combinations, top_n=top_n,
    )
