"""Telegram Bot API notifications with HTML formatting"""
import logging, aiohttp
logger = logging.getLogger(__name__)

class TelegramChannel:
    name = "telegram"
    def __init__(self, bot_token, chat_id):
        self._url=f"https://api.telegram.org/bot{bot_token}/sendMessage"; self._chat_id=str(chat_id)
    async def send(self, payload):
        sym=payload.get("symbol","?"); side=payload.get("side","?"); price=payload.get("avg_price",0)
        emoji="📈" if side=="BUY" else "📉"
        text=f"{emoji} <b>{sym}</b> | {side} | 💰 {price:,.4f} USDT | ⚡ {payload.get('leverage',1)}x"
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as s:
            async with s.post(self._url, json={"chat_id":self._chat_id,"text":text,"parse_mode":"HTML"}) as r:
                r.raise_for_status()
