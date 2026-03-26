"""Emergency stop system: POST /admin/emergency-stop, POST /admin/resume, GET /admin/status"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

class _State:
    def __init__(self): self.stopped=False; self.stopped_at=None; self.reason=None
    def stop(self, reason=None): self.stopped=True; self.stopped_at=datetime.now(timezone.utc); self.reason=reason
    def resume(self): self.stopped=False
_state = _State()

def is_emergency_stopped() -> bool: return _state.stopped

class StopReq(BaseModel): reason: Optional[str]=None

@router.post("/emergency-stop")
async def emergency_stop(body: StopReq):
    if _state.stopped: raise HTTPException(409, "Already stopped")
    _state.stop(body.reason); logger.critical("EMERGENCY STOP: %s", body.reason)
    return {"success":True,"message":"Emergency stop activated","stopped_at":_state.stopped_at.isoformat()}

@router.post("/resume")
async def resume():
    if not _state.stopped: raise HTTPException(409, "Not stopped")
    _state.resume(); logger.warning("System resumed")
    return {"success":True,"message":"System resumed"}

@router.get("/status")
async def status():
    return {"is_stopped":_state.stopped,"stopped_at":_state.stopped_at.isoformat() if _state.stopped_at else None,"reason":_state.reason,"server_time":datetime.now(timezone.utc).isoformat()}
