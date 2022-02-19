import asyncio
import time

from pysqljobber.job_queue import JobQueue

loop = asyncio.get_event_loop()

job_queue = JobQueue(
    broker_url="redis://localhost", result_backend_url="redis://localhost"
)

tasks = loop.run_until_complete(job_queue.get_all_registered_tasks())
print(tasks)


enqueue = job_queue.enqueue_job(
    job_id="a",
    task_name="add",
    job_args={"a": 1, "b": 2},
)
job_status = job_queue.get_job_result(job_id="a")
loop.run_until_complete(enqueue)
status = loop.run_until_complete(job_status)
print(status)
time.sleep(2)
job_result = loop.run_until_complete(job_queue.get_job_result(job_id="a"))
print(job_result)
