import asyncio
import logging

from pysqljobber.job_queue import Worker

logging.basicConfig(level=logging.DEBUG)

worker = Worker(
    broker_url="redis://localhost", result_backend_url="redis://localhost", num_worker=1
)


@worker.register_task(task_name="add")
def add(a: int, b: int) -> int:
    return a + b


asyncio.run(worker.run())
