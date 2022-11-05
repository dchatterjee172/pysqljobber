import argparse
import asyncio
import logging
import random
import sqlite3
import time
import traceback
import uuid
from contextlib import closing
from pathlib import Path
from typing import Any, Callable, Dict, Generator, Iterator, List, Optional, Tuple

import aiohttp
import yaml
from pydantic import BaseModel
from rich.logging import RichHandler
from rich.progress import Progress, Text, TextColumn

from pysqljobber.api.schema import CreateJobResponse, GetJobResultResponse
from pysqljobber.job_queue import JobStatus

logging.basicConfig(level="INFO", handlers=[RichHandler(level="INFO")])
logger = logging.getLogger()


class ReqResponseLogger:
    def __init__(self, db_path: str):
        self.db_conn: sqlite3.Connection = sqlite3.connect(db_path)
        with self.db_conn:
            self.db_conn.executescript(
                """
                create table job_requests (
                    request_id text not null,
                    job_id text,
                    is_queued integer,
                    status_code integer,
                    response_received_at numeric,
                    error_response_body text,
                    python_exception text
                );
                create table job_responses (
                    request_id text not null,
                    job_id text not null,
                    task_name text,
                    queue_name text,
                    job_status text,
                    received_at numeric,
                    queued_at numeric,
                    dequeued_at numeric,
                    completed_at numeric,
                    job_result text,
                    error_msg text,
                    status_code integer,
                    response_received_at numeric,
                    error_response_body text,
                    python_exception text
                );
                """
            )

    def log_job_responses(
        self,
        request_id: str,
        job_id: Optional[str] = None,
        task_name: Optional[str] = None,
        queue_name: Optional[str] = None,
        job_status: Optional[JobStatus] = None,
        received_at: Optional[float] = None,
        queued_at: Optional[float] = None,
        dequeued_at: Optional[float] = None,
        completed_at: Optional[float] = None,
        job_result: Optional[str] = None,
        error_msg: Optional[str] = None,
        status_code: Optional[int] = None,
        response_received_at: Optional[float] = None,
        error_response_body: Optional[str] = None,
        python_exception: Optional[str] = None,
    ):
        with self.db_conn:
            self.db_conn.execute(
                f"""
                insert into job_responses
                values({','.join(['?'] * 15)})
                """,
                (
                    request_id,
                    job_id,
                    task_name,
                    queue_name,
                    job_status.value,
                    received_at,
                    queued_at,
                    dequeued_at,
                    completed_at,
                    job_result,
                    error_msg,
                    status_code,
                    response_received_at,
                    error_response_body,
                    python_exception,
                ),
            )

    def log_job_requests(
        self,
        request_id: str,
        status_code: Optional[int] = None,
        response_received_at: Optional[float] = None,
        job_id: Optional[str] = None,
        is_queued: Optional[bool] = None,
        error_response_body: Optional[str] = None,
        python_exception: Optional[str] = None,
    ):
        with self.db_conn:
            self.db_conn.execute(
                f"""
                insert into job_requests
                values({','.join(['?'] * 7)})
                """,
                (
                    request_id,
                    job_id,
                    is_queued,
                    status_code,
                    response_received_at,
                    error_response_body,
                    python_exception,
                ),
            )

    def close(self):
        self.db_conn.close()


class SubmittedJob(BaseModel):
    request_id: str
    job_id: str
    response_received_at: float


class SpeedColumn(TextColumn):
    def __init__(self, unit: str = "req"):
        super().__init__("")
        self._unit = unit

    def render(self, task: "Task") -> Text:
        if task.speed is None:
            return Text("no speed")
        return Text(f"{task.speed:.3f} {self._unit}/s")


class TestData(BaseModel):
    task_name: str
    result_db: str
    expected_result: List[Dict[str, Any]]
    job_args: Optional[Dict] = None
    job_id: Optional[str] = None


