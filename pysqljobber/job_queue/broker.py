import random
import time
import typing

import aioredis

from .inflight_job import InFlightJobController
from .namespace import QUEUE_NAMESPACE, QUEUE_PATTERN
from .types import EnqueuedJob


class Broker:
    def __init__(self, broker_url: str):
        self.redis = aioredis.from_url(
            broker_url, encoding="utf-8", decode_responses=True
        )
        self.inflight_job = InFlightJobController(broker_url)

    async def enqueue_job(
        self, job_id: str, task_name: str, queue_name: str, job_args: typing.Dict
    ) -> bool:
        received_at = time.time()
        is_set = await self.inflight_job.set_received_job(job_id, received_at)
        if not is_set:
            return False
        payload = EnqueuedJob(
            job_id=job_id, task_name=task_name, job_args=job_args
        ).json()
        queue = QUEUE_NAMESPACE(queue_name)
        await self.redis.lpush(queue, payload)
        queued_at = time.time()
        await self.inflight_job.set_queued_job(job_id, queued_at)
        return True

    async def get_all_queues(self):
        return await self.redis.keys(pattern=QUEUE_PATTERN)

    async def dequeue_job(
        self, queue_name: typing.Optional[str] = None
    ) -> typing.Optional[EnqueuedJob]:
        if queue_name is None:
            available_queues = await self.get_all_queues()
            if len(available_queues) == 0:
                return None
            queue = random.choice(available_queues)
        else:
            queue = QUEUE_NAMESPACE(queue_name)
        payload = await self.redis.rpop(queue)
        dequeued_at = time.time()
        if payload is None:
            return None
        job_packet = EnqueuedJob.parse_raw(payload)
        await self.inflight_job.set_dequeued_job(job_packet.job_id, dequeued_at)
        return job_packet
