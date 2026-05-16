import asyncio
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from .cache import get_redis
from .config import Settings

_WINDOW_SECONDS = 60


async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    """Redis-backed sliding-window rate limiter. No-op when REDIS_URL is unset."""
    settings = Settings()
    client = get_redis(settings)

    if client is None:
        return await call_next(request)

    key = f"rate:{request.client.host}:{request.url.path}"
    limit = settings.rate_limit_per_minute

    count = await asyncio.to_thread(client.incr, key)
    if count == 1:
        await asyncio.to_thread(client.expire, key, _WINDOW_SECONDS)

    remaining = max(0, limit - count)

    if count > limit:
        return JSONResponse(
            {"detail": "Too many requests — try again in a minute."},
            status_code=429,
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "Retry-After": str(_WINDOW_SECONDS),
            },
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response
