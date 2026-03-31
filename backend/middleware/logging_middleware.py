"""JSON structured logging middleware: timestamp, method, path, status, duration_ms, user_id, ip"""
import json, logging, time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
logger = logging.getLogger("tradecoach.access")

class JSONLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        user_id = _extract_user_id(request)
        ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "unknown")
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception as exc:
            status = 500
            _log(request.method, request.url.path, status, (time.perf_counter()-start)*1000, user_id, ip, str(exc))
            raise
        _log(request.method, request.url.path, status, (time.perf_counter()-start)*1000, user_id, ip)
        return response

def _extract_user_id(req):
    auth = req.headers.get("authorization","")
    if not auth.startswith("Bearer "): return None
    try:
        import base64; parts = auth[7:].split(".")
        if len(parts)!=3: return None
        p = parts[1] + "=="*(4-len(parts[1])%4)
        return str(json.loads(base64.urlsafe_b64decode(p)).get("sub"))
    except: return None

def _log(method, path, status, dur_ms, user_id, ip, error=None):
    from datetime import datetime, timezone
    r = {"timestamp":datetime.now(timezone.utc).isoformat(),"method":method,"path":path,"status_code":status,"duration_ms":round(dur_ms,2),"user_id":user_id,"client_ip":ip}
    if error: r["error"]=error
    lvl = logging.ERROR if status>=500 else (logging.WARNING if status>=400 else logging.INFO)
    logger.log(lvl, json.dumps(r, ensure_ascii=False))
