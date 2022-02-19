from contextlib import asynccontextmanager
from functools import lru_cache

from psycopg_pool import AsyncConnectionPool


class ConnectionPool:
    def __init__(self, maxsize: int):

        self._get_pool = lru_cache(maxsize=maxsize)(self._get_new_pool)

    def _get_new_pool(self, dsn: str) -> AsyncConnectionPool:
        return AsyncConnectionPool(dsn)

    @asynccontextmanager
    async def connection(self, dsn: str):
        pool = self._get_pool(dsn=dsn)
        async with pool.connection() as conn:
            yield conn
