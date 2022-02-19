from pydantic import BaseModel


class TaskSettings(BaseModel):
    compute_db: str = ""
    result_db: str = ""


class Task(BaseModel):
    name: str
    settings: TaskSettings
    sql: str = ""
