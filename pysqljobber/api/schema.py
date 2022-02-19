import typing

from pydantic import BaseModel, Field

from pysqljobber.job_queue import JobResult


class CreateJobRequest(BaseModel):
    job_id: typing.Optional[str] = None
    task_name: str
    queue_name: typing.Optional[str] = None
    job_args: typing.Dict[str, typing.Any] = Field(default_factory=dict)


class CreateJobResponse(BaseModel):
    job_id: str
    is_queued: bool


class GetJobResultResponse(JobResult):
    ...
