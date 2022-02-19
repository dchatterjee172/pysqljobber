import enum
import re

from pydantic import BaseModel

TAG_REGEX = re.compile(r"^\s*--\s*(.+)\s*:\s*(.+)")
COMMENT_REGEX = re.compile(r"`^\s*--\s*(.*)")


class LineType(enum.Enum):
    TAG = enum.auto()
    COMMENT = enum.auto()
    SQL = enum.auto()
    EMPTY_LINE = enum.auto()


class ParsedLine(BaseModel):
    type: LineType
    tag: str = ""
    value: str = ""


def parse_line(line: str) -> ParsedLine:
    line = line.strip()

    if line == "":
        return ParsedLine(type=LineType.EMPTY_LINE)

    match = TAG_REGEX.match(line)
    if match:
        tag, value = match.group(1, 2)
        return ParsedLine(type=LineType.TAG, tag=tag, value=value)

    match = COMMENT_REGEX.match(line)
    if match:
        comment = match.group(1)
        return ParsedLine(type=LineType.COMMENT, value=comment)

    return ParsedLine(type=LineType.SQL, value=line)
