"""
metrics.py - Prometheus metrics collector and exporter for API Shield.
Provides standard Prometheus text exposition format for gateway monitoring.
"""

import threading
from typing import Dict, Tuple


class MetricsCollector:
    """
    In-memory thread-safe metrics collector for API Shield.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._request_counts: Dict[Tuple[str, int, str], int] = {}
        self._block_counts: Dict[Tuple[str, str], int] = {}
        self._ai_counts: Dict[Tuple[str, str], int] = {}

    def record_request(self, endpoint: str, status: int, tier: str = "free") -> None:
        """Records an HTTP request outcome."""
        key = (endpoint, status, tier)
        with self._lock:
            self._request_counts[key] = self._request_counts.get(key, 0) + 1

    def record_block(self, endpoint: str, algorithm: str) -> None:
        """Records a rate limit rejection (429)."""
        key = (endpoint, algorithm)
        with self._lock:
            self._block_counts[key] = self._block_counts.get(key, 0) + 1

    def record_ai(self, model: str, status: str) -> None:
        """Records a DeepSeek AI completion request."""
        key = (model, status)
        with self._lock:
            self._ai_counts[key] = self._ai_counts.get(key, 0) + 1

    def export_prometheus(self, policy_manager=None, block_manager=None) -> str:
        """
        Generates Prometheus exposition text (version 0.0.4).
        """
        lines = [
            "# HELP api_shield_requests_total Total number of HTTP requests processed by API Shield",
            "# TYPE api_shield_requests_total counter",
        ]

        with self._lock:
            req_items = list(self._request_counts.items())
            block_items = list(self._block_counts.items())
            ai_items = list(self._ai_counts.items())

        if not req_items:
            lines.append('api_shield_requests_total{endpoint="/health",status="200",tier="free"} 0')
        else:
            for (ep, st, tier), count in req_items:
                lines.append(f'api_shield_requests_total{{endpoint="{ep}",status="{st}",tier="{tier}"}} {count}')

        lines.extend([
            "",
            "# HELP api_shield_rate_limit_blocks_total Total rate limit rejections (HTTP 429)",
            "# TYPE api_shield_rate_limit_blocks_total counter",
        ])
        if not block_items:
            lines.append('api_shield_rate_limit_blocks_total{endpoint="none",algorithm="none"} 0')
        else:
            for (ep, algo), count in block_items:
                lines.append(f'api_shield_rate_limit_blocks_total{{endpoint="{ep}",algorithm="{algo}"}} {count}')

        # Policy & Block Gauges
        active_policies = 0
        total_policies = 0
        if policy_manager:
            policies = policy_manager.list_policies()
            total_policies = len(policies)
            active_policies = sum(1 for p in policies if p.get("active", True))

        lines.extend([
            "",
            "# HELP api_shield_policies_total Total registered rate limit policies",
            "# TYPE api_shield_policies_total gauge",
            f"api_shield_policies_total {total_policies}",
            "",
            "# HELP api_shield_policies_active Active rate limit policies enforcing quotas",
            "# TYPE api_shield_policies_active gauge",
            f"api_shield_policies_active {active_policies}",
        ])

        # AI Gateway Metrics
        lines.extend([
            "",
            "# HELP api_shield_ai_completions_total Total DeepSeek AI completions handled",
            "# TYPE api_shield_ai_completions_total counter",
        ])
        if not ai_items:
            lines.append('api_shield_ai_completions_total{model="deepseek-flash",status="none"} 0')
        else:
            for (model, status), count in ai_items:
                lines.append(f'api_shield_ai_completions_total{{model="{model}",status="{status}"}} {count}')

        lines.append("")
        return "\n".join(lines)


# Singleton metrics collector instance
global_metrics = MetricsCollector()
