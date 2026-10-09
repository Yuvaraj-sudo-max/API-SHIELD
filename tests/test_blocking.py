"""
tests/test_blocking.py - Unit tests for abuse prevention and temporary blocking.
Covers SRS Test Cases T-09, T-10, BR-05, BR-06, and Section 6 & 11.
"""

import time
from blocking import BlockManager


def test_block_duration_tiers(redis_store):
    """
    SRS Section 6.1: Temporary Blocking Duration Tiers.
      - 1–3 violations: 300s (5m)
      - 4–6 violations: 900s (15m)
      - 7+ violations: 1800s (30m)
    """
    bm = BlockManager(redis_store)
    # Tier 1
    assert bm.get_block_duration(1) == 300
    assert bm.get_block_duration(2) == 300
    assert bm.get_block_duration(3) == 300

    # Tier 2
    assert bm.get_block_duration(4) == 900
    assert bm.get_block_duration(5) == 900
    assert bm.get_block_duration(6) == 900

    # Tier 3
    assert bm.get_block_duration(7) == 1800
    assert bm.get_block_duration(10) == 1800


def test_record_violation_and_block(redis_store):
    """
    SRS Section 6.2: Record violation increments count and applies block.
    """
    bm = BlockManager(redis_store)
    client_id = "key:violator_client"

    # Initially not blocked
    blocked, ttl = bm.is_blocked(client_id)
    assert blocked is False
    assert ttl == 0

    # 1st violation
    count, duration = bm.record_violation(client_id)
    assert count == 1
    assert duration == 300

    blocked, ttl = bm.is_blocked(client_id)
    assert blocked is True
    assert 0 < ttl <= 300


def test_temporary_block_response(client):
    """
    T-09 & BR-05: Blocked client receives HTTP 429.
    """
    app = client.application
    client_id = "key:abusive_client"
    headers = {"X-API-Key": "abusive_client"}

    # Manually trigger a block on this client
    app.block_manager.block_client(client_id, duration=60)

    # Next request should be immediately rejected with 429
    resp = client.get("/api/products", headers=headers)
    assert resp.status_code == 429
    data = resp.get_json()
    assert "Rate limit exceeded" in data.get("error", "")
    assert "Retry-After" in resp.headers


def test_block_expiry(client):
    """
    T-10: Client can request again after block expiry.
    """
    app = client.application
    client_id = "key:short_block_client"
    headers = {"X-API-Key": "short_block_client"}

    # Set 1-second block
    app.block_manager.block_client(client_id, duration=1)
    resp = client.get("/api/products", headers=headers)
    assert resp.status_code == 429

    # Wait for block to expire
    time.sleep(1.2)

    # Now request should be permitted
    resp_after = client.get("/api/products", headers=headers)
    assert resp_after.status_code == 200
