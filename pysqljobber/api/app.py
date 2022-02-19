import typing
import uuid

import uvicorn
from fastapi import Depends, FastAPI, HTTPException

from pysqljobber.config_file import Config
from pysqljobber.job_queue import JobQueue

from . import schema

app = FastAPI(docs_url="/")
_job_queue: typing.Optional[JobQueue] = None


def get_job_queue() -> JobQueue:
    global _job_queue
    if _job_queue is None:
        raise Exception()
    return _job_queue


@app.post(
    "/jobs",
    response_model=schema.CreateJobResponse,
)
async def create_job(
    job: schema.CreateJobRequest, job_queue: JobQueue = Depends(get_job_queue)
):
    job_id = job.job_id if job.job_id is not None else uuid.uuid4().hex
    is_queued = await job_queue.enqueue_job(
        job_id=job_id,
        task_name=job.task_name,
        queue_name=job.queue_name,
        job_args=job.job_args,
    )
    return schema.CreateJobResponse(job_id=job_id, is_queued=is_queued)


@app.get(
    "/jobs",
    response_model=schema.GetJobResultResponse,
)
async def get_job_result(job_id: str, job_queue: JobQueue = Depends(get_job_queue)):
    result = await job_queue.get_job_result(job_id=job_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"job_id {job_id} not found")
    return result


def run(host: str, port: int, config: Config):
    global _job_queue
    _job_queue = JobQueue(
        broker_url=config.task_queue_config.broker_url,
        result_backend_url=config.task_queue_config.result_backend_url,
    )
    uvicorn.run("pysqljobber.api.app:app", host=host, port=port, loop="uvloop")
