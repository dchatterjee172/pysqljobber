import typing

import aioredis

from .namespace import INFLIGHT_JOB_NAMESPACE
from .types import JobResult, JobStatus


class InFlightJobController:
    def __init__(self, broker_url: str):
        self.redis = aioredis.from_url(
            broker_url, encoding="utf-8", decode_responses=True
        )

    async def set_received_job(self, job_id: str, received_at: float) -> bool:
        name = INFLIGHT_JOB_NAMESPACE(job_id)
        is_set = await self.redis.hsetnx(name=name, key="job_id", value=job_id)
        if not is_set:
            return False
        payload = {
            "job_status": JobStatus.RECEIVED.value,
            "received_at": received_at,
        }
        await self.redis.hset(name=name, mapping=payload)
        return True

    async def set_queued_job(self, job_id: str, queued_at: float):
        name = INFLIGHT_JOB_NAMESPACE(job_id)
        payload = {
            "job_status": JobStatus.ENQUEUED.value,
            "queued_at": queued_at,
        }
        await self.redis.hset(name=name, mapping=payload)

    async def set_dequeued_job(self, job_id: str, dequeued_at: float):
        name = INFLIGHT_JOB_NAMESPACE(job_id)
        payload = {
            "job_status": JobStatus.DEQUEUED.value,
            "dequeued_at": dequeued_at,
        }
        await self.redis.hset(name=name, mapping=payload)

    async def set_done_job(self, job_id: str):
        name = INFLIGHT_JOB_NAMESPACE(job_id)
        await self.redis.delete(name)

    async def get_job_status(self, job_id) -> typing.Optional[JobResult]:
        name = INFLIGHT_JOB_NAMESPACE(job_id)
        payload = await self.redis.hgetall(name)
        if len(payload) == 0:
            return None
        return JobResult(**payload)
