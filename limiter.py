"""
limiter.py - Rate limiting algorithms and RateLimiter class for API Shield.
Implements SRS Section 4, 5, 11, and 14.2.
"""

import time
from typing import NamedTuple, Any, Union
from policy import RateLimitRule


class RateLimitResult(NamedTuple):
    """
    Detailed rate limit check result.
    """
    allowed: bool
    limit: int
    remaining: int
    retry_after: int
    count: int

    def __bool__(self) -> bool:
        return self.allowed


def fixed_window_allowed(redis_client: Any, key: str, limit: int, window: int) -> bool:
    """
    Fixed Window implementation as defined in SRS Section 4.1.
    Divides time into fixed periods.
    """
    window_number = int(time.time() // window)
    redis_key = f"rate:{key}:{window_number}"
    count = redis_client.incr(redis_key)
    if count == 1:
        redis_client.expire(redis_key, window)
    return count <= limit


def sliding_window_allowed(redis_client: Any, key: str, limit: int, window: int) -> bool:
    """
    Sliding Window implementation as defined in SRS Section 4.2.
    Checks requests made during the last N seconds using Redis Sorted Sets.
    """
    now = time.time()
    redis_key = f"slide:{key}"
    start = now - window
    redis_client.zremrangebyscore(redis_key, 0, start)
    # Using high-resolution timestamp or nonce to preserve count on rapid requests
    member = f"{now}:{time.perf_counter_ns()}"
    redis_client.zadd(redis_key, {member: now})
    count = redis_client.zcard(redis_key)
    redis_client.expire(redis_key, window + 1)
    return count <= limit


def token_bucket_allowed(
    redis_client: Any, key: str, limit: int, window: int, capacity: int = None
) -> bool:
    """
    Token Bucket implementation.
    Allows bursts up to capacity while refilling smoothly at limit/window tokens per second.
    """
    cap = capacity if capacity is not None else limit
    now = time.time()
    rate = limit / float(window)
    redis_key = f"tb:{key}"

    data = redis_client.hgetall(redis_key)
    if data:
        raw_tokens = data.get("tokens") or data.get(b"tokens")
        raw_last = data.get("last_updated") or data.get(b"last_updated")
        tokens = float(raw_tokens) if raw_tokens is not None else float(cap)
        last_updated = float(raw_last) if raw_last is not None else now
        elapsed = max(0.0, now - last_updated)
        tokens = min(float(cap), tokens + elapsed * rate)
    else:
        tokens = float(cap)

    if tokens >= 1.0:
        tokens -= 1.0
        redis_client.hset(redis_key, mapping={"tokens": str(tokens), "last_updated": str(now)})
        redis_client.expire(redis_key, int(window * 2 + 10))
        return True
    else:
        redis_client.hset(redis_key, mapping={"tokens": str(tokens), "last_updated": str(now)})
        redis_client.expire(redis_key, int(window * 2 + 10))
        return False


class RateLimiter:
    """
    RateLimiter class (SRS Section 11 & 14.2).
    Coordinates rate limiting checks using Redis store or raw redis client.
    """

    def __init__(self, redis_store: Any):
        # Support either RedisStore instance or raw redis/fakeredis client
        if hasattr(redis_store, "client") and not callable(getattr(redis_store, "client")):
            self.redis_client = redis_store.client
            self.store = redis_store
        else:
            self.redis_client = redis_store
            self.store = None

    def fixed_window(self, key: str, limit: int, window: int) -> bool:
        """
        Fixed window rate-limiting check returning boolean (SRS 14.2).
        """
        return fixed_window_allowed(self.redis_client, key, limit, window)

    def sliding_window(self, key: str, limit: int, window: int) -> bool:
        """
        Sliding window rate-limiting check returning boolean (SRS 14.2).
        """
        return sliding_window_allowed(self.redis_client, key, limit, window)

    def token_bucket(self, key: str, limit: int, window: int, capacity: int = None) -> bool:
        """
        Token bucket rate-limiting check returning boolean.
        """
        return token_bucket_allowed(self.redis_client, key, limit, window, capacity)

    def check_fixed_window(self, key: str, limit: int, window: int) -> RateLimitResult:
        """
        Fixed window check with full metrics (remaining count, retry-after).
        """
        now = time.time()
        window_number = int(now // window)
        redis_key = f"rate:{key}:{window_number}"
        count = int(self.redis_client.incr(redis_key))
        if count == 1:
            self.redis_client.expire(redis_key, window)

        allowed = count <= limit
        remaining = max(0, limit - count)
        
        # Calculate time until next window starts
        window_end = (window_number + 1) * window
        retry_after = max(1, int(window_end - now)) if not allowed else 0

        return RateLimitResult(
            allowed=allowed,
            limit=limit,
            remaining=remaining,
            retry_after=retry_after,
            count=count,
        )

    def check_sliding_window(self, key: str, limit: int, window: int) -> RateLimitResult:
        """
        Sliding window check with full metrics (remaining count, retry-after).
        """
        now = time.time()
        redis_key = f"slide:{key}"
        start = now - window
        self.redis_client.zremrangebyscore(redis_key, 0, start)
        member = f"{now}:{time.perf_counter_ns()}"
        self.redis_client.zadd(redis_key, {member: now})
        count = int(self.redis_client.zcard(redis_key))
        self.redis_client.expire(redis_key, window + 1)

        allowed = count <= limit
        remaining = max(0, limit - count)

        # Retry-after: time until the oldest request in the window expires
        retry_after = 0
        if not allowed:
            oldest = self.redis_client.zrange(redis_key, 0, 0, withscores=True)
            if oldest:
                oldest_score = float(oldest[0][1])
                retry_after = max(1, int(window - (now - oldest_score)))
            else:
                retry_after = window

        return RateLimitResult(
            allowed=allowed,
            limit=limit,
            remaining=remaining,
            retry_after=retry_after,
            count=count,
        )

    def check_token_bucket(
        self, key: str, limit: int, window: int, capacity: int = None
    ) -> RateLimitResult:
        """
        Token bucket check with full metrics (remaining count, retry-after).
        """
        cap = capacity if capacity is not None else limit
        now = time.time()
        rate = limit / float(window)
        redis_key = f"tb:{key}"

        data = self.redis_client.hgetall(redis_key)
        if data:
            raw_tokens = data.get("tokens") or data.get(b"tokens")
            raw_last = data.get("last_updated") or data.get(b"last_updated")
            tokens = float(raw_tokens) if raw_tokens is not None else float(cap)
            last_updated = float(raw_last) if raw_last is not None else now
            elapsed = max(0.0, now - last_updated)
            tokens = min(float(cap), tokens + elapsed * rate)
        else:
            tokens = float(cap)

        allowed = tokens >= 1.0
        if allowed:
            tokens -= 1.0
            retry_after = 0
        else:
            # Time until 1 full token is refilled
            retry_after = max(1, int((1.0 - tokens) / rate + 0.999))

        self.redis_client.hset(redis_key, mapping={"tokens": str(tokens), "last_updated": str(now)})
        self.redis_client.expire(redis_key, int(window * 2 + 10))

        remaining = int(tokens)
        count = int(cap - tokens)

        return RateLimitResult(
            allowed=allowed,
            limit=limit,
            remaining=remaining,
            retry_after=retry_after,
            count=count,
        )

    def is_allowed(
        self, client_id: str, endpoint: str, policy: RateLimitRule
    ) -> RateLimitResult:
        """
        Evaluates request against the given policy algorithm (SRS Section 5.1).
        Key format: '{client_id}:{endpoint}' (SRS 3.1 & BR-08).
        """
        key = policy.get_key(client_id)
        if policy.algorithm == "sliding_window":
            return self.check_sliding_window(key, policy.limit, policy.window)
        elif policy.algorithm == "token_bucket":
            return self.check_token_bucket(key, policy.limit, policy.window)
        return self.check_fixed_window(key, policy.limit, policy.window)
