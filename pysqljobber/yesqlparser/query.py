import typing

from pydantic import BaseModel, Field


class Query(BaseModel):
    name: str
    sql: str = ""
    tags: typing.Dict[str, str] = Field(default_factory=dict)
