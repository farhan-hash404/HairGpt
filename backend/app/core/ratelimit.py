"""Fixed-window rate limiting as a FastAPI dependency.

Protects the endpoints that can spend money or CPU — above all the evidence
Q&A, which may call a paid or quota-limited LLM on the deployer's key.
"""

from __future__ import annotations

import time

from fastapi import Depends, HTTPException, Request, status

from app.api.deps import get_current_user
from app.core.cache import incr
from app.models.user import User


def rate_limit(bucket: str, per_minute: int):
    def dependency(request: Request, user: User = Depends(get_current_user)) -> None:
        window = int(time.time() // 60)
        key = f"rl:{bucket}:{user.id}:{window}"
        count = incr(key, ttl=70)
        if count > per_minute:
            retry_after = 60 - int(time.time() % 60)
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "rate_limited", "message": f"Limit is {per_minute} requests per minute.",
                        "retry_after_s": retry_after},
                headers={"Retry-After": str(retry_after)},
            )

    return dependency