def load_test_data(test_data_file: Path) -> List[TestData]:
    test_data: List[TestData] = []

    if not args.test_data.exists():
        raise ValueError(f"{args.test_data!r} does not exist.")

    with open(test_data_file, encoding="utf-8") as f:
        for datum in yaml.safe_load(f):
            test_data.append(TestData.parse_obj(datum))

    return test_data


def generate_random_task_stream(
    seed: int, test_data: List[TestData], limit: int
) -> Generator[TestData, None, None]:
    rand = random.Random(seed)
    choices = list(range(len(test_data)))
    for _ in range(limit):
        yield test_data[rand.choice(choices)]


async def submit_job(
    test_data_iterator: Iterator[TestData],
    concurrency: int,
    progress_bar_tick: Callable[[], None],
    pysqljobber_api_host: str,
    session: aiohttp.ClientSession,
    submitted_jobs_queue: asyncio.PriorityQueue[Tuple[int, SubmittedJob]],
    submitted_all_job: asyncio.Event,
    req_resp_logger: ReqResponseLogger,
):
    post_job_url = pysqljobber_api_host.strip("/") + "/jobs"

    async def worker():
        for data in test_data_iterator:
            req_id = uuid.uuid4().hex
            try:
                payload = {"task_name": data.task_name}
                if data.job_args is not None:
                    payload["job_args"] = data.job_args
                if data.job_id is not None:
                    payload["job_id"] = data.job_id
                async with session.post(post_job_url, json=payload) as response:
                    response_received_at = time.time()
                    status = response.status
                    if status in (201, 200):
                        create_job_response = CreateJobResponse.parse_obj(
                            await response.json()
                        )
                        if create_job_response.is_queued:
                            priority = int(response_received_at * 10000)
                            await submitted_jobs_queue.put(
                                (
                                    priority,
                                    SubmittedJob(
                                        request_id=req_id,
                                        job_id=create_job_response.job_id,
                                        response_received_at=response_received_at,
                                    ),
                                )
                            )
                        req_resp_logger.log_job_requests(
                            request_id=req_id,
                            job_id=create_job_response.job_id,
                            is_queued=create_job_response.is_queued,
                            status_code=status,
                            response_received_at=response_received_at,
                        )
                    else:
                        body = await response.text()
                        logger.exception(body)
                        req_resp_logger.log_job_requests(
                            req_id=req_id,
                            status_code=status,
                            error_response_body=body,
                        )
            except aiohttp.ClientError:
                req_resp_logger.log_job_requests(
                    request_id=req_id, python_exception=traceback.format_exc()
                )
                logger.exception("Failed to send request")
            progress_bar_tick()

    workers = [worker() for _ in range(concurrency)]
    await asyncio.gather(*workers)
    submitted_all_job.set()


