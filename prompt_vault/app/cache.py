from functools import lru_cache

import redis as redis_lib

from .config import Settings


@lru_cache(maxsize=1)
def _build_client(url: str) -> redis_lib.Redis:
    return redis_lib.from_url(url, decode_responses=True)


def get_redis(settings: Settings) -> redis_lib.Redis | None:
    """Return a Redis client, or None if REDIS_URL is not configured."""
    if not settings.redis_url:
        return None
    return _build_client(settings.redis_url)
