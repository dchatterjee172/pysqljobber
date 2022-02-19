from typing import Any, Dict, Optional

from pydantic import BaseModel, constr

from pysqljobber.job_queue import JobResult


class CreateJobRequest(BaseModel):
    task_name: constr(regex=r"^[a-zA-Z0-9-_]{1,32}$")
    job_id: Optional[constr(regex=r"^[a-zA-Z0-9-_]{1,32}$")] = None
    queue_name: Optional[constr(regex=r"^[a-zA-Z0-9-_]{1,32}$")] = None
    job_args: Optional[Dict[str, Any]] = None


class CreateJobResponse(BaseModel):
    job_id: str
    is_queued: bool


class GetJobResultResponse(JobResult):
    ...
