import asyncio
import inspect
import json
import signal
import time
import typing
from functools import partial

from .broker import Broker
from .inflight_job import InFlightJobController
from .logger import logger
from .result_store import ResultStore
from .types import JobResult, JobStatus

RESULT_TTL = 300


async def _task_wrapper(
    function: typing.Callable, job_result: JobResult, **kwargs
) -> JobResult:
    serialized_result = None
    error_msg = None
    try:
        if inspect.iscoroutinefunction(function):
            result = await function(**kwargs)
        else:
            result = await asyncio.to_thread(function, **kwargs)
        status = JobStatus.COMPLETED
        serialized_result = json.dumps(result)
    except Exception as ex:
        status = JobStatus.FAILED
        error_msg = str(ex)
        logger.exception("job %r failed", job_result.job_id)
    completed_at = time.time()
    job_result = job_result.copy()
    job_result.job_status = status
    job_result.job_result = serialized_result
    job_result.error_msg = error_msg
    job_result.completed_at = completed_at
    return job_result


def _task_not_found(
    job_result: JobResult,
):
    job_result = job_result.copy()
    job_result.job_status = JobStatus.FAILED
    job_result.error_msg = f"task {job_result.task_name!r} is not registered."
    return job_result


class Worker:
    def __init__(
        self,
        broker_url: str,
        result_backend_url: str,
        queue: typing.Optional[str] = None,
        concurrency: int = 4,
    ):
        self._registered_tasks: typing.Dict = {}
        self._result_store = ResultStore(result_backend_url)
        self._broker = Broker(broker_url)
        self._inflight_job = InFlightJobController(broker_url)
        self._queue = queue
        self._concurrency = concurrency

        self.stop = False

    def register_task(self, task_name: str):
        if task_name in self._registered_tasks:
            raise ValueError(f"task name {task_name!r} is already registered")

        def decorator(function: typing.Callable):
            self._registered_tasks[task_name] = partial(
                _task_wrapper, function=function
            )
            return function

        return decorator

    def _signal_handler(self, signal_int, *args):
        signal_name = signal.Signals(signal_int).name
        logger.info("received %r. shutting down worker", signal_name)
        self.stop = True

    async def _run(self):
        while not self.stop:
            job = await self._broker.dequeue_job(queue_name=self._queue)
            if job is None:
                logger.debug("no job received, sleeping.")
                await asyncio.sleep(1)
                continue
            job_result = await self._inflight_job.get_job_status(job_id=job.job_id)
            if job_result is None:
                logger.error("no inflight job entry for %r ignoring", job.job_id)
            try:
                logger.debug("executing job %r", job.job_id)
                if job.task_name not in self._registered_tasks:
                    logger.warning(
                        "task name not recognized %r ignoring.", job.task_name
                    )
                    await self._result_store.store_result(
                        result=_task_not_found(job_result=job_result), ttl=RESULT_TTL
                    )
                else:
                    task = self._registered_tasks[job.task_name]
                    job_result = await task(job_result=job_result, **job.job_args)
                    logger.debug("executing completed for job %r", job.job_id)
                    await self._result_store.store_result(
                        result=job_result, ttl=RESULT_TTL
                    )
                    logger.debug("result of job %r stored", job.job_id)
            finally:
                await self._inflight_job.set_done_job(job_id=job.job_id)

    async def run(self):
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        await asyncio.gather(*[self._run() for _ in range(self._concurrency)])
