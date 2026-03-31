"""Backtest Task Manager — asyncio-based in-memory task registry with auto-cleanup"""
import asyncio, uuid, logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class TaskEntry:
    task_id: str
    status: str = "pending"
    progress: int = 0
    result: Optional[Dict] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

class BacktestTaskManager:
    def __init__(self):
        self._tasks: Dict[str, TaskEntry] = {}
    
    def create_task(self) -> str:
        tid = str(uuid.uuid4())
        self._tasks[tid] = TaskEntry(task_id=tid)
        return tid
    
    def get_status(self, tid: str) -> Optional[Dict]:
        t = self._tasks.get(tid)
        if not t: return None
        return {"task_id":tid,"status":t.status,"progress":t.progress,"error":t.error}
    
    def get_result(self, tid: str) -> Optional[Dict]:
        t = self._tasks.get(tid)
        return t.result if t and t.status=="completed" else None
    
    async def run_backtest_async(self, tid: str, func, *args, **kwargs):
        t = self._tasks.get(tid)
        if not t: return
        t.status = "running"; t.progress = 10
        try:
            loop = asyncio.get_event_loop()
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = await loop.run_in_executor(None, lambda: func(*args, **kwargs))
            t.result = result; t.status = "completed"; t.progress = 100
        except Exception as e:
            t.status = "failed"; t.error = str(e)
            logger.error("Backtest task %s failed: %s", tid, e)
    
    def cleanup_old(self, max_age_hours=1):
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        expired = [k for k,v in self._tasks.items() if v.status in ("completed","failed") and v.created_at < cutoff]
        for k in expired: del self._tasks[k]

task_manager = BacktestTaskManager()
