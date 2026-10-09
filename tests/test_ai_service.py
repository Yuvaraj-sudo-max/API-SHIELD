"""
tests/test_ai_service.py - Unit and integration tests for DeepSeek AI features and rate limiting.
"""

import json
from ai_service import AIService


def test_ai_service_masked_key():
    ai = AIService(api_key="sk-fc02e982d5934be9a510598120f2b1df")
    masked = ai.get_masked_key()
    assert masked.startswith("sk-fc0")
    assert masked.endswith("b1df")
    assert "..." in masked


def test_ai_status_endpoint(client, monkeypatch):
    app = client.application
    monkeypatch.setattr(
        app.ai_service,
        "check_status",
        lambda: {
            "configured": True,
            "connected": True,
            "provider": "DeepSeek",
            "model": "deepseek-flash",
            "key_masked": "sk-fc0...b1df",
            "status": "active",
        },
    )
    res = client.get("/api/ai/status")
    assert res.status_code == 200
    data = res.get_json()
    assert data.get("configured") is True
    assert data.get("provider") == "DeepSeek"
    assert data.get("model") == "deepseek-flash"


def test_ai_chat_rate_limiting_flow(client, monkeypatch):
    """
    Verifies that the DeepSeek AI Chat Gateway (/api/ai/chat)
    is rate-limited according to the active policy (limit: 5 req / 60s).
    """
    # Mock chat_completion to test rate limiting without external API latency
    app = client.application
    monkeypatch.setattr(
        app.ai_service,
        "chat_completion",
        lambda prompt, **kwargs: {
            "success": True,
            "content": f"AI Response to: {prompt}",
            "model": "deepseek-flash",
            "source": "mock_test",
        },
    )

    headers = {
        "X-API-Key": "sk-fc02e982d5934be9a510598120f2b1df",
        "Content-Type": "application/json",
    }
    payload = {"prompt": "What is API rate limiting?"}

    # 5 requests should be processed and tracked
    for i in range(1, 6):
        res = client.post("/api/ai/chat", headers=headers, json=payload)
        assert res.status_code == 200
        assert res.headers.get("X-RateLimit-Limit") == "5"
        expected_remaining = str(5 - i)
        assert res.headers.get("X-RateLimit-Remaining") == expected_remaining
        data = res.get_json()
        assert "response" in data
        assert data["response"] == "AI Response to: What is API rate limiting?"

    # 6th request must be rejected with HTTP 429 Too Many Requests
    res6 = client.post("/api/ai/chat", headers=headers, json=payload)
    assert res6.status_code == 429
    assert res6.headers.get("X-RateLimit-Remaining") == "0"
    assert res6.headers.get("Retry-After") is not None


def test_ai_threat_assessment_endpoint(client, monkeypatch):
    app = client.application
    monkeypatch.setattr(
        app.ai_service,
        "chat_completion",
        lambda prompt, **kwargs: {
            "success": True,
            "content": "[Autonomous Threat Assessment] Low risk baseline.",
            "model": "deepseek-flash",
        },
    )

    res = client.post("/api/ai/analyze-threat")
    assert res.status_code == 200
    data = res.get_json()
    assert "threat_level" in data
    assert "ai_analysis" in data


def test_ai_generate_policy_endpoint(client, monkeypatch):
    app = client.application
    monkeypatch.setattr(
        app.ai_service,
        "chat_completion",
        lambda prompt, **kwargs: {
            "success": True,
            "content": json.dumps({
                "name": "ai_test_policy",
                "endpoint": "/api/payments",
                "limit": 10,
                "window": 60,
                "algorithm": "sliding_window",
                "active": True,
            }),
            "model": "deepseek-flash",
        },
    )

    res = client.post(
        "/api/ai/generate-policy",
        json={"intent": "Protect payments API with sliding window"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert "policy" in data
    policy = data["policy"]
    assert policy["endpoint"] == "/api/payments"
    assert policy["limit"] == 10
    assert policy["window"] == 60
