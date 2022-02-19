from contextlib import asynccontextmanager
from functools import lru_cache

from psycopg_pool import AsyncConnectionPool


class ConnectionPool:
    def __init__(self, max_connection_pools: int, *, min_size: int = 2):
        self._get_pool = lru_cache(maxsize=max_connection_pools)(self._get_new_pool)
        self._min_size = min_size

    def _get_new_pool(self, dsn: str) -> AsyncConnectionPool:
        return AsyncConnectionPool(dsn, min_size=self._min_size)

    @asynccontextmanager
    async def connection(self, dsn: str):
        pool = self._get_pool(dsn=dsn)
        async with pool.connection() as conn:
            yield conn
