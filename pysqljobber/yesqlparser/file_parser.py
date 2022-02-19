import typing

from .line_parser import LineType, parse_line
from .query import Query

IGNORE_TYPES = (LineType.EMPTY_LINE, LineType.COMMENT)
NAME = "name"


class ParserError(Exception):
    def __init__(self, message: str, line_number: int, line: str):
        error_message = f"""
        Error at line {line_number}
        {line}
        {message}
        """
        super().__init__(error_message)


def parse(file_: typing.TextIO) -> typing.List[Query]:

    current_query_block: typing.Optional[Query] = None
    all_query_blocks: typing.List[Query] = []

    for line_number, line in enumerate(file_, start=1):
        parsed_line = parse_line(line)

        if parsed_line.type in IGNORE_TYPES:
            continue

        if parsed_line.type is LineType.TAG:
            if parsed_line.tag == NAME:

                if parsed_line.value in all_query_blocks:
                    raise ParserError(
                        message=f"query name {parsed_line.value} already used",
                        line_number=line_number,
                        line=line,
                    )

                if current_query_block is not None:
                    all_query_blocks.append(current_query_block)

                current_query_block = Query(name=parsed_line.value)
            else:
                if current_query_block is None:
                    raise ParserError(
                        message="name tag should be before other tags",
                        line_number=line_number,
                        line=line,
                    )
                if current_query_block.sql != "":
                    raise ParserError(
                        message="tags should appear before sql",
                        line_number=line_number,
                        line=line,
                    )

                current_query_block.tags[parsed_line.tag] = parsed_line.value

        elif parsed_line.type is LineType.SQL:
            if current_query_block is None:
                raise ParserError(
                    message="name tag should be before SQL",
                    line_number=line_number,
                    line=line,
                )
            current_query_block.sql += line

    if current_query_block is not None:
        all_query_blocks.append(current_query_block)
    return all_query_blocks
