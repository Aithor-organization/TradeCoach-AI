"use client";

import { useState, useEffect } from "react";
import type { ParsedStrategy } from "@/lib/types";
import type { OptimizeResult } from "@/lib/api";
import PortalTooltip from "@/components/common/PortalTooltip";
import { runOptimization } from "@/lib/api";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";

interface OptimizeModalProps {
  strategy: ParsedStrategy;
  onClose: () => void;
  onApply: (params: Record<string, number>) => void;
}

// 인디케이터별 파라미터 최적화 범위
const INDICATOR_PARAM_RANGES: Record<string, Record<string, number[]>> = {
  "rsi": { "period": [9, 14, 21] },
  "stoch_rsi": { "rsi_period": [9, 14, 21] },
  "ma_cross": { "short_period": [5, 7, 12], "long_period": [20, 25, 50] },
  "ema_cross": { "short_period": [5, 7, 12], "long_period": [20, 25, 50] },
  "macd": { "fast_period": [8, 12, 16], "slow_period": [21, 26, 30] },
  "bollinger_lower": { "period": [14, 20, 30] },
  "bollinger_upper": { "period": [14, 20, 30] },
};

function buildDefaultRanges(_strategy: ParsedStrategy): Record<string, number[]> {
  // 기본: Leverage + TP + SL 3개만 (인디케이터 파라미터는 속도 문제로 제외)
  // 3 × 3 × 3 = 27 조합 → 빠른 최적화
  return {
    "leverage": [5, 10],
    "exit.take_profit.value": [1.5, 2.0, 3.0],
    "exit.stop_loss.value": [-0.3, -0.5, -0.8],
  };
}

// 파라미터별 설명
const PARAM_TIPS: Record<string, { ko: string; en: string }> = {
  "leverage": {
    ko: "레버리지 배율. 5x=보수적, 10x=중립, 20x=공격적. 높을수록 수익/손실이 비례 증가",
    en: "Leverage multiplier. 5x=conservative, 10x=neutral, 20x=aggressive. Higher = proportionally more profit/loss",
  },
  "exit.take_profit.value": {
    ko: "익절 비율(%). 목표 수익에 도달하면 자동 청산. 예: 2.0 = 2% 수익 시 익절",
    en: "Take profit ratio (%). Auto-close at target profit. e.g. 2.0 = close at 2% profit",
  },
  "exit.stop_loss.value": {
    ko: "손절 비율(%, 음수). 손실 한도에 도달하면 자동 청산. 예: -0.5 = 0.5% 손실 시 손절",
    en: "Stop loss ratio (%, negative). Auto-close at loss limit. e.g. -0.5 = close at 0.5% loss",
  },
  "indicators.rsi.period": {
    ko: "RSI 계산 기간. 9=민감, 14=표준, 21=완만",
    en: "RSI calculation period. 9=sensitive, 14=standard, 21=smooth",
  },
  "indicators.ma_cross.short_period": {
    ko: "단기 이동평균 기간. 짧을수록 빠른 반응",
    en: "Short MA period. Shorter = faster response",
  },
  "indicators.ma_cross.long_period": {
    ko: "장기 이동평균 기간. 길수록 추세 확인",
    en: "Long MA period. Longer = trend confirmation",
  },
  "indicators.ema_cross.short_period": {
    ko: "단기 EMA 기간. 짧을수록 빠른 반응",
    en: "Short EMA period. Shorter = faster response",
  },
  "indicators.ema_cross.long_period": {
    ko: "장기 EMA 기간. 길수록 추세 확인",
    en: "Long EMA period. Longer = trend confirmation",
  },
  "indicators.bollinger_lower.period": {
    ko: "볼린저밴드 기간. 짧을수록 민감, 길수록 안정",
    en: "Bollinger period. Shorter = sensitive, longer = stable",
  },
  "indicators.macd.fast_period": {
    ko: "MACD 빠른 기간. 표준: 12",
    en: "MACD fast period. Standard: 12",
  },
};

