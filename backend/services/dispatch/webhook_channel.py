"""HMAC-SHA256 signed HTTP POST webhook, 5s timeout"""
import hashlib, hmac, json, logging
import aiohttp
logger = logging.getLogger(__name__)

class WebhookChannel:
    name = "webhook"
    def __init__(self, url, secret):
        self._url=url; self._secret=secret.encode()
    async def send(self, payload):
        body=json.dumps(payload,ensure_ascii=False).encode()
        sig=f"sha256={hmac.new(self._secret,body,hashlib.sha256).hexdigest()}"
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as s:
            async with s.post(self._url, data=body, headers={"Content-Type":"application/json","X-Signature":sig}) as r:
                r.raise_for_status()
