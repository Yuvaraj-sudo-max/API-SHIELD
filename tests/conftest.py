"""
tests/conftest.py - Pytest fixtures for API Shield testing suite.
"""

import sys
import os
import pytest
import fakeredis

# Ensure parent directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from config import Config
from redis_store import RedisStore
from policy import PolicyManager


class TestConfig(Config):
    TESTING = True
    DEBUG = False
    POLICIES_FILE = None  # in-memory policies during test runs


@pytest.fixture
def redis_client():
    """
    Provides an isolated in-memory Redis client instance for tests.
    Matches SRS Section 14.2 test signature: test_fixed_window_limit(redis_client).
    """
    fake = fakeredis.FakeRedis(decode_responses=True)
    fake.flushdb()
    yield fake
    fake.flushdb()


@pytest.fixture
def redis_store(redis_client):
    """Provides a RedisStore wrapper around the test redis_client."""
    return RedisStore(client=redis_client)


@pytest.fixture
def app(redis_client):
    """Provides an isolated Flask test application."""
    test_app = create_app(config_class=TestConfig, redis_client=redis_client)
    # Clear and re-populate default policies
    test_app.policy_manager.policies.clear()
    test_app.policy_manager.create_policy({
        "name": "product_limit",
        "endpoint": "/api/products",
        "limit": 5,
        "window": 60,
        "algorithm": "fixed_window",
        "active": True
    })
    test_app.policy_manager.create_policy({
        "name": "user_limit",
        "endpoint": "/api/users",
        "limit": 5,
        "window": 60,
        "algorithm": "sliding_window",
        "active": True
    })
    test_app.policy_manager.create_policy({
        "name": "login_limit",
        "endpoint": "/api/login",
        "limit": 5,
        "window": 300,
        "algorithm": "fixed_window",
        "active": True
    })
    test_app.policy_manager.create_policy({
        "name": "ai_chat_limit",
        "endpoint": "/api/ai/chat",
        "limit": 5,
        "window": 60,
        "algorithm": "sliding_window",
        "active": True
    })
    return test_app


@pytest.fixture
def client(app):
    """Provides a Flask test client."""
    return app.test_client()
