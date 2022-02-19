import time
from typing import Optional

import aioredis

from .namespace import INFLIGHT_JOB_NAMESPACE, QUEUE_NAMESPACE
from .redis_client import from_url
from .types import EnqueuedJob, JobResult, JobStatus


class InFlightJobController:
    def __init__(self, broker_url: str):
        self._redis: aioredis.Redis = from_url(
            broker_url, encoding="utf-8", decode_responses=True
        )

    async def set_received_job(
        self, job_id: str, task_name: str, queue_name: str
    ) -> bool:
        received_at = time.time()
        name = INFLIGHT_JOB_NAMESPACE(job_id)
        is_set = await self._redis.hsetnx(
            name=name, key="job_status", value=JobStatus.RECEIVED.value
        )
        if not is_set:
            return False
        payload = {
            "received_at": received_at,
            "task_name": task_name,
            "queue_name": queue_name,
        }
        await self._redis.hset(name=name, mapping=payload)
        return True

    async def queue_job(self, job: EnqueuedJob, queue_name: str):
        queue_name = QUEUE_NAMESPACE(queue_name)
        queue_payload = job.json(exclude_none=True)
        queued_at = time.time()
        status_name = INFLIGHT_JOB_NAMESPACE(job.job_id)
        status_payload = {
            "job_status": JobStatus.ENQUEUED.value,
            "queued_at": queued_at,
        }

        async def tx(pipe: aioredis.client.Pipeline):
            await pipe.lpush(queue_name, queue_payload).hset(
                status_name, mapping=status_payload
            )

        result = await self._redis.transaction(func=tx)
        if not isinstance(result, list) or len(result) != 2 or not all(result):
            raise ValueError(f"unexpected value for result {result!r}")

    async def set_dequeued_job(self, job_id: str):
        dequeued_at = time.time()
        name = INFLIGHT_JOB_NAMESPACE(job_id)
        payload = {
            "job_status": JobStatus.DEQUEUED.value,
            "dequeued_at": dequeued_at,
        }
        await self._redis.hset(name=name, mapping=payload)

    async def set_done_job(self, job_id: str):
        name = INFLIGHT_JOB_NAMESPACE(job_id)
        await self._redis.delete(name)

    async def get_job_status(self, job_id) -> Optional[JobResult]:
        name = INFLIGHT_JOB_NAMESPACE(job_id)
        payload = await self._redis.hgetall(name)
        if len(payload) == 0:
            return None
        return JobResult(job_id=job_id, **payload)
