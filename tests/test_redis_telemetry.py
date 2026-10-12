"""
tests/test_redis_telemetry.py - Tests for live Redis storage inspection,
unknown user tracking, and telemetry endpoints.
"""

import json
from app import create_app
from policy import RateLimitRule


def test_redis_info_and_keys_endpoints(client):
    # Test Redis info endpoint
    resp = client.get("/api/redis/info")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "connected" in data
    assert "backend" in data

    # Test Redis keys endpoint
    resp_keys = client.get("/api/redis/keys")
    assert resp_keys.status_code == 200
    data_keys = resp_keys.get_json()
    assert "keys" in data_keys
    assert isinstance(data_keys["keys"], list)


def test_redis_telemetry_unknown_user_tracking(client):
    # 1. Trigger request from an "unknown user" (IP only, no X-API-Key)
    client.get(
        "/api/products",
        headers={
            "X-Forwarded-For": "203.0.113.195",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TestBrowser",
        }
    )

    # 2. Trigger request from an identified client with API Key
    client.get(
        "/api/users",
        headers={
            "X-API-Key": "test_client_key_corp",
            "X-Client-Tier": "pro",
            "X-Forwarded-For": "198.51.100.42",
        }
    )

    # 3. Query telemetry endpoint
    resp = client.get("/api/redis/telemetry")
    assert resp.status_code == 200
    telemetry = resp.get_json()

    assert "server_info" in telemetry
    assert "requests" in telemetry
    assert "total_requests" in telemetry
    assert telemetry["total_requests"] >= 2

    # Verify unknown user record details
    unknown_reqs = [r for r in telemetry["requests"] if r.get("is_unknown_user")]
    assert len(unknown_reqs) >= 1
    un_req = unknown_reqs[0]
    assert un_req["sender_ip"] == "203.0.113.195"
    assert "receiver_ip" in un_req
    assert un_req["user_type"] == "Unknown User (IP Only)"
    assert un_req["endpoint"] == "/api/products"
    assert "redis_key" in un_req
    assert "redis_type" in un_req
    assert un_req["status"] == "ALLOWED"

    # Verify identified user record
    identified_reqs = [r for r in telemetry["requests"] if not r.get("is_unknown_user")]
    assert len(identified_reqs) >= 1
    id_req = identified_reqs[0]
    assert id_req["sender_ip"] == "198.51.100.42"
    assert id_req["user_type"] == "Identified Client"
    assert id_req["tier"] == "pro"


def test_redis_probe_and_clear_endpoints(client):
    # Test Redis latency probe
    resp_test = client.post("/api/redis/test")
    assert resp_test.status_code == 200
    data_test = resp_test.get_json()
    assert "success" in data_test
    assert data_test["success"] is True

    # Test clear rate limit keys
    resp_clear = client.post("/api/redis/clear")
    assert resp_clear.status_code == 200
    data_clear = resp_clear.get_json()
    assert "deleted_count" in data_clear
