import logging
import typing
from pathlib import Path

import rich_click as click

from pysqljobber import api, worker
from pysqljobber.config_file import parse_config_file
from pysqljobber.logger import add_cli_handler
from pysqljobber.sql_dir import get_all_tasks_in_dir


@click.group()
@click.option("--debug/--no-debug", default=False, show_default=True)
def cli(debug: bool):
    click.echo(f"Debug logging is {'on' if debug else 'off'}")
    add_cli_handler(level=logging.DEBUG if debug else logging.INFO)


@cli.command(name="worker")
@click.option(
    "--sql-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
)
@click.option(
    "--config-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option(
    "--queue-name",
    type=str,
)
@click.option("--concurrency", type=int, default=4, show_default=True)
def run_worker(
    sql_dir: Path,
    config_file: Path,
    queue_name: typing.Optional[str],
    concurrency: int,
):
    click.echo("Starting worker")
    config = parse_config_file(config_file)
    tasks = get_all_tasks_in_dir(sql_dir)
    worker.run(
        config=config, tasks=tasks, queue_name=queue_name, concurrency=concurrency
    )


@cli.command()
@click.option("--host", type=str, default="127.0.0.1", show_default=True)
@click.option("--port", type=int, default=8000, show_default=True)
@click.option(
    "--config-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
def api_server(host: str, port: int, config_file: Path):
    click.echo("Starting API control plane")
    config = parse_config_file(config_file)
    api.run(host=host, port=port, config=config)
