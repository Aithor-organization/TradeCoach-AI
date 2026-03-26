"""
인메모리 백그라운드 작업 저장소.

긴 실행 시간의 최적화/전진분석 작업을 비동기로 처리하고
결과를 폴링으로 조회할 수 있게 한다.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Job:
    __slots__ = ("id", "status", "result", "error", "created_at", "completed_at")

    def __init__(self, job_id: str):
        self.id = job_id
        self.status = JobStatus.PENDING
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.created_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        d: Dict[str, Any] = {
            "job_id": self.id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
        }
        if self.status == JobStatus.COMPLETED:
            d["result"] = self.result
            d["completed_at"] = self.completed_at.isoformat() if self.completed_at else None
        elif self.status == JobStatus.FAILED:
            d["error"] = self.error
            d["completed_at"] = self.completed_at.isoformat() if self.completed_at else None
        return d


# 인메모리 저장소 (서버 재시작 시 초기화됨)
_jobs: Dict[str, Job] = {}
_MAX_JOBS = 100
_JOB_TTL = timedelta(minutes=30)


def _cleanup_old_jobs() -> None:
    """오래된 작업 정리 (30분 초과)"""
    now = datetime.utcnow()
    expired = [
        jid for jid, j in _jobs.items()
        if now - j.created_at > _JOB_TTL
    ]
    for jid in expired:
        del _jobs[jid]


def create_job() -> Job:
    """새 작업 생성"""
    _cleanup_old_jobs()
    if len(_jobs) >= _MAX_JOBS:
        # 가장 오래된 완료 작업 삭제
        completed = [
            (jid, j) for jid, j in _jobs.items()
            if j.status in (JobStatus.COMPLETED, JobStatus.FAILED)
        ]
        if completed:
            completed.sort(key=lambda x: x[1].created_at)
            del _jobs[completed[0][0]]

    job_id = uuid.uuid4().hex[:12]
    job = Job(job_id)
    _jobs[job_id] = job
    return job


def get_job(job_id: str) -> Optional[Job]:
    """작업 조회"""
    return _jobs.get(job_id)


async def run_job_async(
    job: Job,
    func: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> None:
    """백그라운드에서 동기 함수를 실행하고 결과를 job에 저장"""
    job.status = JobStatus.RUNNING
    try:
        result = await asyncio.to_thread(func, *args, **kwargs)
        job.result = result
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        logger.info("작업 %s 완료", job.id)
    except Exception as e:
        job.error = str(e)
        job.status = JobStatus.FAILED
        job.completed_at = datetime.utcnow()
        logger.error("작업 %s 실패: %s", job.id, e, exc_info=True)
