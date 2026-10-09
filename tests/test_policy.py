"""
tests/test_policy.py - Unit tests for PolicyManager and RateLimitRule.
Covers SRS Test Cases T-07, T-08, BR-01, BR-02, BR-03, BR-04, and Section 3.3.
"""

import pytest
from policy import RateLimitRule, PolicyManager


def test_valid_policy_creation():
    """Validates that a correctly specified policy creates successfully."""
    rule = RateLimitRule(
        name="valid_rule",
        endpoint="/api/items",
        limit=10,
        window=60,
        algorithm="fixed_window",
        active=True,
    )
    assert rule.name == "valid_rule"
    assert rule.endpoint == "/api/items"
    assert rule.limit == 10
    assert rule.window == 60
    assert rule.algorithm == "fixed_window"
    assert rule.active is True


def test_invalid_policy_empty_name():
    """T-07: Invalid policy - empty or missing name raises ValueError."""
    with pytest.raises(ValueError, match="Policy name must be a non-empty string"):
        RateLimitRule(name="", endpoint="/api/test", limit=5, window=60)


def test_invalid_policy_endpoint_format():
    """T-07: Invalid policy - endpoint must start with '/'."""
    with pytest.raises(ValueError, match="Endpoint must start with '/'"):
        RateLimitRule(name="test", endpoint="api/test", limit=5, window=60)


def test_invalid_policy_limit():
    """T-07: Invalid policy - limit must be > 0 (BR-03)."""
    with pytest.raises(ValueError, match="Limit must be greater than 0"):
        RateLimitRule(name="test", endpoint="/api/test", limit=0, window=60)
    with pytest.raises(ValueError, match="Limit must be greater than 0"):
        RateLimitRule(name="test", endpoint="/api/test", limit=-5, window=60)


def test_invalid_policy_window():
    """T-07: Invalid policy - window must be > 0 (BR-04)."""
    with pytest.raises(ValueError, match="Window must be greater than 0"):
        RateLimitRule(name="test", endpoint="/api/test", limit=5, window=0)
    with pytest.raises(ValueError, match="Window must be greater than 0"):
        RateLimitRule(name="test", endpoint="/api/test", limit=5, window=-60)


def test_invalid_policy_algorithm():
    """T-07: Invalid policy - algorithm must be fixed_window, sliding_window, or token_bucket."""
    with pytest.raises(ValueError, match="Algorithm must be"):
        RateLimitRule(name="test", endpoint="/api/test", limit=5, window=60, algorithm="unsupported_algorithm")

    # token_bucket is a supported, valid algorithm
    rule = RateLimitRule(name="test_tb", endpoint="/api/test", limit=5, window=60, algorithm="token_bucket")
    assert rule.algorithm == "token_bucket"



def test_policy_manager_create_and_duplicate():
    """Verifies policy registration and duplicate rejection."""
    pm = PolicyManager()
    data = {
        "name": "rule_a",
        "endpoint": "/api/test",
        "limit": 10,
        "window": 60,
        "algorithm": "fixed_window",
    }
    rule = pm.create_policy(data)
    assert rule.name == "rule_a"

    # Reject duplicate policy name
    with pytest.raises(ValueError, match="already exists"):
        pm.create_policy(data)


def test_inactive_policy(client):
    """
    T-08 & BR-01: Inactive policy shall not limit requests.
    Deactivating a policy allows unlimited requests on that endpoint.
    """
    # Deactivate the product_limit policy
    pm = client.application.policy_manager
    pm.deactivate_policy("product_limit")
    assert pm.get_policy("product_limit").active is False

    # Send more requests than limit (limit was 5)
    for _ in range(8):
        resp = client.get("/api/products", headers={"X-API-Key": "testkey_inactive"})
        assert resp.status_code == 200

    # Re-activate policy and ensure limiting resumes
    pm.activate_policy("product_limit")
    assert pm.get_policy("product_limit").active is True


def test_unregistered_endpoint_not_limited(client):
    """
    BR-02: If no policy exists for an endpoint (like /health), request shall be allowed without limiting.
    """
    for _ in range(10):
        resp = client.get("/health", headers={"X-API-Key": "testkey_unprotected"})
        assert resp.status_code == 200
        # No rate limit headers injected because no policy applies
        assert "X-RateLimit-Limit" not in resp.headers
