"""
tests/test_api_integration.py - Full end-to-end API integration tests.
Covers SRS Section 8, 13, and 15 (Postman flow verification in Python).
"""

import json


def test_health_check(client):
    """Verifies health check endpoint returns 200 OK (SRS Section 8.1 & FR-14)."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] in ("healthy", "degraded")
    assert "redis" in data


def test_rate_limit_flow_fixed_window(client):
    """
    Simulates Section 15 Postman testing:
    - 5 successful requests with limit=5, window=60
    - 6th request fails with 429 Too Many Requests and Retry-After header
    """
    headers = {"X-API-Key": "client-test-alpha"}

    # Requests 1 to 5 should succeed (200 OK)
    for i in range(1, 6):
        res = client.get("/api/products", headers=headers)
        assert res.status_code == 200
        assert res.headers.get("X-RateLimit-Limit") == "5"
        expected_remaining = str(5 - i)
        assert res.headers.get("X-RateLimit-Remaining") == expected_remaining
        data = res.get_json()
        assert data["message"] == "Request successful"

    # Request 6 should be rejected with HTTP 429
    res6 = client.get("/api/products", headers=headers)
    assert res6.status_code == 429
    assert res6.headers.get("X-RateLimit-Limit") == "5"
    assert res6.headers.get("X-RateLimit-Remaining") == "0"
    assert res6.headers.get("Retry-After") is not None
    data6 = res6.get_json()
    assert data6["error"] == "Rate limit exceeded"
    assert data6["message"] == "Please try again later"


def test_temporary_block_on_repeated_violations(client):
    """
    Simulates repeated rate limit violations causing temporary client blocking.
    """
    headers = {"X-API-Key": "abusive-client-99"}

    # Exhaust quota
    for _ in range(5):
        client.get("/api/products", headers=headers)

    # Trigger rate limit violation
    blocked_res = client.get("/api/products", headers=headers)
    assert blocked_res.status_code == 429

    # Next attempt is blocked by temporary block rule immediately
    immediate_block_res = client.get("/api/products", headers=headers)
    assert immediate_block_res.status_code == 429
    assert immediate_block_res.headers.get("Retry-After") is not None


def test_policy_crud_api(client):
    """
    Tests policy management REST endpoints (SRS Section 7.1).
    """
    # 1. Create Policy
    new_policy = {
        "name": "search_limit",
        "endpoint": "/api/search",
        "limit": 20,
        "window": 60,
        "algorithm": "fixed_window",
        "active": True,
    }
    create_res = client.post(
        "/api/policies",
        data=json.dumps(new_policy),
        content_type="application/json",
    )
    assert create_res.status_code == 201

    # 2. Get Created Policy
    get_res = client.get("/api/policies/search_limit")
    assert get_res.status_code == 200
    assert get_res.get_json()["policy"]["name"] == "search_limit"

    # 3. Update Policy
    update_data = {
        "endpoint": "/api/search",
        "limit": 50,
        "window": 120,
        "algorithm": "sliding_window",
        "active": True,
    }
    update_res = client.put(
        "/api/policies/search_limit",
        data=json.dumps(update_data),
        content_type="application/json",
    )
    assert update_res.status_code == 200
    assert update_res.get_json()["policy"]["limit"] == 50

    # 4. Deactivate Policy
    deactivate_res = client.post("/api/policies/search_limit/deactivate")
    assert deactivate_res.status_code == 200
    assert deactivate_res.get_json()["policy"]["active"] is False

    # 5. Activate Policy
    activate_res = client.post("/api/policies/search_limit/activate")
    assert activate_res.status_code == 200
    assert activate_res.get_json()["policy"]["active"] is True

    # 6. List Policies
    list_res = client.get("/api/policies")
    assert list_res.status_code == 200
    assert len(list_res.get_json()["policies"]) >= 1


def test_invalid_policy_creation_error_handling(client):
    """
    SRS Section 13: Invalid policy data returns HTTP 400.
    """
    bad_policy = {
        "name": "bad",
        "endpoint": "no_slash",  # missing leading slash
        "limit": -5,
        "window": 0,
    }
    res = client.post(
        "/api/policies",
        data=json.dumps(bad_policy),
        content_type="application/json",
    )
    assert res.status_code == 400
    assert res.get_json()["error"] == "Invalid policy"


def test_policy_not_found_error_handling(client):
    """
    SRS Section 13: Policy not found returns HTTP 404.
    """
    res = client.get("/api/policies/non_existent_policy")
    assert res.status_code == 404
    assert res.get_json()["error"] == "Policy not found"


def test_index_dashboard_renders(client):
    """
    Verifies that the interactive 3D dashboard frontend renders successfully (200 OK).
    """
    res = client.get("/")
    assert res.status_code == 200
    assert b"API SHIELD" in res.data
    assert b"shield-3d-canvas-container" in res.data
    assert b"Internal Process Transparency" in res.data
    assert b"styles.css" in res.data
    assert b"shield3d.js" in res.data
