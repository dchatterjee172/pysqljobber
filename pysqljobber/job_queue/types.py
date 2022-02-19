import enum
import typing

from pydantic import BaseModel


class EnqueuedJob(BaseModel):
    job_id: str
    task_name: str
    job_args: typing.Dict


@enum.unique
class JobStatus(enum.Enum):
    UNKNOWN = "UNKNOWN"
    RECEIVED = "RECEIVED"
    ENQUEUED = "ENQUEUED"
    DEQUEUED = "DEQUEUED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobResult(BaseModel):
    job_id: str
    job_status: JobStatus = JobStatus.UNKNOWN
    received_at: typing.Optional[float] = None
    queued_at: typing.Optional[float] = None
    dequeued_at: typing.Optional[float] = None
    completed_at: typing.Optional[float] = None
    job_result: typing.Optional[str] = None
    error_msg: typing.Optional[str] = None

    class Config:
        validate_assignment = True
