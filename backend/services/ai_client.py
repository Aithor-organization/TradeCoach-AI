"""Unified AI client supporting Gemini (primary) and Claude (fallback).

Usage:
    from services.ai_client import get_ai_client

    client = get_ai_client()
    response = await client.chat(system_prompt, user_message)
    print(response.content, response.model_used, response.tokens_used)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from config import get_settings

logger = logging.getLogger(__name__)

# Claude (anthropic) SDK is optional — gracefully handle missing installation.
try:
    import anthropic  # type: ignore

    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False
    logger.info(
        "anthropic SDK not installed. Claude fallback will be disabled. "
        "Install with: pip install 'anthropic>=0.40.0'"
    )

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds


@dataclass
class AIResponse:
    """Structured response from any AI backend."""

    content: str
    model_used: str
    tokens_used: int = 0
    # Internal metadata — not exposed to callers
    _errors: list[str] = field(default_factory=list, repr=False)


class AIClient:
    """Unified LLM client supporting Gemini and Claude.

    Selection strategy:
    - Primary model is determined by the AI_PRIMARY_MODEL env variable
      (accepted values: "gemini", "claude"). Defaults to "gemini".
    - On primary model failure after MAX_RETRIES, auto-falls back to secondary.
    - If the fallback SDK is not installed, the error from the primary is re-raised.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        # Allow runtime override via environment variable
        import os

        primary_env = os.getenv("AI_PRIMARY_MODEL", "gemini").lower()
        if primary_env not in ("gemini", "claude"):
            logger.warning(
                "AI_PRIMARY_MODEL '%s' is not recognized. Defaulting to 'gemini'.",
                primary_env,
            )
            primary_env = "gemini"
        self.primary: str = primary_env
        self.fallback: str = "claude" if self.primary == "gemini" else "gemini"
        self._gemini_client = self._init_gemini()
        self._claude_client = self._init_claude()

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _init_gemini(self):
        """Lazily initialise the Gemini client; returns None on failure."""
        try:
            from google import genai  # type: ignore

            api_key = self._settings.gemini_api_key
            if not api_key:
                logger.warning("GEMINI_API_KEY not set — Gemini will be unavailable.")
                return None
            return genai.Client(api_key=api_key)
        except Exception as exc:
            logger.warning("Failed to initialise Gemini client: %s", exc)
            return None

    def _init_claude(self):
        """Lazily initialise the Anthropic client; returns None if SDK absent."""
        if not _ANTHROPIC_AVAILABLE:
            return None
        try:
            api_key = getattr(self._settings, "anthropic_api_key", None)
            import os

            api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
            if not api_key:
                logger.warning("ANTHROPIC_API_KEY not set — Claude will be unavailable.")
                return None
            return anthropic.AsyncAnthropic(api_key=api_key)
        except Exception as exc:
            logger.warning("Failed to initialise Anthropic client: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        image_data: Optional[bytes] = None,
        max_tokens: int = 2000,
    ) -> AIResponse:
        """Send a chat request, trying the primary model then falling back.

        Args:
            system_prompt: The system / instruction prompt.
            user_message:  The user's message text.
            image_data:    Optional raw image bytes (multimodal). Claude does
                           support images, but Gemini is preferred for vision tasks.
            max_tokens:    Maximum tokens to generate.

        Returns:
            AIResponse with content, model_used, and tokens_used fields.

        Raises:
            RuntimeError: When both primary and fallback models fail.
        """
        primary_caller = (
            self._call_gemini if self.primary == "gemini" else self._call_claude
        )
        fallback_caller = (
            self._call_claude if self.primary == "gemini" else self._call_gemini
        )

        errors: list[str] = []

        # --- Try primary ---
        try:
            response = await primary_caller(
                system_prompt=system_prompt,
                user_message=user_message,
                image_data=image_data,
                max_tokens=max_tokens,
            )
            return response
        except Exception as primary_exc:
            err_msg = f"{self.primary} failed: {type(primary_exc).__name__}: {primary_exc}"
            logger.warning("%s — attempting fallback to %s", err_msg, self.fallback)
            errors.append(err_msg)

        # --- Try fallback ---
        try:
            response = await fallback_caller(
                system_prompt=system_prompt,
                user_message=user_message,
                image_data=image_data,
                max_tokens=max_tokens,
            )
            response._errors = errors
            return response
        except Exception as fallback_exc:
            err_msg = f"{self.fallback} failed: {type(fallback_exc).__name__}: {fallback_exc}"
            errors.append(err_msg)
            raise RuntimeError(
                "Both AI models failed.\n" + "\n".join(errors)
            ) from fallback_exc

    # ------------------------------------------------------------------
    # Backend implementations
    # ------------------------------------------------------------------

    async def _call_gemini(
        self,
        system_prompt: str,
        user_message: str,
        image_data: Optional[bytes] = None,
        max_tokens: int = 2000,
    ) -> AIResponse:
        """Call Gemini with retry / back-off logic."""
        if self._gemini_client is None:
            raise RuntimeError("Gemini client is not initialised (missing API key or SDK).")

        from google.genai import types  # type: ignore

        config = types.GenerateContentConfig(
            temperature=0.5,
            max_output_tokens=max_tokens,
            system_instruction=system_prompt,
        )

        contents: list = []
        if image_data:
            from PIL import Image  # type: ignore
            import io

            img = Image.open(io.BytesIO(image_data))
            contents.append(img)
        contents.append(user_message)

        model = "gemini-3-flash-preview"
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await self._gemini_client.aio.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                )
                tokens = 0
                try:
                    usage = response.usage_metadata
                    tokens = (usage.total_token_count or 0) if usage else 0
                except Exception:
                    pass
                return AIResponse(
                    content=response.text or "",
                    model_used=model,
                    tokens_used=tokens,
                )
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "Gemini attempt %d/%d failed: %s", attempt + 1, MAX_RETRIES, exc
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_BASE_DELAY * (2**attempt))

        raise last_exc  # type: ignore[misc]

    async def _call_claude(
        self,
        system_prompt: str,
        user_message: str,
        image_data: Optional[bytes] = None,
        max_tokens: int = 2000,
    ) -> AIResponse:
        """Call Claude (Anthropic) with retry / back-off logic."""
        if not _ANTHROPIC_AVAILABLE:
            raise RuntimeError(
                "anthropic SDK is not installed. "
                "Install with: pip install 'anthropic>=0.40.0'"
            )
        if self._claude_client is None:
            raise RuntimeError(
                "Claude client is not initialised (missing ANTHROPIC_API_KEY)."
            )

        model = "claude-3-5-haiku-latest"

        # Build message content
        message_content: list = []
        if image_data:
            import base64

            encoded = base64.standard_b64encode(image_data).decode("utf-8")
            message_content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": encoded,
                    },
                }
            )
        message_content.append({"type": "text", "text": user_message})

        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await self._claude_client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": message_content}],
                )
                content_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        content_text += block.text
                tokens = 0
                if response.usage:
                    tokens = (
                        (response.usage.input_tokens or 0)
                        + (response.usage.output_tokens or 0)
                    )
                return AIResponse(
                    content=content_text,
                    model_used=model,
                    tokens_used=tokens,
                )
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "Claude attempt %d/%d failed: %s", attempt + 1, MAX_RETRIES, exc
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_BASE_DELAY * (2**attempt))

        raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Module-level singleton factory
# ---------------------------------------------------------------------------

_ai_client_instance: AIClient | None = None


def get_ai_client() -> AIClient:
    """Return the module-level AIClient singleton."""
    global _ai_client_instance
    if _ai_client_instance is None:
        _ai_client_instance = AIClient()
    return _ai_client_instance
