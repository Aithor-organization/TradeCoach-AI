from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Optional
from dependencies import get_current_user_id
from routers.auth import limiter
import json
import logging
import re

logger = logging.getLogger(__name__)

router = APIRouter()


def _extract_strategy_from_text(text: str, ensure_defaults=None) -> Optional[dict]:
    """AI 응답 텍스트에서 전략 JSON을 추출한다 (strategy_update, 코드블록, 인라인)."""
    if not text:
        return None

    # 1. ```strategy_update 블록
    if "```strategy_update" in text:
        try:
            start = text.index("```strategy_update") + len("```strategy_update")
            end = text.index("```", start)
            c = json.loads(text[start:end].strip())
            if isinstance(c, dict) and "name" in c:
                return ensure_defaults(c) if ensure_defaults else c
        except (ValueError, json.JSONDecodeError):
            pass

    # 2. 모든 코드 블록
    code_blocks = re.findall(r'```(?:\w*)\s*\n?(.*?)```', text, re.DOTALL)
    for block in code_blocks:
        try:
            c = json.loads(block.strip())
            if isinstance(c, dict) and "name" in c and "entry" in c:
                return ensure_defaults(c) if ensure_defaults else c
        except (ValueError, json.JSONDecodeError):
            continue

    # 3. 인라인 JSON: {"name": 패턴으로 시작하는 JSON 객체 추출 (중괄호 매칭)
    for match in re.finditer(r'\{"name"\s*:', text):
        start = match.start()
        depth = 0
        end = start
        for i in range(start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end > start:
            try:
                c = json.loads(text[start:end])
                if isinstance(c, dict) and "entry" in c:
                    return ensure_defaults(c) if ensure_defaults else c
            except (ValueError, json.JSONDecodeError):
                continue

    return None


@router.post("/message")
@limiter.limit("30/minute")
async def send_message(
    request: Request,
    content: str = Form(...),
    strategy_id: Optional[str] = Form(None),
    history: Optional[str] = Form(None),
    language: Optional[str] = Form("ko"),
):
    """텍스트 메시지 전송 → AI 응답 + DB 저장"""
    from services.gemini import process_chat_message
    from services.supabase_client import save_chat_message

    # 대화 히스토리 파싱
    chat_history = []
    if history:
        try:
            chat_history = json.loads(history)
        except json.JSONDecodeError:
            pass

    try:
        result = await process_chat_message(
            text=content,
            strategy_id=strategy_id,
            history=chat_history,
            language=language or "ko",
        )
    except Exception as e:
        logger.error(f"AI 메시지 처리 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="AI 응답 생성에 실패했습니다.")

    # 코칭 응답에서 전략 JSON 추출 (strategy_update, 코드블록, 인라인 JSON)
    msg_text = result.get("message", "")
    if not result.get("parsed_strategy"):
        from services.gemini import _ensure_strategy_defaults
        result["parsed_strategy"] = _extract_strategy_from_text(msg_text, _ensure_strategy_defaults)
        if result["parsed_strategy"]:
            result["type"] = "strategy_parsed"

    # strategy_id가 있으면 user/AI 메시지를 DB에 저장 (실패해도 응답은 반환)
    if strategy_id:
        try:
            await save_chat_message(strategy_id, "user", content)
            ai_content = result.get("message", "")
            ai_metadata = {}
            if result.get("parsed_strategy"):
                ai_metadata["parsed_strategy"] = result["parsed_strategy"]
            if result.get("type"):
                ai_metadata["type"] = result["type"]
            await save_chat_message(strategy_id, "assistant", ai_content, ai_metadata or None)
        except Exception as e:
            logger.warning(f"채팅 메시지 DB 저장 실패 (무시): {e}")

    return result


@router.post("/message/image")
@limiter.limit("30/minute")
async def send_message_with_image(
    request: Request,
    content: str = Form(""),
    strategy_id: Optional[str] = Form(None),
    image: UploadFile = File(...),
    history: Optional[str] = Form(None),
    language: Optional[str] = Form("ko"),
):
    """이미지 포함 메시지 → Gemini 멀티모달 분석 + DB 저장"""
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Image file required")

    image_bytes = await image.read()
    if len(image_bytes) > 10 * 1024 * 1024:  # 10MB 제한
        raise HTTPException(status_code=400, detail="Image too large (max 10MB)")

    from services.gemini import process_chat_message
    from services.supabase_client import save_chat_message

    chat_history = []
    if history:
        try:
            chat_history = json.loads(history)
        except json.JSONDecodeError:
            pass

    try:
        result = await process_chat_message(
            text=content,
            image=image_bytes,
            strategy_id=strategy_id,
            history=chat_history,
            language=language or "ko",
        )
    except Exception as e:
        logger.error(f"이미지 메시지 AI 처리 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="AI 이미지 분석에 실패했습니다.")

    # strategy_id가 있으면 user/AI 메시지를 DB에 저장 (실패해도 응답은 반환)
    if strategy_id:
        try:
            await save_chat_message(strategy_id, "user", content or "[이미지 전송]")
            ai_content = result.get("message", "")
            ai_metadata = {}
            if result.get("parsed_strategy"):
                ai_metadata["parsed_strategy"] = result["parsed_strategy"]
            if result.get("type"):
                ai_metadata["type"] = result["type"]
            await save_chat_message(strategy_id, "assistant", ai_content, ai_metadata or None)
        except Exception as e:
            logger.warning(f"채팅 메시지 DB 저장 실패 (무시): {e}")

    return result


@router.post("/message/stream")
@limiter.limit("30/minute")
async def send_message_stream(
    request: Request,
    content: str = Form(...),
    strategy_id: Optional[str] = Form(None),
    history: Optional[str] = Form(None),
    language: Optional[str] = Form("ko"),
):
    """텍스트 메시지 스트리밍 → SSE 응답 + DB 저장"""
    from services.gemini import process_chat_message_stream
    from services.supabase_client import save_chat_message

    lang = language or "ko"

    chat_history = []
    if history:
        try:
            chat_history = json.loads(history)
        except json.JSONDecodeError:
            pass

    # 유저 메시지 먼저 DB 저장
    if strategy_id:
        try:
            await save_chat_message(strategy_id, "user", content)
        except Exception as e:
            logger.warning(f"유저 메시지 DB 저장 실패 (무시): {e}")

    async def event_generator():
        full_text = ""
        response_type = "coaching"
        parsed_strategy = None
        try:
            async for chunk in process_chat_message_stream(
                text=content,
                strategy_id=strategy_id,
                history=chat_history,
                language=lang,
            ):
                # 전략 파싱 JSON인 경우 (non-stream 폴백)
                if chunk.startswith("{") and '"type"' in chunk:
                    try:
                        data = json.loads(chunk)
                        response_type = data.get("type", "coaching")
                        parsed_strategy = data.get("parsed_strategy")
                        full_text = data.get("message", chunk)
                        yield f"data: {json.dumps({'chunk': full_text}, ensure_ascii=False)}\n\n"
                        break
                    except json.JSONDecodeError:
                        pass

                full_text += chunk
                yield f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"스트리밍 오류: {e}")
            error_msg = f"AI 응답 생성에 실패했습니다. (오류: {type(e).__name__})"
            if not full_text:
                full_text = error_msg
            yield f"data: {json.dumps({'chunk': error_msg}, ensure_ascii=False)}\n\n"

        # 코칭 응답에서 전략 JSON 추출 (공통 함수 사용)
        if not parsed_strategy:
            from services.gemini import _ensure_strategy_defaults
            extracted = _extract_strategy_from_text(full_text, _ensure_strategy_defaults)
            if extracted:
                parsed_strategy = extracted
                response_type = "strategy_parsed"

        # 완료 이벤트 (전체 텍스트 + 메타데이터)
        done_data = {"done": True, "type": response_type, "full_text": full_text}
        if parsed_strategy:
            done_data["parsed_strategy"] = parsed_strategy
        yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"

        # AI 응답 DB 저장
        if strategy_id and full_text:
            try:
                ai_metadata = {"type": response_type}
                if parsed_strategy:
                    ai_metadata["parsed_strategy"] = parsed_strategy
                await save_chat_message(strategy_id, "assistant", full_text, ai_metadata)
            except Exception as e:
                logger.warning(f"AI 메시지 DB 저장 실패 (무시): {e}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/history/{strategy_id}")
async def get_chat_history(
    strategy_id: str,
    user_id: str | None = Depends(get_current_user_id),
):
    """대화 히스토리 조회 (로그인 시 소유권 검증)"""
    from services.supabase_client import get_chat_messages, get_strategy_by_id

    try:
        # 로그인한 경우에만 소유권 검증
        if user_id:
            strategy = await get_strategy_by_id(strategy_id)
            if strategy:
                owner = strategy.get("user_id")
                if owner and owner != user_id:
                    raise HTTPException(status_code=403, detail="이 대화에 대한 권한이 없습니다.")

        messages = await get_chat_messages(strategy_id)
        return {"messages": messages}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"대화 히스토리 조회 실패 (strategy_id={strategy_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="대화 히스토리 조회 중 오류가 발생했습니다.")
