import typing

from .broker import Broker
from .inflight_job import InFlightJobController
from .result_store import ResultStore
from .types import JobResult

DEFAULT_QUEUE = "default_queue"


class JobQueue:
    def __init__(self, broker_url: str, result_backend_url: str):
        self.broker = Broker(broker_url)
        self.result_store = ResultStore(result_backend_url)
        self.inflight_job = InFlightJobController(broker_url)

    async def enqueue_job(
        self,
        job_id: str,
        task_name: str,
        queue_name: typing.Optional[str] = DEFAULT_QUEUE,
        job_args: typing.Optional[typing.Dict] = None,
    ) -> bool:
        job_args = {} if job_args is None else job_args
        queue_name = queue_name or DEFAULT_QUEUE
        return await self.broker.enqueue_job(
            job_id=job_id, task_name=task_name, queue_name=queue_name, job_args=job_args
        )

    async def get_job_result(self, job_id: str) -> typing.Optional[JobResult]:
        job_result = await self.inflight_job.get_job_status(job_id)
        if job_result is not None:
            return job_result
        return await self.result_store.get_job_result(job_id)
