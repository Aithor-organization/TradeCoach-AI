import asyncio
import json
import io
import logging
from typing import AsyncGenerator, Optional

import google.generativeai as genai
from PIL import Image

from config import get_settings
from prompts.strategy_parser import STRATEGY_SYSTEM_PROMPT, build_parse_prompt
from prompts.coaching import COACHING_SYSTEM_PROMPT
from services.rag import build_rag_context

logger = logging.getLogger(__name__)

settings = get_settings()
genai.configure(api_key=settings.gemini_api_key)

_model = genai.GenerativeModel("gemini-2.5-flash")

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # 초


async def _safe_generate(parts: list, generation_config: genai.GenerationConfig) -> str:
    """Gemini API 호출 + 재시도 로직 (지수 백오프)"""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = await _model.generate_content_async(
                parts,
                generation_config=generation_config,
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
    parts: list, generation_config: genai.GenerationConfig
) -> AsyncGenerator[str, None]:
    """Gemini API 스트리밍 호출 + 재시도 로직"""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = await _model.generate_content_async(
                parts,
                generation_config=generation_config,
                stream=True,
            )
            async for chunk in response:
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
    # ```json ... ``` 블록 추출
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        json_str = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        json_str = text[start:end].strip()
    else:
        json_str = text.strip()

    return json.loads(json_str)


async def parse_strategy_text(text: str) -> dict:
    """텍스트 → 구조화된 전략 JSON"""
    prompt = build_parse_prompt(text)
    result = await _safe_generate(
        [STRATEGY_SYSTEM_PROMPT, prompt],
        generation_config=genai.GenerationConfig(
            temperature=0.3,
            max_output_tokens=2048,
        ),
    )
    return _extract_json_from_response(result)


async def parse_strategy_multimodal(text: str, image: bytes) -> dict:
    """이미지 + 텍스트 → 전략 JSON (멀티모달)"""
    img = Image.open(io.BytesIO(image))
    parts = [
        STRATEGY_SYSTEM_PROMPT,
        img,
        "위 차트 이미지를 분석하여 트레이딩 전략으로 변환해주세요.",
    ]
    if text:
        parts.append(f"추가 설명: {text}")

    result = await _safe_generate(
        parts,
        generation_config=genai.GenerationConfig(
            temperature=0.3,
            max_output_tokens=2048,
        ),
    )
    return _extract_json_from_response(result)


async def generate_backtest_summary(strategy: dict, metrics: dict) -> str:
    """백테스트 결과(전략 + 지표)를 바탕으로 AI 요약 피드백 생성"""
    
    analysis_system_prompt = """당신은 날카로운 암호화폐 트레이더 및 분석가입니다. 
주어진 트레이딩 전략 정보와 백테스트 결과 지표를 분석하여 3~4문장의 아주 간결한 한국어 마크다운 리포트를 작성하세요.
수익률, MDD, 승률을 언급하며 전략의 한계점이나 개선 방향을 짚어주세요.
절대 < 기호나 > 기호를 사용하지 말고, '초과', '미만', '이하'로 풀어서 쓰세요.
중간에 문장을 끊거나 멈추지 말고 끝까지 완성된 문장으로 대답하세요."""

    user_prompt = f"""
## 전략: {strategy.get('name', '이름 없음')}
```json
{json.dumps(strategy, ensure_ascii=False, indent=2)}
```

## 백테스트 지표
```json
{json.dumps(metrics, ensure_ascii=False, indent=2)}
```
"""
    result = await _safe_generate(
        [analysis_system_prompt, user_prompt],
        generation_config=genai.GenerationConfig(
            temperature=0.5,
            max_output_tokens=1024,
        ),
    )
    return result


