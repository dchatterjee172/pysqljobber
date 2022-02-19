import typing

from pydantic import BaseModel, Field, constr


class Query(BaseModel):
    name: constr(min_length=1)
    sql: str = ""
    tags: typing.Dict[str, str] = Field(default_factory=dict)
