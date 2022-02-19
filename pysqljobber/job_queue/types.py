import enum
from typing import Dict, Optional

from pydantic import BaseModel, Field


class EnqueuedJob(BaseModel):
    job_id: str
    task_name: str
    job_args: Optional[Dict] = Field(default_factory=dict)


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
    task_name: str
    queue_name: str
    job_status: JobStatus = JobStatus.UNKNOWN
    received_at: Optional[float] = None
    queued_at: Optional[float] = None
    dequeued_at: Optional[float] = None
    completed_at: Optional[float] = None
    job_result: Optional[str] = None
    error_msg: Optional[str] = None

    class Config:
        validate_assignment = True
