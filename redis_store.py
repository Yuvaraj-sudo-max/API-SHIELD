"""
redis_store.py - Redis data store abstraction for API Shield.
Implements SRS Section 4, 6, 9, 10.1, and 11.
"""

import time
import logging
from typing import Dict, Any, Optional, Tuple, List
import redis

try:
    import fakeredis
except ImportError:
    fakeredis = None

logger = logging.getLogger("api_shield.redis")


class RedisStore:
    """
    Encapsulates Redis operations (SRS Section 11 - RedisStore).
    Maintains clean separation of Redis commands from rate limiting logic.
    Supports live Redis servers and transparent fallback to FakeRedis for testing/local setups.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        client: Optional[Any] = None,
        use_fallback: bool = True,
    ):
        self.host = host
        self.port = port
        self.db = db
        self.backend = "unknown"

        if client is not None:
            self.client = client
            self.backend = "custom"
        else:
            try:
                # Attempt connection to real Redis
                real_client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    decode_responses=True,
                    socket_connect_timeout=1.5,
                )
                real_client.ping()
                self.client = real_client
                self.backend = "redis"
                logger.info(f"Connected to live Redis at {host}:{port}")
            except Exception as e:
                if use_fallback and fakeredis is not None:
                    logger.warning(
                        f"Could not connect to Redis at {host}:{port} ({e}). "
                        "Using in-memory FakeRedis fallback for seamless local operation."
                    )
                    self.client = fakeredis.FakeRedis(decode_responses=True)
                    self.backend = "fakeredis"
                else:
                    logger.error(f"Failed to connect to Redis at {host}:{port}: {e}")
                    raise

    def ping(self) -> bool:
        """Checks if store is alive."""
        try:
            return bool(self.client.ping())
        except Exception:
            return False

    def increment(self, key: str, expiry: Optional[int] = None) -> int:
        """
        Increments counter key. If key was just created and expiry is given,
        sets TTL on the key (SRS Section 4.1).
        """
        count = self.client.incr(key)
        if count == 1 and expiry is not None and expiry > 0:
            self.client.expire(key, expiry)
        return int(count)

    def expire(self, key: str, seconds: int) -> bool:
        """Sets TTL in seconds for a key."""
        if seconds <= 0:
            seconds = 1
        return bool(self.client.expire(key, int(seconds)))

    def ttl(self, key: str) -> int:
        """Returns TTL in seconds (-1 if no expiry, -2 if key does not exist)."""
        val = self.client.ttl(key)
        return int(val) if val is not None else -2

    def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> int:
        """Removes members within score range (SRS Section 4.2)."""
        return int(self.client.zremrangebyscore(key, min_score, max_score))

    def zadd(self, key: str, mapping: Dict[str, float]) -> int:
        """Adds members with scores to sorted set (SRS Section 4.2)."""
        return int(self.client.zadd(key, mapping))

    def zcard(self, key: str) -> int:
        """Returns cardinality of sorted set (SRS Section 4.2)."""
        return int(self.client.zcard(key))

    def zrange(self, key: str, start: int, stop: int, withscores: bool = False) -> List[Any]:
        """Returns range of elements from sorted set."""
        return self.client.zrange(key, start, stop, withscores=withscores)

    def get(self, key: str) -> Optional[str]:
        """Gets string value."""
        val = self.client.get(key)
        return str(val) if val is not None else None

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Sets string value with optional TTL."""
        if ex is not None:
            return bool(self.client.set(key, str(value), ex=int(ex)))
        return bool(self.client.set(key, str(value)))

    def delete(self, *keys: str) -> int:
        """Deletes one or more keys."""
        if not keys:
            return 0
        return int(self.client.delete(*keys))

    def is_blocked(self, client_id: str) -> Tuple[bool, int]:
        """
        Checks if client is temporarily blocked (SRS Section 6.1 & 9).
        Key: 'block:<client_id>'
        Returns: (is_blocked, remaining_ttl)
        """
        block_key = f"block:{client_id}"
        val = self.client.get(block_key)
        if val is not None:
            remaining_ttl = self.ttl(block_key)
            # If TTL is -1 (no expiry) or -2 (expired), handle gracefully
            if remaining_ttl <= 0:
                remaining_ttl = 1
            return True, remaining_ttl
        return False, 0

    def block(self, client_id: str, duration: int) -> bool:
        """
        Sets block key 'block:<client_id>' to 1 with expiry duration (SRS Section 6.1 & 9).
        """
        block_key = f"block:{client_id}"
        return self.set(block_key, "1", ex=duration)

    def get_violation_count(self, client_id: str) -> int:
        """
        Reads violation count for client: 'violation:<client_id>' (SRS Section 6.1 & 9).
        """
        violation_key = f"violation:{client_id}"
        val = self.client.get(violation_key)
        return int(val) if val is not None else 0

    def increment_violation(self, client_id: str, ttl: int = 86400) -> int:
        """
        Increments violation counter for client.
        """
        violation_key = f"violation:{client_id}"
        count = self.client.incr(violation_key)
        if count == 1:
            self.client.expire(violation_key, ttl)
        return int(count)

    def flushdb(self) -> None:
        """Clears all keys in the current DB (used primarily in tests)."""
        self.client.flushdb()