async def get_job_status(
    submitted_jobs_queue: asyncio.PriorityQueue[Tuple[int, SubmittedJob]],
    session: aiohttp.ClientSession,
    progress_bar_tick: Callable[[], None],
    concurrency: int,
    pysqljobber_api_host: str,
    submitted_all_job: asyncio.Event,
    req_resp_logger: ReqResponseLogger,
):
    get_job_result_url = pysqljobber_api_host.strip("/") + "/jobs"

    async def worker():
        while True:
            submitted_job = None
            try:
                priority, submitted_job = submitted_jobs_queue.get_nowait()
                payload = {"job_id": submitted_job.job_id}
                async with session.get(get_job_result_url, params=payload) as response:
                    response_received_at = time.time()
                    status = response.status
                    if status == 200:
                        job_response = GetJobResultResponse.parse_obj(
                            await response.json()
                        )
                        job_status = job_response.job_status
                        if job_status not in (
                            JobStatus.COMPLETED,
                            JobStatus.FAILED,
                        ):
                            if (time.time() - submitted_job.response_received_at) < 600:
                                logger.info(
                                    "putting %r (%r) back to queue",
                                    submitted_job.job_id,
                                    job_status,
                                )
                                await submitted_jobs_queue.put(
                                    (
                                        priority,
                                        submitted_job,
                                    )
                                )
                            else:
                                logger.warning(
                                    "not putting %r (%r) back to queue",
                                    submitted_job.job_id,
                                    job_status,
                                )
                        else:
                            progress_bar_tick()
                        req_resp_logger.log_job_responses(
                            request_id=submitted_job.request_id,
                            status_code=status,
                            response_received_at=response_received_at,
                            **job_response.dict(),
                        )
                    else:
                        body = await response.text()
                        logger.exception(body)
                        req_resp_logger.log_job_responses(
                            request_id=submitted_job.request_id,
                            status_code=status,
                            error_response_body=body,
                        )
            except aiohttp.ClientError:
                req_resp_logger.log_job_responses(
                    request_id=submitted_job.request_id,
                    python_exception=traceback.format_exc(),
                )
                logger.exception("Failed to send request")
            except asyncio.QueueEmpty:
                if submitted_all_job.is_set():
                    logger.info("Shutting down worker")
                    break
                await asyncio.sleep(1)
            finally:
                if submitted_job:
                    submitted_jobs_queue.task_done()

    workers = [worker() for _ in range(concurrency)]
    await asyncio.gather(*workers)


async def main(
    submit_job_concurrency: int,
    num_jobs: int,
    db_path: str,
    test_data: Path,
    pysqljobber_api_host: str,
    get_job_status_concurrency: int,
):
    test_data = load_test_data(args.test_data)
    session = aiohttp.ClientSession()
    try:
        with Progress(
            *Progress.get_default_columns(), SpeedColumn()
        ) as progress, closing(ReqResponseLogger(db_path=db_path)) as req_resp_logger:
            submit_job_progress_task_uuid = progress.add_task(
                "[green]Sending jobs...", total=num_jobs
            )
            job_status_progress_task_uuid = progress.add_task(
                "[green]Checking status jobs...", total=num_jobs
            )
            submitted_jobs_queue = asyncio.PriorityQueue(num_jobs)
            submitted_all_job = asyncio.Event()
            submit = submit_job(
                test_data_iterator=generate_random_task_stream(
                    limit=num_jobs,
                    test_data=test_data,
                    seed=1,
                ),
                concurrency=submit_job_concurrency,
                pysqljobber_api_host=pysqljobber_api_host,
                progress_bar_tick=lambda: progress.update(
                    submit_job_progress_task_uuid, advance=1
                ),
                session=session,
                submitted_jobs_queue=submitted_jobs_queue,
                submitted_all_job=submitted_all_job,
                req_resp_logger=req_resp_logger,
            )
            get_status = get_job_status(
                submitted_jobs_queue=submitted_jobs_queue,
                session=session,
                progress_bar_tick=lambda: progress.update(
                    job_status_progress_task_uuid, advance=1
                ),
                concurrency=get_job_status_concurrency,
                pysqljobber_api_host=pysqljobber_api_host,
                submitted_all_job=submitted_all_job,
                req_resp_logger=req_resp_logger,
            )
            await asyncio.gather(submit, get_status)
    finally:
        await session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--submit-job-concurrency", type=int, required=True)
    parser.add_argument("--num-jobs", type=int, required=True)
    parser.add_argument("--db-path", type=Path, default="./test.db")
    parser.add_argument("--test-data", type=Path, default="./test_data.yaml")
    parser.add_argument(
        "--pysqljobber-api-host", type=str, default="http://localhost:8000"
    )
    parser.add_argument("--get-job-status-concurrency", type=int, default=10)
    args = parser.parse_args()
    asyncio.run(
        main(
            submit_job_concurrency=args.submit_job_concurrency,
            num_jobs=args.num_jobs,
            db_path=args.db_path,
            test_data=args.test_data,
            pysqljobber_api_host=args.pysqljobber_api_host,
            get_job_status_concurrency=args.get_job_status_concurrency,
        )
    )
