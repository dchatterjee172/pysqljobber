import asyncio
import typing
import uuid
from functools import partial

from pydantic import BaseModel

from pysqljobber.config_file import Config
from pysqljobber.job_queue import Worker as JobQueueWorker
from pysqljobber.logger import logger
from pysqljobber.task import Task

from .multi_dsn_connection_pool import ConnectionPool

_TYPE_CODES_TO_TYPE_NAME: typing.Dict[int, str] = {}


class _ResultDbTableConfig(BaseModel):
    create_query: str
    copy_query: str


async def _type_code_to_type_name(
    type_codes: typing.List[int], cursor
) -> typing.List[str]:
    unknown_type_codes = [
        code for code in type_codes if code not in _TYPE_CODES_TO_TYPE_NAME
    ]

    if unknown_type_codes:
        logger.debug("getting type names for %r", unknown_type_codes)
        sql = "select oid, typname from pg_type where oid = any(%(type_codes)s);"
        await cursor.execute(sql, params={"type_codes": unknown_type_codes})
        rows = await cursor.fetchall()
        _TYPE_CODES_TO_TYPE_NAME.update({row[0]: row[1] for row in rows})

    type_names = [_TYPE_CODES_TO_TYPE_NAME[code] for code in type_codes]
    return type_names


async def _get_result_column_name_and_types(
    cursor_description, cursor
) -> typing.Dict[str, str]:
    cols = [col.name for col in cursor_description]
    type_codes = [col.type_code for col in cursor_description]
    type_names = await _type_code_to_type_name(type_codes, cursor=cursor)
    return dict(zip(cols, type_names))


def _get_result_table_info(
    table_name: str, col_name_and_types: typing.Dict[str, str]
) -> _ResultDbTableConfig:
    create_table_sql_query = """
    CREATE UNLOGGED TABLE {table_name} ({column_name_type_spec})
    """
    column_name_type_spec = ",".join(
        f"{col_name} {col_type}" for col_name, col_type in col_name_and_types.items()
    )
    create_table_sql_query = create_table_sql_query.format(
        table_name=table_name, column_name_type_spec=column_name_type_spec
    )

    copy_values_sql_query = """
        COPY {table_name} ({column_name_spec}) FROM STDIN
    """

    column_name_spec = ",".join(col_name_and_types.keys())

    copy_values_sql_query = copy_values_sql_query.format(
        table_name=table_name,
        column_name_spec=column_name_spec,
    )

    return _ResultDbTableConfig(
        create_query=create_table_sql_query, copy_query=copy_values_sql_query
    )


async def _task_wrapper(
    config: Config, task: Task, connection_pool: ConnectionPool, **job_args
) -> typing.Dict[str, str]:

    result_table_name = f"{task.name}_{uuid.uuid4().hex}"

    compute_db_name = task.settings.compute_db
    compute_db_dsn = config.compute_db_configs[compute_db_name].dsn

    async with connection_pool.connection(compute_db_dsn) as connection:
        async with connection.cursor() as cur:
            logger.debug("executing sql query for task %r", task.name)
            await cur.execute(task.sql, params=job_args)
            cursor_description = cur.description
            logger.debug("fetching data for task %r", task.name)
            rows = await cur.fetchall()
            result_col_name_and_types = await _get_result_column_name_and_types(
                cursor_description=cursor_description, cursor=cur
            )
            result_table_config = _get_result_table_info(
                table_name=result_table_name,
                col_name_and_types=result_col_name_and_types,
            )

    result_db_name = task.settings.result_db
    result_db_dsn = config.result_db_configs[result_db_name].dsn

    async with connection_pool.connection(result_db_dsn) as connection:
        async with connection.cursor() as cur:
            logger.debug("storing result for task %r", task.name)
            await cur.execute(result_table_config.create_query)
            async with cur.copy(result_table_config.copy_query) as copy:
                for row in rows:
                    await copy.write_row(row)

    return {"table_name": result_table_name}


def run(
    config: Config,
    tasks: typing.List[Task],
    queue_name: typing.Optional[str] = None,
    concurrency: int = 4,
):

    connection_pool: ConnectionPool = ConnectionPool(
        len(config.compute_db_configs) + len(config.result_db_configs)
    )

    for task in tasks:
        if task.settings.compute_db not in config.compute_db_configs:
            raise ValueError()
        if task.settings.result_db not in config.result_db_configs:
            raise ValueError()

    worker = JobQueueWorker(
        broker_url=config.task_queue_config.broker_url,
        result_backend_url=config.task_queue_config.result_backend_url,
        queue=queue_name,
        concurrency=concurrency,
    )

    for task in tasks:
        worker.register_task(task_name=task.name)(
            partial(
                _task_wrapper,
                config=config,
                task=task,
                connection_pool=connection_pool,
            )
        )

    asyncio.run(worker.run())
