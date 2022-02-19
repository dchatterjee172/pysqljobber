import typing
from pathlib import Path

import toml
from pydantic import BaseModel, constr


class TaskQueueConfig(BaseModel):
    broker_url: constr(min_length=1)
    result_backend_url: constr(min_length=1)


class ResultDbConfig(BaseModel):
    name: constr(regex=r"^[a-zA-Z0-9-_]{1,32}$")
    dsn: constr(min_length=1)


class ComputeDbConfig(BaseModel):
    name: constr(regex=r"^[a-zA-Z0-9-_]{1,32}$")
    dsn: constr(min_length=1)


class Config(BaseModel):
    task_queue_config: TaskQueueConfig
    result_db_configs: typing.Dict[str, ResultDbConfig]
    compute_db_configs: typing.Dict[str, ComputeDbConfig]


TASK_QUEUE = "task_queue"
RESULT_DB = "result_db"
COMPUTE_DB = "compute_db"


def parse_config_file(path: Path) -> Config:
    with open(path, encoding="utf-8") as file_:
        raw_config = toml.load(file_)

    if TASK_QUEUE not in raw_config:
        raise ValueError(f"{TASK_QUEUE} section not present")

    task_queue_config = TaskQueueConfig(**raw_config[TASK_QUEUE])

    if RESULT_DB not in raw_config:
        raise ValueError(f"{RESULT_DB} section not present")

    result_db_configs = {}
    for name, config in raw_config[RESULT_DB].items():
        result_db_configs[name] = ResultDbConfig(name=name, **config)

    if COMPUTE_DB not in raw_config:
        raise ValueError(f"{COMPUTE_DB} section not present")

    compute_db_configs = {}
    for name, config in raw_config[COMPUTE_DB].items():
        compute_db_configs[name] = ComputeDbConfig(name=name, **config)

    return Config(
        task_queue_config=task_queue_config,
        result_db_configs=result_db_configs,
        compute_db_configs=compute_db_configs,
    )
