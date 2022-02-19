from functools import lru_cache

import aioredis


@lru_cache(maxsize=1)
def from_url(url: str, encoding: str, decode_responses: bool) -> aioredis.Redis:
    return aioredis.from_url(
        url=url, encoding=encoding, decode_responses=decode_responses
    )
