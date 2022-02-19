from pydantic import BaseModel, constr


class TaskSettings(BaseModel):
    compute_db: constr(regex=r"^[a-zA-Z0-9-_]{1,32}$")
    result_db: constr(regex=r"^[a-zA-Z0-9-_]{1,32}$")


class Task(BaseModel):
    name: constr(regex=r"^[a-zA-Z0-9-_]{1,32}$")
    settings: TaskSettings
    sql: constr(min_length=1)
