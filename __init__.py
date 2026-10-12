"""
API Shield - Autonomous Rate Limiting & Zero-Trust Abuse Defense Gateway.
A production-grade, multi-algorithm rate limiting and threat mitigation framework for Python.
"""

from .shield import APIShield
from .limiter import RateLimiter, LimitResult
from .redis_store import RedisStore
from .policy import PolicyManager, RateLimitRule
from .blocking import BlockManager
from .identity import get_client_id, get_client_tier, get_tier_multiplier
from .app import create_app
from .config import Config

__version__ = "2.4.0"
__author__ = "API Shield Team"

__all__ = [
    "APIShield",
    "RateLimiter",
    "LimitResult",
    "RedisStore",
    "PolicyManager",
    "RateLimitRule",
    "BlockManager",
    "create_app",
    "Config",
    "get_client_id",
    "get_client_tier",
    "get_tier_multiplier",
]
