"""
tests/test_limiter.py - Unit tests for RateLimiter algorithms.
Covers SRS Test Cases T-01, T-02, T-03, T-04, T-05, T-06, and Section 14.2.
"""

import time
from limiter import RateLimiter, fixed_window_allowed, sliding_window_allowed


def test_fixed_window_limit(redis_client):
    """
    Exact implementation from SRS Section 14.2:
    Allows 5 requests, 6th is rejected.
    """
    limiter = RateLimiter(redis_client)
    for _ in range(5):
        assert limiter.fixed_window("client1:/api/products", 5, 60) is True
    assert limiter.fixed_window("client1:/api/products", 5, 60) is False


def test_sliding_window_limit(redis_client):
    """
    Verifies sliding window limits requests to configured limit.
    """
    limiter = RateLimiter(redis_client)
    for _ in range(5):
        assert limiter.sliding_window("client1:/api/users", 5, 60) is True
    assert limiter.sliding_window("client1:/api/users", 5, 60) is False


def test_fixed_window_expiry(redis_client):
    """
    T-03: Fixed window expiry - New window starts after expiry.
    """
    limiter = RateLimiter(redis_client)
    # 2 requests in a 1-second window
    assert limiter.fixed_window("client_fw:/api/products", 2, 1) is True
    assert limiter.fixed_window("client_fw:/api/products", 2, 1) is True
    assert limiter.fixed_window("client_fw:/api/products", 2, 1) is False

    # Wait for the 1-second window boundary to cross
    time.sleep(1.1)

    # After expiry, request should be allowed again
    assert limiter.fixed_window("client_fw:/api/products", 2, 1) is True


def test_sliding_window_removes_old_timestamps(redis_client):
    """
    T-04: Sliding window removes old timestamps - Expired requests no longer count.
    """
    limiter = RateLimiter(redis_client)
    # 2 requests in a 1-second rolling window
    assert limiter.sliding_window("client_sw:/api/users", 2, 1) is True
    assert limiter.sliding_window("client_sw:/api/users", 2, 1) is True
    assert limiter.sliding_window("client_sw:/api/users", 2, 1) is False

    # Wait for rolling window to pass
    time.sleep(1.1)

    # Expired timestamps removed; new request allowed
    assert limiter.sliding_window("client_sw:/api/users", 2, 1) is True


def test_separate_clients(redis_client):
    """
    T-05: Client A does not use Client B's counter (BR-08).
    """
    limiter = RateLimiter(redis_client)
    limit = 3
    window = 60

    # Exhaust limit for Client A
    for _ in range(limit):
        assert limiter.fixed_window("clientA:/api/products", limit, window) is True
    assert limiter.fixed_window("clientA:/api/products", limit, window) is False

    # Client B should still have full quota available
    for _ in range(limit):
        assert limiter.fixed_window("clientB:/api/products", limit, window) is True
    assert limiter.fixed_window("clientB:/api/products", limit, window) is False


def test_separate_endpoints(redis_client):
    """
    T-06: Endpoint A does not use Endpoint B's counter (BR-08).
    """
    limiter = RateLimiter(redis_client)
    limit = 3
    window = 60

    # Exhaust limit on Endpoint 1 for client1
    for _ in range(limit):
        assert limiter.fixed_window("client1:/api/products", limit, window) is True
    assert limiter.fixed_window("client1:/api/products", limit, window) is False

    # Endpoint 2 should still be allowed for the same client1
    for _ in range(limit):
        assert limiter.fixed_window("client1:/api/orders", limit, window) is True
    assert limiter.fixed_window("client1:/api/orders", limit, window) is False


def test_check_detailed_metrics(redis_client):
    """
    Verifies detailed result metrics: limit, remaining count, and retry_after.
    """
    limiter = RateLimiter(redis_client)
    res1 = limiter.check_fixed_window("client_metric:/api/test", 5, 60)
    assert res1.allowed is True
    assert res1.remaining == 4
    assert res1.count == 1

    # Call 4 more times to reach limit
    for _ in range(4):
        limiter.check_fixed_window("client_metric:/api/test", 5, 60)

    res_blocked = limiter.check_fixed_window("client_metric:/api/test", 5, 60)
    assert res_blocked.allowed is False
    assert res_blocked.remaining == 0
    assert res_blocked.retry_after > 0
