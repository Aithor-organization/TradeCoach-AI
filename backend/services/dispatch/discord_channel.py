"""Discord Webhook Embed: green=BUY, red=SELL, grey=CLOSE, handles 204"""
import logging, aiohttp
from datetime import datetime, timezone
logger = logging.getLogger(__name__)

class DiscordChannel:
    name = "discord"
    def __init__(self, webhook_url): self._url=webhook_url
    async def send(self, payload):
        side=payload.get("side","").upper()
        color={"BUY":0x2ECC71,"SELL":0xE74C3C}.get(side, 0x95A5A6)
        embed={"title":f"{payload.get('symbol','?')} | {side}","color":color,
            "fields":[{"name":"Price","value":f"{payload.get('avg_price',0):,.4f}","inline":True},
                      {"name":"Leverage","value":f"{payload.get('leverage',1)}x","inline":True}],
            "timestamp":datetime.now(timezone.utc).isoformat(),"footer":{"text":"TradeCoach AI"}}
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as s:
            async with s.post(self._url, json={"embeds":[embed]}) as r:
                if r.status not in (200,204): r.raise_for_status()
