import logging

from rich.logging import RichHandler

logger = logging.getLogger()


def add_cli_handler(level: int = logging.INFO):
    handler = RichHandler(level=level, show_path=True)
    handler.setLevel(level)
    logger.setLevel(level)
    logger.addHandler(handler)
