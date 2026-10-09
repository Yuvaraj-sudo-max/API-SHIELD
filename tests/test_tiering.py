"""
tests/test_tiering.py - Tests for multi-tenant client tiers and quota multipliers.
"""

from identity import get_client_tier, get_tier_multiplier


class DummyRequest:
    def __init__(self, headers=None, remote_addr="127.0.0.1"):
        self.headers = headers or {}
        self.remote_addr = remote_addr


def test_client_tier_resolution_from_header():
    req_ent = DummyRequest(headers={"X-Client-Tier": "enterprise"})
    assert get_client_tier(req_ent) == "enterprise"

    req_pro = DummyRequest(headers={"X-Client-Tier": "Pro"})
    assert get_client_tier(req_pro) == "pro"

    req_free = DummyRequest(headers={"X-Client-Tier": "free"})
    assert get_client_tier(req_free) == "free"


def test_client_tier_resolution_from_key_prefix():
    req_ent_key = DummyRequest(headers={"X-API-Key": "ent_corp_key_999"})
    assert get_client_tier(req_ent_key) == "enterprise"

    req_pro_key = DummyRequest(headers={"X-API-Key": "pro_dev_key_456"})
    assert get_client_tier(req_pro_key) == "pro"

    req_default = DummyRequest(headers={"X-API-Key": "standard_key_123"})
    assert get_client_tier(req_default) == "free"


def test_tier_multiplier_values():
    assert get_tier_multiplier("free") == 1.0
    assert get_tier_multiplier("pro") == 3.0
    assert get_tier_multiplier("enterprise") == 10.0
    assert get_tier_multiplier("unknown") == 1.0


def test_client_tier_endpoint_quota_scaling(client):
    """
    Verifies that Enterprise clients receive scaled rate limit limits
    and the X-Client-Tier response header.
    """
    headers_ent = {
        "X-API-Key": "ent_test_client_enterprise",
        "X-Client-Tier": "enterprise",
    }
    # Base limit for /api/products is 5 (Fixed Window)
    # Enterprise multiplier is 10.0 -> Limit becomes 50
    res = client.get("/api/products", headers=headers_ent)
    assert res.status_code == 200
    assert res.headers.get("X-Client-Tier") == "enterprise"
    assert res.headers.get("X-RateLimit-Limit") == "50"
