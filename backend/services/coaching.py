import json
from typing import Optional

from google import genai
from google.genai import types

from config import get_settings
from prompts.coaching import COACHING_SYSTEM_PROMPT

settings = get_settings()

_client = genai.Client(api_key=settings.gemini_api_key)
_MODEL = "gemini-3-flash-preview"


async def generate_coaching(
    strategy: dict,
    backtest_result: dict,
    user_message: Optional[str] = None,
) -> str:
    """백테스트 결과 기반 AI 코칭 생성"""
    metrics = backtest_result.get("metrics", backtest_result)

    context = f"""
현재 전략: {json.dumps(strategy, ensure_ascii=False, indent=2)}

백테스트 결과:
- 총 수익률: {metrics.get('total_return', 0)}%
- 최대 낙폭 (MDD): {metrics.get('max_drawdown', 0)}%
- 샤프 비율: {metrics.get('sharpe_ratio', 0)}
- 승률: {metrics.get('win_rate', 0)}%
- 총 거래 수: {metrics.get('total_trades', 0)}
"""

    contents = [COACHING_SYSTEM_PROMPT, context]
    if user_message:
        contents.append(f"사용자 질문: {user_message}")
    else:
        contents.append("이 백테스트 결과를 분석하고 전략 개선점을 코칭해주세요.")

    response = await _client.aio.models.generate_content(
        model=_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0.5,
            max_output_tokens=8192,
        ),
    )
    return response.text