def _build_chat_history(history: list[dict]) -> list[str]:
    """대화 히스토리를 Gemini 프롬프트용 문자열 리스트로 변환"""
    parts = []
    for msg in history[-10:]:  # 최근 10개 메시지만 사용
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            parts.append(f"사용자: {content}")
        else:
            parts.append(f"AI: {content}")
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
        "알려줘", "알려주세요", "설명해", "설명해줘", "설명해주세요",
        "뭐야", "뭔가요", "무엇인가요", "어떻게", "어떤가요", "어떤건가요",
        "왜", "무슨", "차이", "비교", "장단점", "추천", "좋을까",
        "?", "하나요", "할까요", "인가요", "건가요", "나요",
        "방법", "팁", "주의", "조언",
    ]
    text_lower = text.strip()
    return any(m in text_lower for m in question_markers)


async def process_chat_message(
    text: str,
    image: Optional[bytes] = None,
    strategy_id: Optional[str] = None,
    history: Optional[list[dict]] = None,
) -> dict:
    """채팅 메시지 처리 (텍스트 또는 멀티모달)"""
    history = history or []

    try:
        # 이미지가 있으면 멀티모달 전략 파싱
        if image:
            parsed = await parse_strategy_multimodal(text, image)
            return {
                "type": "strategy_parsed",
                "message": "차트 이미지를 분석하여 전략을 생성했습니다.",
                "parsed_strategy": parsed,
            }

        # 기존 전략이 있으면 코칭 모드 (DB 저장된 전략)
        if strategy_id:
            return await _coaching_response(text, strategy_id, history)

        # 대화 히스토리에서 이전에 파싱된 전략이 있으면 코칭 모드
        prev_strategy = _extract_strategy_from_history(history)
        if prev_strategy:
            return await _coaching_with_context(text, prev_strategy, history)

        # 질문/일반 대화 감지 → RAG 기반 응답
        if _is_question_or_chat(text):
            return await _general_response(text, history)

        # 새 전략 파싱 시도
        try:
            parsed = await parse_strategy_text(text)
            return {
                "type": "strategy_parsed",
                "message": "전략을 분석했습니다. 백테스트를 실행해볼까요?",
                "parsed_strategy": parsed,
            }
        except (json.JSONDecodeError, ValueError):
            # 전략이 아닌 일반 대화
            return await _general_response(text, history)

    except Exception as e:
        logger.error(f"Gemini API 처리 실패: {e}")
        return {
            "type": "error",
            "message": f"AI 응답 생성에 실패했습니다. 잠시 후 다시 시도해주세요. (오류: {type(e).__name__})",
        }


async def _coaching_response(
    text: str, strategy_id: str, history: Optional[list[dict]] = None
) -> dict:
    """전략 컨텍스트 기반 코칭 응답 (DB 전략) + RAG"""
    from services.supabase_client import get_strategy_by_id

    strategy = await get_strategy_by_id(strategy_id)
    context = ""
    if strategy:
        context = f"현재 전략: {json.dumps(strategy.get('parsed_strategy', {}), ensure_ascii=False)}"

    # RAG: 관련 트레이딩 지식 검색
    rag_context = build_rag_context(text)

    parts = [COACHING_SYSTEM_PROMPT, context]
    if rag_context:
        parts.append(rag_context)
    if history:
        parts.extend(_build_chat_history(history))
    parts.append(f"사용자: {text}")

    result = await _safe_generate(
        parts,
        generation_config=genai.GenerationConfig(
            temperature=0.5,
            max_output_tokens=8192,
        ),
    )
    return {
        "type": "coaching",
        "message": result,
    }


async def _coaching_with_context(
    text: str, strategy: dict, history: Optional[list[dict]] = None
) -> dict:
    """대화 히스토리의 전략 컨텍스트 기반 코칭 응답 + RAG"""
    context = f"현재 전략: {json.dumps(strategy, ensure_ascii=False)}"

    # RAG: 관련 트레이딩 지식 검색
    rag_context = build_rag_context(text)

    parts = [COACHING_SYSTEM_PROMPT, context]
    if rag_context:
        parts.append(rag_context)
    if history:
        parts.extend(_build_chat_history(history))
    parts.append(f"사용자: {text}")

    result = await _safe_generate(
        parts,
        generation_config=genai.GenerationConfig(
            temperature=0.5,
            max_output_tokens=8192,
        ),
    )
    return {
        "type": "coaching",
        "message": result,
    }