const OBJECTIVE_TIPS: Record<string, { ko: string; en: string }> = {
  sharpe: {
    ko: "위험 대비 수익률. 높을수록 같은 리스크로 더 많이 벌음. 1.0+ 양호, 1.5+ 우수",
    en: "Risk-adjusted return. Higher = more profit per risk. 1.0+ good, 1.5+ excellent",
  },
  calmar: {
    ko: "연수익률 / 최대낙폭. 높을수록 MDD 대비 수익이 좋음. 1.0+ 적정, 2.0+ 우수",
    en: "Annual return / Max drawdown. Higher = better return vs drawdown. 1.0+ ok, 2.0+ excellent",
  },
  profit_factor: {
    ko: "총수익 / 총손실. 1.5+ 양호, 2.0+ 우수. 1.0 미만이면 손실이 더 큼",
    en: "Total profit / Total loss. 1.5+ good, 2.0+ excellent. Below 1.0 = net loss",
  },
  total_return: {
    ko: "단순 총 수익률(%). 가장 직관적이지만 리스크를 고려하지 않음",
    en: "Simple total return (%). Most intuitive but doesn't account for risk",
  },
};

function Tip({ text }: { text: string }) {
  return <PortalTooltip text={text} />;
}

export default function OptimizeModal({ strategy, onClose, onApply }: OptimizeModalProps) {
  const { language } = useLanguageStore();
  const [ranges, setRanges] = useState(() => buildDefaultRanges(strategy));
  const [objective, setObjective] = useState("sharpe");
  const [maxCombinations, setMaxCombinations] = useState(100);
  const [results, setResults] = useState<OptimizeResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [tested, setTested] = useState(0);

  // 최적화 중 새로고침 방지
  useEffect(() => {
    if (!loading) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [loading]);

  const handleRun = async () => {
    setLoading(true);
    try {
      const res = await runOptimization(
        strategy as unknown as Record<string, unknown>,
        ranges, objective, maxCombinations,
      );
      setResults(res.results || []);
      setTested(res.total_tested || 0);
    } catch (e) {
      console.error("Optimization error:", e);
      setResults([]); setTested(0);
    } finally {
      setLoading(false);
    }
  };

  const updateRange = (key: string, value: string) => {
    const nums = value.split(",").map(v => parseFloat(v.trim())).filter(v => !isNaN(v));
    setRanges(prev => ({ ...prev, [key]: nums }));
  };

  const tip = (key: string) => {
    const t = PARAM_TIPS[key];
    return t ? t[language === "ko" ? "ko" : "en"] : "";
  };

  const objTip = OBJECTIVE_TIPS[objective]?.[language === "ko" ? "ko" : "en"] || "";

  // 파라미터 키를 읽기 쉽게 변환
  const displayKey = (key: string) => {
    const map: Record<string, string> = {
      "leverage": "Leverage",
      "exit.take_profit.value": "Take Profit (%)",
      "exit.stop_loss.value": "Stop Loss (%)",
      "indicators.rsi.period": "RSI Period",
      "indicators.stoch_rsi.rsi_period": "StochRSI Period",
      "indicators.ma_cross.short_period": "MA Short",
      "indicators.ma_cross.long_period": "MA Long",
      "indicators.ema_cross.short_period": "EMA Short",
      "indicators.ema_cross.long_period": "EMA Long",
      "indicators.macd.fast_period": "MACD Fast",
      "indicators.macd.slow_period": "MACD Slow",
      "indicators.bollinger_lower.period": "BB Period",
      "indicators.bollinger_upper.period": "BB Period",
    };
    return map[key] || key.split(".").pop() || key;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        {/* 헤더 */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-[#0F172A]">
          <div className="flex items-center gap-1">
            <span className="font-semibold text-white text-sm">{t("opt.title", language)}</span>
            <Tip text={language === "ko"
              ? "여러 파라미터 조합을 자동 백테스트하여 최적의 설정을 찾습니다. 범위를 지정하고 Run을 누르세요."
              : "Automatically backtests multiple parameter combinations to find optimal settings. Set ranges and click Run."
            } />
          </div>
          <button onClick={() => !loading && onClose()} disabled={loading} className={`text-[#475569] hover:text-white text-lg cursor-pointer ${loading ? "opacity-30 cursor-not-allowed" : ""}`}>&times;</button>
        </div>

        {!results ? (
          <div className="px-5 py-4 space-y-4">
            {/* 파라미터 범위 */}
            {Object.entries(ranges).map(([key, vals]) => (
              <div key={key}>
                <div className="flex items-center mb-1">
                  <label className="text-xs text-[#475569]">{displayKey(key)}</label>
                  {tip(key) && <Tip text={tip(key)} />}
                </div>
                <input
                  type="text"
                  value={vals.join(", ")}
                  onChange={e => updateRange(key, e.target.value)}
                  className="w-full bg-[#0F172A] text-white text-sm font-mono rounded-lg px-3 py-2 border border-[#47556933] focus:border-[#22D3EE50] focus:outline-none"
                />
              </div>
            ))}

            {/* 목적 함수 */}
            <div>
              <div className="flex items-center mb-1">
                <label className="text-xs text-[#475569]">Objective</label>
                <Tip text={objTip} />
              </div>
              <select
                value={objective}
                onChange={e => setObjective(e.target.value)}
                className="w-full bg-[#0F172A] text-white text-sm rounded-lg px-3 py-2 border border-[#47556933] focus:outline-none"
              >
                <option value="sharpe">Sharpe Ratio</option>
                <option value="calmar">Calmar Ratio</option>
                <option value="profit_factor">Profit Factor</option>
                <option value="total_return">Total Return</option>
              </select>
            </div>

            {/* Max combinations */}
            <div>
              <div className="flex items-center mb-1">
                <label className="text-xs text-[#475569]">Max Combinations</label>
                <Tip text={language === "ko"
                  ? "테스트할 최대 조합 수. 많을수록 정확하지만 시간이 오래 걸립니다. 기본 100."
                  : "Maximum combinations to test. More = accurate but slower. Default 100."
                } />
              </div>
              <input
                type="number"
                value={maxCombinations}
                onChange={e => setMaxCombinations(Number(e.target.value))}
                min={10} max={1000}
                className="w-full bg-[#0F172A] text-white text-sm font-mono rounded-lg px-3 py-2 border border-[#47556933] focus:outline-none"
              />
            </div>

            {/* 버튼 */}
            <div className="flex gap-2 pt-2">
              <button onClick={onClose} className="flex-1 py-2 text-xs font-semibold rounded-lg bg-[#0F172A] text-[#94A3B8] border border-[#22D3EE20] cursor-pointer">
                Cancel
              </button>
              <button onClick={handleRun} disabled={loading}
                className="flex-1 py-2 text-xs font-semibold rounded-lg gradient-accent text-[#0A0F1C] cursor-pointer disabled:opacity-50">
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                    {t("opt.testing", language)}
                  </span>
                ) : t("opt.run", language)}
              </button>
            </div>
          </div>
        ) : (
          <div className="px-5 py-4">
            <p className="text-xs text-[#475569] mb-3">
              {t("opt.tested", language)}: {tested} | Top {results.length}
            </p>

            {results.length === 0 ? (
              <div className="text-center py-6 space-y-2">
                <p className="text-sm text-[#94A3B8]">{language === "ko" ? "유효한 결과가 없습니다" : "No valid results"}</p>
                <p className="text-[10px] text-[#475569]">
                  {language === "ko"
                    ? "파라미터 범위를 넓히거나 다른 목적 함수를 시도하세요"
                    : "Try wider parameter ranges or a different objective"}
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-[#475569] border-b border-[#0F172A]">
                      <th className="py-2 text-left">#</th>
                      {results[0] && Object.keys(results[0].params).map(k => (
                        <th key={k} className="py-2 text-right">{displayKey(k)}</th>
                      ))}
                      <th className="py-2 text-right">Sharpe</th>
                      <th className="py-2 text-right">Return</th>
                      <th className="py-2 text-center">Apply</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((r, i) => (
                      <tr key={i} className="border-b border-[#0F172A]/50 text-[#94A3B8]">
                        <td className="py-2 text-[#22D3EE]">{i + 1}</td>
                        {Object.values(r.params).map((v, j) => (
                          <td key={j} className="py-2 text-right font-mono">{v}</td>
                        ))}
                        <td className="py-2 text-right font-mono">{r.metrics.sharpe_ratio?.toFixed(2)}</td>
                        <td className={`py-2 text-right font-mono ${(r.metrics.total_return ?? 0) >= 0 ? "text-[#22C55E]" : "text-[#EF4444]"}`}>
                          {r.metrics.total_return?.toFixed(1)}%
                        </td>
                        <td className="py-2 text-center">
                          <button onClick={() => onApply(r.params)}
                            className="text-[#22D3EE] hover:underline cursor-pointer">
                            Apply
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* 성능 경고: 최상위 결과가 Return < 0% 또는 Sharpe < 0.5 */}
            {results.length > 0 && (results[0].metrics.total_return ?? 0) < 0 && (
              <div className="mt-3 bg-[#EF4444]/10 border border-[#EF4444]/20 rounded-lg px-4 py-3">
                <div className="flex items-start gap-2">
                  <span className="text-[#EF4444] text-sm mt-0.5">!</span>
                  <div className="text-[10px]">
                    <p className="text-[#EF4444] font-semibold mb-1">
                      {language === "ko"
                        ? "모든 파라미터 조합이 손실입니다"
                        : "All parameter combinations result in losses"}
                    </p>
                    <p className="text-[#94A3B8] mb-2">
                      {language === "ko"
                        ? "파라미터 조정만으로는 수익을 낼 수 없습니다. 전략의 진입 조건 자체를 수정해야 합니다."
                        : "Parameter tuning alone cannot produce profit. The entry conditions need to be redesigned."}
                    </p>
                    <p className="text-[#F59E0B]">
                      {language === "ko"
                        ? "AI 코치에게 \"진입 조건을 개선해줘\" 또는 \"다른 지표 조합으로 바꿔줘\"라고 요청하세요."
                        : "Ask the AI Coach: \"Improve entry conditions\" or \"Try a different indicator combination\"."}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {results.length > 0 && (results[0].metrics.total_return ?? 0) >= 0 && (results[0].metrics.sharpe_ratio ?? 0) < 0.5 && (
              <div className="mt-3 bg-[#F59E0B]/10 border border-[#F59E0B]/20 rounded-lg px-4 py-3">
                <div className="flex items-start gap-2">
                  <span className="text-[#F59E0B] text-sm mt-0.5">!</span>
                  <div className="text-[10px]">
                    <p className="text-[#F59E0B] font-semibold mb-1">
                      {language === "ko"
                        ? "Sharpe 비율이 낮습니다 (< 0.5)"
                        : "Low Sharpe Ratio (< 0.5)"}
                    </p>
                    <p className="text-[#94A3B8]">
                      {language === "ko"
                        ? "수익은 나지만 위험 대비 수익률이 낮습니다. AI 코치에게 리스크를 줄이는 조건을 추가하도록 요청하세요."
                        : "Profitable but risk-adjusted return is low. Ask AI Coach to add risk-reducing conditions."}
                    </p>
                  </div>
                </div>
              </div>
            )}

            <button onClick={() => setResults(null)}
              className="mt-3 w-full py-2 text-xs font-semibold rounded-lg bg-[#0F172A] text-[#94A3B8] border border-[#22D3EE20] cursor-pointer">
              {t("opt.rerun", language)}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
