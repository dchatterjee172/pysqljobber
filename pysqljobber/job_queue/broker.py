import random
import re
from typing import Dict, Optional

import aioredis

from .inflight_job import InFlightJobController
from .logger import logger
from .namespace import QUEUE_NAMESPACE, QUEUE_PATTERN
from .redis_client import from_url
from .types import EnqueuedJob

VALIDATION_REGEX = re.compile(r"^[a-zA-Z0-9-_]{1,32}$")


def _validate_string(string: str, entity_name: str):
    if not VALIDATION_REGEX.match(string):
        raise ValueError(
            f"{string!r} is not a valid value for {entity_name!r}."
            f"Please ensure {entity_name!r} follows pattern {VALIDATION_REGEX!r}"
        )


class Broker:
    def __init__(self, broker_url: str):
        self._redis: aioredis.Redis = from_url(
            broker_url, encoding="utf-8", decode_responses=True
        )
        self.inflight_job = InFlightJobController(broker_url)

    async def enqueue_job(
        self,
        job_id: str,
        task_name: str,
        queue_name: str,
        job_args: Optional[Dict],
    ) -> bool:

        logger.debug("adding job %r to queue", job_id)

        _validate_string(job_id, "job_id")
        _validate_string(task_name, "task_name")
        _validate_string(queue_name, "queue_name")

        is_set = await self.inflight_job.set_received_job(
            job_id, task_name=task_name, queue_name=queue_name
        )
        if not is_set:
            return False

        job = EnqueuedJob(job_id=job_id, task_name=task_name, job_args=job_args)
        await self.inflight_job.queue_job(job, queue_name=queue_name)
        logger.debug("pushed job %r to queue %r", job.job_id, queue_name)
        return True

    async def get_all_queues(self):
        return await self._redis.keys(pattern=QUEUE_PATTERN)

    async def dequeue_job(
        self, queue_name: Optional[str] = None
    ) -> Optional[EnqueuedJob]:
        if queue_name is None:
            available_queues = await self.get_all_queues()
            if len(available_queues) == 0:
                return None
            queue = random.choice(available_queues)
        else:
            queue = QUEUE_NAMESPACE(queue_name)
        payload = await self._redis.rpop(queue)
        if payload is None:
            return None
        job_packet = EnqueuedJob.parse_raw(payload)
        await self.inflight_job.set_dequeued_job(job_packet.job_id)
        return job_packet