async def _general_response(
    text: str, history: Optional[list[dict]] = None
) -> dict:
    """일반 대화 응답 (히스토리 포함) + RAG"""
    # RAG: 관련 트레이딩 지식 검색
    rag_context = build_rag_context(text)

    parts = [COACHING_SYSTEM_PROMPT]
    if rag_context:
        parts.append(rag_context)
    if history:
        parts.extend(_build_chat_history(history))
    parts.append(f"사용자: {text}")

    result = await _safe_generate(
        parts,
        generation_config=genai.GenerationConfig(
            temperature=0.7,
            max_output_tokens=8192,
        ),
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
) -> AsyncGenerator[str, None]:
    """채팅 메시지 스트리밍 처리 (텍스트 전용, 이미지는 기존 방식 유지)"""
    history = history or []

    try:
        # strategy_id가 있으면 DB에서 전략 로드 후 코칭 스트리밍
        if strategy_id:
            from services.supabase_client import get_strategy_by_id
            strategy = await get_strategy_by_id(strategy_id)
            context = ""
            if strategy:
                context = f"현재 전략: {json.dumps(strategy.get('parsed_strategy', {}), ensure_ascii=False)}"
            rag_context = build_rag_context(text)
            parts = [COACHING_SYSTEM_PROMPT, context]
            if rag_context:
                parts.append(rag_context)
            if history:
                parts.extend(_build_chat_history(history))
            parts.append(f"사용자: {text}")

            async for chunk in _safe_generate_stream(
                parts,
                generation_config=genai.GenerationConfig(
                    temperature=0.5,
                    max_output_tokens=8192,
                ),
            ):
                yield chunk
            return

        # 히스토리에서 전략 추출 → 코칭
        prev_strategy = _extract_strategy_from_history(history)
        if prev_strategy:
            context = f"현재 전략: {json.dumps(prev_strategy, ensure_ascii=False)}"
            rag_context = build_rag_context(text)
            parts = [COACHING_SYSTEM_PROMPT, context]
            if rag_context:
                parts.append(rag_context)
            if history:
                parts.extend(_build_chat_history(history))
            parts.append(f"사용자: {text}")

            async for chunk in _safe_generate_stream(
                parts,
                generation_config=genai.GenerationConfig(
                    temperature=0.5,
                    max_output_tokens=8192,
                ),
            ):
                yield chunk
            return

        # 질문/일반 대화
        if _is_question_or_chat(text):
            rag_context = build_rag_context(text)
            parts = [COACHING_SYSTEM_PROMPT]
            if rag_context:
                parts.append(rag_context)
            if history:
                parts.extend(_build_chat_history(history))
            parts.append(f"사용자: {text}")

            async for chunk in _safe_generate_stream(
                parts,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=8192,
                ),
            ):
                yield chunk
            return

        # 전략 파싱 시도 (스트리밍 불가 → non-stream 폴백)
        try:
            parsed = await parse_strategy_text(text)
            yield json.dumps({
                "type": "strategy_parsed",
                "message": "전략을 분석했습니다. 백테스트를 실행해볼까요?",
                "parsed_strategy": parsed,
            }, ensure_ascii=False)
            return
        except (json.JSONDecodeError, ValueError):
            pass

        # 일반 대화 폴백
        rag_context = build_rag_context(text)
        parts = [COACHING_SYSTEM_PROMPT]
        if rag_context:
            parts.append(rag_context)
        if history:
            parts.extend(_build_chat_history(history))
        parts.append(f"사용자: {text}")

        async for chunk in _safe_generate_stream(
            parts,
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                max_output_tokens=8192,
            ),
        ):
            yield chunk

    except Exception as e:
        logger.error(f"스트리밍 처리 실패: {e}")
        yield f"AI 응답 생성에 실패했습니다. (오류: {type(e).__name__})"
