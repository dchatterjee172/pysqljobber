import typing
from pathlib import Path

import rich_click as click

from pysqljobber import api
from pysqljobber.config_file import parse_config_file
from pysqljobber.sql_dir import get_all_tasks_in_dir


@click.group()
def cli():
    ...


@cli.command()
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
def worker(sql_dir: Path, config_file: Path, queue_name: typing.Optional[str]):
    click.echo("Starting worker")
    config = parse_config_file(config_file)
    print(config.json(indent=1))
    tasks = get_all_tasks_in_dir(sql_dir)
    for task in tasks.values():
        print(task.json(indent=1))


@cli.command()
@click.option("--host", type=str, default="localhost", show_default=True)
@click.option("--port", type=int, default=8000, show_default=True)
@click.option(
    "--config-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
def api_server(host: str, port: int, config_file: Path):
    click.echo("Starting API control plane")
    config = parse_config_file(config_file)
    print(config.json(indent=1))
    api.run(host=host, port=port, config=config)
