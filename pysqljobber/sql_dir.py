import typing
from pathlib import Path

from .task import Task, TaskSettings
from .yesqlparser import parse_file


def get_all_tasks_in_dir(path: Path) -> typing.List[Task]:
    tasks = {}

    for file_path in path.glob("*.sql"):
        with open(file_path, encoding="utf-8") as file_:
            queries = parse_file(file_)
            tasks_in_file = {
                query.name: Task(
                    name=query.name, sql=query.sql, settings=TaskSettings(**query.tags)
                )
                for query in queries
            }

        tasks_already_present = tasks.keys() & tasks_in_file.keys()
        if len(tasks_already_present) > 0:
            raise ValueError(f"{tasks_already_present} tasks already seen")

        tasks.update(tasks_in_file)

    return list(tasks.values())
