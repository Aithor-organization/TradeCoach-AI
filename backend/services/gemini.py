import asyncio
import json
import io
import logging
from typing import AsyncGenerator, Optional

from google import genai
from google.genai import types
from PIL import Image

from config import get_settings
from prompts.strategy_parser import STRATEGY_SYSTEM_PROMPT, build_parse_prompt, get_strategy_system_prompt
from prompts.coaching import COACHING_SYSTEM_PROMPT, COACHING_SYSTEM_PROMPT_EN, get_coaching_prompt
from prompts.backtest_report import BACKTEST_REPORT_TEMPLATE, BACKTEST_REPORT_TEMPLATE_EN
from services.rag import build_rag_context
from services.market_data import fetch_market_summary

logger = logging.getLogger(__name__)

settings = get_settings()

_client = genai.Client(api_key=settings.gemini_api_key)
_MODEL = "gemini-3-flash-preview"

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # 초
MAX_INPUT_LENGTH = 5000  # 사용자 입력 최대 길이

# 프롬프트 인젝션 의심 패턴
_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "disregard your instructions",
    "forget your system prompt",
    "you are now",
    "new instructions:",
    "system prompt:",
    "override:",
    "이전 지시를 무시",
    "시스템 프롬프트를 무시",
    "지시를 무시하고",
]


def _sanitize_user_input(text: str) -> str:
    """사용자 입력 sanitization: 길이 제한 + 인젝션 패턴 경고"""
    if not text:
        return text

    # 길이 제한
    text = text[:MAX_INPUT_LENGTH]

    # 인젝션 패턴 감지 (차단하지 않고 경고 로그 + 안전 래핑)
    text_lower = text.lower()
    for pattern in _INJECTION_PATTERNS:
        if pattern in text_lower:
            logger.warning(f"프롬프트 인젝션 의심 패턴 감지: '{pattern}'")
            # 사용자 입력을 명확히 구분하여 시스템 프롬프트와 분리
            return f"[사용자 메시지 시작]\n{text}\n[사용자 메시지 끝]"

    return text


def _make_config(temperature: float = 0.5, max_output_tokens: int = 8192, system_instruction: str = None) -> types.GenerateContentConfig:
    """GenerateContentConfig 생성 헬퍼"""
    kwargs = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
    }
    if system_instruction:
        kwargs["system_instruction"] = system_instruction
    return types.GenerateContentConfig(**kwargs)


