"""
tests/test_token_bucket.py - Unit tests for Token Bucket rate limiting algorithm.
"""

import time
import fakeredis
from limiter import RateLimiter, token_bucket_allowed
from policy import RateLimitRule


def test_token_bucket_allowed_basic():
    r = fakeredis.FakeStrictRedis()
    key = "test_tb_client"
    limit = 3
    window = 10

    # 3 requests allowed immediately (capacity = 3)
    assert token_bucket_allowed(r, key, limit, window) is True
    assert token_bucket_allowed(r, key, limit, window) is True
    assert token_bucket_allowed(r, key, limit, window) is True

    # 4th request must be rejected (bucket depleted)
    assert token_bucket_allowed(r, key, limit, window) is False


def test_token_bucket_check_metrics():
    r = fakeredis.FakeStrictRedis()
    limiter = RateLimiter(r)
    key = "client_tb_metrics"
    limit = 4
    window = 20

    res1 = limiter.check_token_bucket(key, limit, window)
    assert res1.allowed is True
    assert res1.limit == 4
    assert res1.remaining == 3
    assert res1.retry_after == 0

    res2 = limiter.check_token_bucket(key, limit, window)
    assert res2.allowed is True
    assert res2.remaining == 2

    res3 = limiter.check_token_bucket(key, limit, window)
    assert res3.allowed is True
    assert res3.remaining == 1

    res4 = limiter.check_token_bucket(key, limit, window)
    assert res4.allowed is True
    assert res4.remaining == 0

    # 5th request is rejected with calculated retry_after
    res5 = limiter.check_token_bucket(key, limit, window)
    assert res5.allowed is False
    assert res5.remaining == 0
    assert res5.retry_after >= 1


def test_token_bucket_policy_integration():
    r = fakeredis.FakeStrictRedis()
    limiter = RateLimiter(r)
    policy = RateLimitRule(
        name="tb_policy",
        endpoint="/api/stream",
        limit=2,
        window=10,
        algorithm="token_bucket",
        active=True,
    )

    client_id = "key:usr_tb_123"
    assert limiter.is_allowed(client_id, "/api/stream", policy).allowed is True
    assert limiter.is_allowed(client_id, "/api/stream", policy).allowed is True
    assert limiter.is_allowed(client_id, "/api/stream", policy).allowed is False
