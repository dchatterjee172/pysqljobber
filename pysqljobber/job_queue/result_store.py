import typing

import aioredis

from .namespace import ROOT, Namespace
from .redis_client import from_url
from .types import JobResult

RESULT = Namespace(ROOT("result_store"))


class ResultStore:
    def __init__(self, result_backend_url: str):
        self._redis: aioredis.Redis = from_url(
            result_backend_url, encoding="utf-8", decode_responses=True
        )

    async def store_result(self, result: JobResult, ttl: int):
        job_id = result.job_id
        name = RESULT(job_id)
        value = result.json()
        await self._redis.set(name, value, ex=ttl)

    async def get_job_result(self, job_id: str) -> typing.Optional[JobResult]:
        name = RESULT(job_id)
        value = await self._redis.get(name)
        if value is None:
            return value
        return JobResult.parse_raw(value)
