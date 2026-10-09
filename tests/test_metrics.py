"""
tests/test_metrics.py - Tests for Prometheus metrics collection and exposition.
"""

from metrics import MetricsCollector


def test_metrics_collector_record_and_export():
    collector = MetricsCollector()
    collector.record_request("/api/test", 200, "free")
    collector.record_request("/api/test", 429, "free")
    collector.record_block("/api/test", "token_bucket")
    collector.record_ai("deepseek-flash", "success")

    text = collector.export_prometheus()
    assert "# HELP api_shield_requests_total" in text
    assert 'api_shield_requests_total{endpoint="/api/test",status="200",tier="free"} 1' in text
    assert 'api_shield_requests_total{endpoint="/api/test",status="429",tier="free"} 1' in text
    assert 'api_shield_rate_limit_blocks_total{endpoint="/api/test",algorithm="token_bucket"} 1' in text
    assert 'api_shield_ai_completions_total{model="deepseek-flash",status="success"} 1' in text


def test_metrics_http_endpoint(client):
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "text/plain" in res.content_type
    body = res.get_data(as_text=True)
    assert "api_shield_requests_total" in body
    assert "api_shield_policies_total" in body
    assert "api_shield_policies_active" in body