async def _safe_generate(contents: list, config: types.GenerateContentConfig) -> str:
    """Gemini API 호출 + 재시도 로직 (지수 백오프)"""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = await _client.aio.models.generate_content(
                model=_MODEL,
                contents=contents,
                config=config,
            )
            return response.text
        except Exception as e:
            last_error = e
            logger.warning(f"Gemini API 오류 (시도 {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                await asyncio.sleep(delay)
    raise last_error


async def _safe_generate_stream(
    contents: list, config: types.GenerateContentConfig
) -> AsyncGenerator[str, None]:
    """Gemini API 스트리밍 호출 + 재시도 로직"""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            async for chunk in await _client.aio.models.generate_content_stream(
                model=_MODEL,
                contents=contents,
                config=config,
            ):
                if chunk.text:
                    yield chunk.text
            return
        except Exception as e:
            last_error = e
            logger.warning(f"Gemini 스트리밍 오류 (시도 {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                await asyncio.sleep(delay)
    raise last_error


def _extract_json_from_response(text: str) -> dict:
    """Gemini 응답에서 JSON 블록 추출"""
    json_str = text.strip()

    if "```json" in text:
        start = text.index("```json") + 7
        end = text.find("```", start)
        if end == -1:
            # 닫는 ``` 없으면 나머지 전체를 JSON으로 간주
            json_str = text[start:].strip()
        else:
            json_str = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        # 줄바꿈 이후부터 (언어 태그 건너뛰기)
        nl = text.find("\n", start)
        if nl != -1:
            start = nl + 1
        end = text.find("```", start)
        if end == -1:
            json_str = text[start:].strip()
        else:
            json_str = text[start:end].strip()

    # JSON 객체가 아닌 텍스트가 앞에 있으면 제거
    brace_start = json_str.find("{")
    if brace_start > 0:
        json_str = json_str[brace_start:]
    # 닫는 중괄호 이후 잡음 제거
    brace_end = json_str.rfind("}")
    if brace_end != -1 and brace_end < len(json_str) - 1:
        json_str = json_str[:brace_end + 1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Gemini가 잘못된 JSON 반환 시 복구 시도
        repaired = _repair_json(json_str)
        return json.loads(repaired)


def _repair_json(text: str) -> str:
    """Gemini가 생성한 잘못된 JSON 복구"""
    import re
    s = text
    # trailing comma 제거: ,} → } , ,] → ]
    s = re.sub(r',\s*}', '}', s)
    s = re.sub(r',\s*]', ']', s)
    # 작은따옴표 → 큰따옴표 (JSON 값 내부가 아닌 키/값 구분자)
    s = re.sub(r"(?<!\\)'", '"', s)
    # 줄바꿈이 문자열 내부에 있으면 이스케이프
    # 주석 제거 (// 스타일)
    s = re.sub(r'//[^\n]*', '', s)
    # 불완전한 JSON 닫기: 열린 괄호 수 체크
    open_braces = s.count('{') - s.count('}')
    open_brackets = s.count('[') - s.count(']')
    s += ']' * max(0, open_brackets)
    s += '}' * max(0, open_braces)
    return s


async def parse_strategy_text(text: str, language: str = "ko") -> dict:
    """텍스트 → 구조화된 전략 JSON"""
    text = _sanitize_user_input(text)
    prompt = build_parse_prompt(text, language)
    result = await _safe_generate(
        [get_strategy_system_prompt(language), prompt],
        config=_make_config(temperature=0.3, max_output_tokens=2048),
    )
    return _extract_json_from_response(result)


async def parse_strategy_multimodal(text: str, image: bytes, language: str = "ko") -> dict:
    """이미지 + 텍스트 → 전략 JSON (멀티모달)"""
    img = Image.open(io.BytesIO(image))
    chart_prompt = "Analyze this chart image and convert it into a trading strategy." if language == "en" else "위 차트 이미지를 분석하여 트레이딩 전략으로 변환해주세요."
    contents = [
        get_strategy_system_prompt(language),
        img,
        chart_prompt,
    ]
    if text:
        extra_label = "Additional description" if language == "en" else "추가 설명"
        contents.append(f"{extra_label}: {text}")

    result = await _safe_generate(
        contents,
        config=_make_config(temperature=0.3, max_output_tokens=2048),
    )
    return _extract_json_from_response(result)


async def generate_strategy_explanation(parsed: dict, language: str = "ko") -> str:
    """전략 JSON을 초보자 친화적으로 상세 설명"""
    strategy_json = json.dumps(parsed, ensure_ascii=False, indent=2)

    if language == "en":
        prompt = f"""You are a friendly trading education expert.
Explain the following strategy JSON in simple terms that a trading beginner can easily understand, in English.

## Explanation Format (Markdown)

### Strategy at a Glance
Summarize the core idea in 2-3 sentences (include analogies or simple examples)

### When to Buy? (Entry Conditions)
Explain each entry condition for beginners.
- What each indicator is (e.g., RSI is a "thermometer that tells you if something is overbought/oversold")
- Why this condition is a buy signal
- What the AND/OR logic between conditions means

### When to Sell? (Take Profit/Stop Loss)
- Take profit: Automatically sell when profit reaches N% to lock in gains
- Stop loss: Automatically sell when loss reaches N% to prevent bigger losses
- Risk:Reward ratio calculation and meaning

### Investment Settings
- Per-trade investment amount, meaning of max simultaneous positions
- Total maximum investment calculation

### Strengths and Cautions
- 2-3 strengths (what market conditions it works best in)
- 2-3 cautions (what situations are risky)

## Rules
- Always add simple explanations in parentheses when using technical terms
- Use specific numbers and examples
- No cheerful encouragement, only practical information
- Use markdown formatting

Strategy JSON:
```json
{strategy_json}
```"""
    else:
        prompt = f"""당신은 친절한 트레이딩 교육 전문가입니다.
아래 전략 JSON을 트레이딩 초보자도 쉽게 이해할 수 있게 한국어로 설명해주세요.

## 설명 형식 (마크다운)

### 전략 한눈에 보기
전략의 핵심 아이디어를 2~3문장으로 요약 (비유나 쉬운 예시 포함)

### 언제 사나요? (진입 조건)
각 진입 조건을 초보자가 이해할 수 있게 설명.
- 지표가 무엇인지 (예: RSI는 "과매수/과매도를 알려주는 온도계")
- 왜 이 조건이 매수 신호인지
- 여러 조건의 AND/OR 로직이 의미하는 것

### 언제 팔아요? (익절/손절)
- 익절: 수익이 N% 나면 자동으로 팔아서 이익을 확정
- 손절: 손실이 N%에 도달하면 자동으로 팔아서 더 큰 손실 방지
- 리스크:리워드 비율 계산 및 의미

### 투자금 설정
- 1회 투자금, 최대 동시 포지션의 의미
- 총 최대 투자금 계산

### 이 전략의 장점과 주의사항
- 장점 2~3개 (어떤 시장 상황에서 효과적인지)
- 주의사항 2~3개 (어떤 상황에서 위험한지)

## 규칙
- 전문 용어를 사용할 때는 반드시 괄호 안에 쉬운 설명 추가
- 구체적인 숫자와 예시를 활용
- 응원이나 격려 문구 불필요, 실용적 정보만 제공
- 마크다운 형식 사용

전략 JSON:
```json
{strategy_json}
```"""

    try:
        result = await _safe_generate(
            [prompt],
            config=_make_config(temperature=0.5, max_output_tokens=4096),
        )
        return result
    except Exception as e:
        logger.warning(f"전략 설명 생성 실패: {e}")
        return ""


async def generate_backtest_summary(strategy: dict, metrics: dict, language: str = "ko") -> str:
    """백테스트 결과(전략 + 지표)를 바탕으로 AI 요약 피드백 생성"""
    strategy_label = "Strategy" if language == "en" else "전략"
    no_name = "Unnamed" if language == "en" else "이름 없음"
    metrics_label = "Backtest Metrics" if language == "en" else "백테스트 지표"
    template = BACKTEST_REPORT_TEMPLATE_EN if language == "en" else BACKTEST_REPORT_TEMPLATE
    user_prompt = f"""
## {strategy_label}: {strategy.get('name', no_name)}
```json
{json.dumps(strategy, ensure_ascii=False, indent=2)}
```

## {metrics_label}
```json
{json.dumps(metrics, ensure_ascii=False, indent=2)}
```
"""
    result = await _safe_generate(
        [template, user_prompt],
        config=_make_config(temperature=0.5, max_output_tokens=4096),
    )
    return result


def _build_chat_history(history: list[dict], language: str = "ko") -> list[str]:
    """대화 히스토리를 Gemini 프롬프트용 문자열 리스트로 변환"""
    user_label = "User" if language == "en" else "사용자"
    ai_label = "AI"
    parts = []
    for msg in history[-10:]:  # 최근 10개 메시지만 사용
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            parts.append(f"{user_label}: {content}")
        else:
            parts.append(f"{ai_label}: {content}")
    return parts


def _extract_strategy_from_history(history: list[dict]) -> Optional[dict]:
    """대화 히스토리에서 마지막 파싱된 전략 추출"""
    for msg in reversed(history):
        meta = msg.get("metadata", {})
        if meta and meta.get("parsed_strategy"):
            return meta["parsed_strategy"]
    return None


def _is_question_or_chat(text: str) -> bool:
    """질문/일반 대화인지 판별 (전략 파싱 시도 전 필터링)"""
    question_markers = [
        # 한국어
        "알려줘", "알려주세요", "설명해", "설명해줘", "설명해주세요",
        "뭐야", "뭔가요", "무엇인가요", "어떻게", "어떤가요", "어떤건가요",
        "왜", "무슨", "차이", "비교", "장단점", "추천", "좋을까",
        "?", "하나요", "할까요", "인가요", "건가요", "나요",
        "방법", "팁", "주의", "조언",
        # English
        "what is", "what are", "how to", "how do", "how does",
        "why", "explain", "tell me", "describe", "compare",
        "difference", "recommend", "suggest", "tips", "advice",
        "should i", "can you", "what about", "is it",
    ]
    text_lower = text.strip().lower()
    return any(m in text_lower for m in question_markers)


async def process_chat_message(
    text: str,
    image: Optional[bytes] = None,
    strategy_id: Optional[str] = None,
    history: Optional[list[dict]] = None,
    language: str = "ko",
) -> dict:
    """채팅 메시지 처리 (텍스트 또는 멀티모달)"""
    text = _sanitize_user_input(text)
    history = history or []

    try:
        # 이미지가 있으면 멀티모달 전략 파싱
        if image:
            parsed = await parse_strategy_multimodal(text, image, language=language)
            explanation = await generate_strategy_explanation(parsed, language=language)
            default_msg = "Analyzed the chart image and generated a strategy." if language == "en" else "차트 이미지를 분석하여 전략을 생성했습니다."
            return {
                "type": "strategy_parsed",
                "message": explanation or default_msg,
                "parsed_strategy": parsed,
            }

        # 기존 전략이 있으면 코칭 모드 (DB 저장된 전략)
        if strategy_id:
            return await _coaching_response(text, strategy_id, history, language=language)

        # 대화 히스토리에서 이전에 파싱된 전략이 있으면 코칭 모드
        prev_strategy = _extract_strategy_from_history(history)
        if prev_strategy:
            return await _coaching_with_context(text, prev_strategy, history, language=language)

        # 질문/일반 대화 감지 → RAG 기반 응답
        if _is_question_or_chat(text):
            return await _general_response(text, history, language=language)

        # 새 전략 파싱 시도
        try:
            parsed = await parse_strategy_text(text, language=language)
            explanation = await generate_strategy_explanation(parsed, language=language)
            default_msg = "Strategy analyzed. Would you like to run a backtest?" if language == "en" else "전략을 분석했습니다. 백테스트를 실행해볼까요?"
            return {
                "type": "strategy_parsed",
                "message": explanation or default_msg,
                "parsed_strategy": parsed,
            }
        except (json.JSONDecodeError, ValueError):
            # 전략이 아닌 일반 대화
            return await _general_response(text, history, language=language)

    except Exception as e:
        logger.error(f"Gemini API 처리 실패: {e}")
        return {
            "type": "error",
            "message": f"Failed to generate AI response. Please try again. (Error: {type(e).__name__})" if language == "en" else f"AI 응답 생성에 실패했습니다. 잠시 후 다시 시도해주세요. (오류: {type(e).__name__})",
        }


async def _coaching_response(
    text: str, strategy_id: str, history: Optional[list[dict]] = None, language: str = "ko"
) -> dict:
    """전략 컨텍스트 기반 코칭 응답 (DB 전략) + RAG + 시장 데이터"""
    from services.supabase_client import get_strategy_by_id

    strategy = await get_strategy_by_id(strategy_id)
    parsed = strategy.get("parsed_strategy", {}) if strategy else {}
    context = ""
    if parsed:
        context = f"현재 전략: {json.dumps(parsed, ensure_ascii=False)}"

    # Binance 실시간 시장 데이터
    market_data = await fetch_market_summary(text, parsed)

    # RAG: 관련 트레이딩 지식 검색
    rag_context = build_rag_context(text)

    contents = [get_coaching_prompt(language), context]
    if market_data:
        contents.append(market_data)
    if rag_context:
        contents.append(rag_context)
    if history:
        contents.extend(_build_chat_history(history, language))
    contents.append(f"{'User' if language == 'en' else '사용자'}: {text}")

    result = await _safe_generate(
        contents,
        config=_make_config(temperature=0.5, max_output_tokens=8192),
    )
    return {
        "type": "coaching",
        "message": result,
    }


async def _coaching_with_context(
    text: str, strategy: dict, history: Optional[list[dict]] = None, language: str = "ko"
) -> dict:
    """대화 히스토리의 전략 컨텍스트 기반 코칭 응답 + RAG + 시장 데이터"""
    context = f"현재 전략: {json.dumps(strategy, ensure_ascii=False)}"

    # Binance 실시간 시장 데이터
    market_data = await fetch_market_summary(text, strategy)

    # RAG: 관련 트레이딩 지식 검색
    rag_context = build_rag_context(text)

    contents = [get_coaching_prompt(language), context]
    if market_data:
        contents.append(market_data)
    if rag_context:
        contents.append(rag_context)
    if history:
        contents.extend(_build_chat_history(history, language))
    contents.append(f"{'User' if language == 'en' else '사용자'}: {text}")

    result = await _safe_generate(
        contents,
        config=_make_config(temperature=0.5, max_output_tokens=8192),
    )
    return {
        "type": "coaching",
        "message": result,
    }


async def _general_response(
    text: str, history: Optional[list[dict]] = None, language: str = "ko"
) -> dict:
    """일반 대화 응답 (히스토리 포함) + RAG + 시장 데이터"""
    # Binance 실시간 시장 데이터 (텍스트에서 토큰 감지)
    market_data = await fetch_market_summary(text)

    # RAG: 관련 트레이딩 지식 검색
    rag_context = build_rag_context(text)

    contents = [get_coaching_prompt(language)]
    if market_data:
        contents.append(market_data)
    if rag_context:
        contents.append(rag_context)
    if history:
        contents.extend(_build_chat_history(history, language))
    contents.append(f"{'User' if language == 'en' else '사용자'}: {text}")

    result = await _safe_generate(
        contents,
        config=_make_config(temperature=0.7, max_output_tokens=8192),
    )
    return {
        "type": "general",
        "message": result,
    }


# ── 스트리밍 버전 ──────────────────────────────────────────


async def process_chat_message_stream(
    text: str,
    strategy_id: Optional[str] = None,
    history: Optional[list[dict]] = None,
    language: str = "ko",
) -> AsyncGenerator[str, None]:
    """채팅 메시지 스트리밍 처리 (텍스트 전용, 이미지는 기존 방식 유지)"""
    text = _sanitize_user_input(text)
    history = history or []
    coaching_prompt = get_coaching_prompt(language)

    try:
        # strategy_id가 있으면 DB에서 전략 로드 후 코칭 스트리밍
        if strategy_id:
            from services.supabase_client import get_strategy_by_id
            strategy = await get_strategy_by_id(strategy_id)
            parsed = strategy.get("parsed_strategy", {}) if strategy else {}
            context = ""
            if parsed:
                context = f"{'Current strategy' if language == 'en' else '현재 전략'}: {json.dumps(parsed, ensure_ascii=False)}"
            market_data = await fetch_market_summary(text, parsed)
            rag_context = build_rag_context(text)
            contents = [coaching_prompt, context]
            if market_data:
                contents.append(market_data)
            if rag_context:
                contents.append(rag_context)
            if history:
                contents.extend(_build_chat_history(history, language))
            contents.append(f"{'User' if language == 'en' else '사용자'}: {text}")

            async for chunk in _safe_generate_stream(
                contents,
                config=_make_config(temperature=0.5, max_output_tokens=8192),
            ):
                yield chunk
            return

        # 히스토리에서 전략 추출 → 코칭
        prev_strategy = _extract_strategy_from_history(history)
        if prev_strategy:
            context = f"{'Current strategy' if language == 'en' else '현재 전략'}: {json.dumps(prev_strategy, ensure_ascii=False)}"
            market_data = await fetch_market_summary(text, prev_strategy)
            rag_context = build_rag_context(text)
            contents = [coaching_prompt, context]
            if market_data:
                contents.append(market_data)
            if rag_context:
                contents.append(rag_context)
            if history:
                contents.extend(_build_chat_history(history, language))
            contents.append(f"{'User' if language == 'en' else '사용자'}: {text}")

            async for chunk in _safe_generate_stream(
                contents,
                config=_make_config(temperature=0.5, max_output_tokens=8192),
            ):
                yield chunk
            return

        # 질문/일반 대화
        if _is_question_or_chat(text):
            market_data = await fetch_market_summary(text)
            rag_context = build_rag_context(text)
            contents = [coaching_prompt]
            if market_data:
                contents.append(market_data)
            if rag_context:
                contents.append(rag_context)
            if history:
                contents.extend(_build_chat_history(history, language))
            contents.append(f"{'User' if language == 'en' else '사용자'}: {text}")

            async for chunk in _safe_generate_stream(
                contents,
                config=_make_config(temperature=0.7, max_output_tokens=8192),
            ):
                yield chunk
            return

        # 전략 파싱 시도 (스트리밍 불가 → non-stream 폴백)
        try:
            parsed = await parse_strategy_text(text, language=language)
            explanation = await generate_strategy_explanation(parsed, language=language)
            default_msg = "Strategy analyzed. Would you like to run a backtest?" if language == "en" else "전략을 분석했습니다. 백테스트를 실행해볼까요?"
            yield json.dumps({
                "type": "strategy_parsed",
                "message": explanation or default_msg,
                "parsed_strategy": parsed,
            }, ensure_ascii=False)
            return
        except (json.JSONDecodeError, ValueError):
            pass

        # 일반 대화 폴백
        market_data = await fetch_market_summary(text)
        rag_context = build_rag_context(text)
        contents = [coaching_prompt]
        if market_data:
            contents.append(market_data)
        if rag_context:
            contents.append(rag_context)
        if history:
            contents.extend(_build_chat_history(history, language))
        contents.append(f"{'User' if language == 'en' else '사용자'}: {text}")

        async for chunk in _safe_generate_stream(
            contents,
            config=_make_config(temperature=0.7, max_output_tokens=8192),
        ):
            yield chunk
    except Exception as e:
        logger.error(f"스트리밍 처리 실패: {e}", exc_info=True)
        yield json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)


async def generate_marketplace_summary(
    strategy_name: str,
    metrics: dict,
    sessions: list,
) -> str:
    """트레이드 실적을 분석하여 마켓플레이스용 AI 요약을 생성한다."""
    prompt = f"""You are a trading strategy analyst. Analyze the following paper trading results
and write a concise marketplace listing summary (3-5 paragraphs) in English.

Strategy Name: {strategy_name}

Performance Metrics:
- Total Sessions: {metrics.get('total_sessions', 0)}
- Total Trades: {metrics.get('total_trades', 0)}
- Winning Trades: {metrics.get('winning_trades', 0)}
- Win Rate: {metrics.get('win_rate', 0)}%
- Total PnL: {metrics.get('total_pnl', 0)}%
- Avg Session PnL: {metrics.get('avg_session_pnl', 0)}%

Recent Session Details:
{json.dumps(sessions[:5], indent=2, default=str)}

Write the analysis covering:
1. **Performance Overview**: Key metrics and what they mean
2. **Strengths**: What this strategy does well
3. **Risk Assessment**: Potential risks and drawdowns
4. **Best Market Conditions**: When this strategy performs best
5. **Verdict**: Overall recommendation (Aggressive/Moderate/Conservative)

Keep it professional and factual. Do not exaggerate results."""

    # 마켓플레이스 요약은 경량 모델 사용 (비용 절감)
    lite_model = "gemini-3.1-flash-lite-preview"
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=lite_model,
            contents=[prompt],
            config=_make_config(temperature=0.5, max_output_tokens=2048),
        )
        return response.text.strip() if response and response.text else ""
    except Exception as e:
        logger.warning(f"Lite 모델 실패, 기본 모델로 폴백: {e}")
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=settings.gemini_model,
                contents=[prompt],
                config=_make_config(temperature=0.5, max_output_tokens=2048),
            )
            return response.text.strip() if response and response.text else ""
        except Exception as e2:
            logger.error(f"마켓플레이스 AI 요약 생성 실패: {e2}")
            return ""

    except Exception as e:
        logger.error(f"스트리밍 처리 실패: {e}")
        yield f"Failed to generate AI response. (Error: {type(e).__name__})" if language == "en" else f"AI 응답 생성에 실패했습니다. (오류: {type(e).__name__})"
