import asyncio
import json
import logging
import time
import typing
from functools import partial

from .broker import Broker
from .inflight_job import InFlightJobController
from .result_store import ResultStore
from .types import JobResult, JobStatus

logger = logging.getLogger(__name__)


def _task_wrapper(
    function: typing.Callable, job_result: JobResult, **kwargs
) -> JobResult:
    serialized_result = None
    error_msg = None
    try:
        result = function(**kwargs)
        status = JobStatus.COMPLETED
        serialized_result = json.dumps(result)
    except Exception as ex:
        status = JobStatus.FAILED
        error_msg = str(ex)
    completed_at = time.time()
    job_result = job_result.copy()
    job_result.job_status = status
    job_result.job_result = serialized_result
    job_result.error_msg = error_msg
    job_result.completed_at = completed_at
    return job_result


class Worker:
    def __init__(
        self,
        broker_url: str,
        result_backend_url: str,
        queue: typing.Optional[str] = None,
        num_worker: int = 4,
    ):
        self.registered_tasks: typing.Dict = {}
        self.result_store = ResultStore(result_backend_url)
        self.broker = Broker(broker_url)
        self.inflight_job = InFlightJobController(broker_url)
        self.queue = queue
        self.num_worker = num_worker

    def register_task(self, task_name: str):
        if task_name in self.registered_tasks:
            raise ValueError(f"task name {task_name} is already registered")

        def decorator(function: typing.Callable):
            self.registered_tasks[task_name] = partial(_task_wrapper, function=function)
            return function

        return decorator

    async def _run(self):
        while True:
            job = await self.broker.dequeue_job(queue_name=self.queue)
            if job is None:
                logger.info("no job received, sleeping.")
                await asyncio.sleep(1)
                continue
            if job.task_name not in self.registered_tasks:
                logger.warning("task name not recognized\n%s\nignoring.", job)
                continue
            task = self.registered_tasks[job.task_name]
            job_result = await self.inflight_job.get_job_status(job_id=job.job_id)
            if job_result is None:
                job_result = JobResult(job_id=job.job_id)
            try:
                logger.debug("executing job %s", job.job_id)
                job_result = await asyncio.to_thread(
                    task, job_result=job_result, **job.job_args
                )
                logger.debug("executing completed for job %s", job.job_id)
                await self.result_store.store_result(result=job_result, ttl=300)
                logger.debug("result of job %s stored", job.job_id)
            finally:
                await self.inflight_job.set_done_job(job_id=job.job_id)

    async def run(self):
        await asyncio.gather(*[self._run() for _ in range(self.num_worker)])
