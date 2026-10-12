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
        self.pool = None

        if client is not None:
            self.client = client
            self.backend = "custom"
        else:
            try:
                # Production-grade Connection Pool for live Redis
                self.pool = redis.ConnectionPool(
                    host=host,
                    port=port,
                    db=db,
                    decode_responses=True,
                    socket_connect_timeout=2.0,
                    socket_timeout=2.0,
                    socket_keepalive=True,
                    max_connections=50,
                    retry_on_timeout=True,
                )
                real_client = redis.Redis(connection_pool=self.pool)
                real_client.ping()
                self.client = real_client
                self.backend = "redis"
                logger.info(f"Connected to live Redis at {host}:{port} (db={db})")
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

    def test_latency(self) -> float:
        """Measures ping roundtrip latency in milliseconds."""
        try:
            t0 = time.perf_counter()
            self.client.ping()
            t1 = time.perf_counter()
            return round((t1 - t0) * 1000.0, 2)
        except Exception:
            return -1.0

    def test_read_write_cycle(self) -> Dict[str, Any]:
        """Tests end-to-end write, read, and delete cycle against the Redis instance."""
        test_key = "shield:selftest"
        test_val = f"live_probe_{int(time.time() * 1000)}"
        t0 = time.perf_counter()
        try:
            self.client.set(test_key, test_val, ex=10)
            read_back = self.client.get(test_key)
            self.client.delete(test_key)
            t1 = time.perf_counter()
            success = (read_back == test_val)
            latency_ms = round((t1 - t0) * 1000.0, 2)
            return {
                "success": success,
                "latency_ms": latency_ms,
                "backend": self.backend,
                "host": self.host,
                "port": self.port,
                "verified": success,
            }
        except Exception as e:
            return {
                "success": False,
                "latency_ms": -1.0,
                "error": str(e),
                "backend": self.backend,
            }

    def get_server_info(self) -> Dict[str, Any]:
        """
        Retrieves real-time server information, memory, version, and database statistics.
        Works with both live Redis server and FakeRedis.
        """
        try:
            info = self.client.info() if hasattr(self.client, "info") else {}
            version = info.get("redis_version", "unknown" if self.backend != "fakeredis" else "fakeredis-virtual")
            uptime_sec = int(info.get("uptime_in_seconds", 0))
            used_mem_human = info.get("used_memory_human", "in-memory")
            used_mem_bytes = info.get("used_memory", 0)
            clients_connected = int(info.get("connected_clients", 1))
            total_commands = int(info.get("total_commands_processed", 0))
            role = info.get("role", "master")
            try:
                db_size = self.client.dbsize()
            except Exception:
                db_size = 0

            return {
                "connected": self.ping(),
                "backend": self.backend,
                "version": version,
                "host": self.host,
                "port": self.port,
                "db": self.db,
                "uptime_seconds": uptime_sec,
                "uptime_days": round(uptime_sec / 86400, 1),
                "used_memory_human": used_mem_human,
                "used_memory_bytes": used_mem_bytes,
                "connected_clients": clients_connected,
                "total_commands": total_commands,
                "role": role,
                "dbsize": db_size,
                "latency_ms": self.test_latency(),
            }
        except Exception as e:
            logger.warning(f"Failed to fetch Redis server info: {e}")
            return {
                "connected": self.ping(),
                "backend": self.backend,
                "version": "unknown",
                "error": str(e),
                "dbsize": 0,
            }

    def get_rate_limit_keys(self, pattern: str = "*") -> List[Dict[str, Any]]:
        """
        Inspects all active keys matching API Shield patterns.
        Returns key names, data types, TTLs, categories, and representations.
        """
        results = []
        try:
            keys = self.client.keys(pattern)
            for k in keys:
                # Classify key category
                category = "other"
                if k.startswith("rate:"):
                    category = "fixed_window"
                elif k.startswith("slide:"):
                    category = "sliding_window"
                elif k.startswith("tb:"):
                    category = "token_bucket"
                elif k.startswith("block:"):
                    category = "client_block"
                elif k.startswith("violation:"):
                    category = "violation_tracker"
                elif k.startswith("shield:"):
                    category = "system_probe"

                try:
                    ktype = self.client.type(k)
                except Exception:
                    ktype = "string"

                ttl_val = self.ttl(k)

                # Safe value preview
                val_preview = ""
                try:
                    if ktype == "string":
                        val_preview = str(self.client.get(k))
                    elif ktype == "zset":
                        card = self.client.zcard(k)
                        val_preview = f"{card} timestamp(s)"
                    elif ktype == "hash":
                        val_preview = "hash table"
                    else:
                        val_preview = f"type: {ktype}"
                except Exception:
                    val_preview = "unavailable"

                results.append({
                    "key": k,
                    "category": category,
                    "type": ktype,
                    "ttl": ttl_val,
                    "value_preview": val_preview,
                })
        except Exception as e:
            logger.warning(f"Error inspecting Redis keys: {e}")

        # Sort so active blocks and high-traffic keys appear first
        results.sort(key=lambda x: (x["category"] != "client_block", x["key"]))
        return results

    def clear_rate_limit_keys(self) -> int:
        """
        Clears only API Shield rate limit keys (rate:*, slide:*, tb:*, block:*, violation:*),
        preserving any other data in the Redis database.
        """
        patterns = ["rate:*", "slide:*", "tb:*", "block:*", "violation:*", "shield:*"]
        deleted_count = 0
        for pat in patterns:
            try:
                matched = self.client.keys(pat)
                if matched:
                    deleted_count += int(self.client.delete(*matched))
            except Exception as e:
                logger.warning(f"Error clearing pattern {pat}: {e}")
        return deleted_count

    def record_request_telemetry(self, item: Dict[str, Any]) -> None:
        """
        Stores live client request telemetry directly in Redis under 'telemetry:requests'.
        Retains the latest 150 requests with a 24h expiration.
        """
        try:
            import json
            raw = json.dumps(item)
            self.client.lpush("telemetry:requests", raw)
            self.client.ltrim("telemetry:requests", 0, 149)
            self.client.expire("telemetry:requests", 86400)
        except Exception as e:
            logger.debug(f"Failed to record request telemetry in Redis: {e}")

    def get_request_telemetry(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves real-time request records from Redis list 'telemetry:requests'.
        """
        results = []
        try:
            import json
            items = self.client.lrange("telemetry:requests", 0, limit - 1)
            for it in items:
                try:
                    results.append(json.loads(it))
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Failed to load request telemetry from Redis: {e}")
        return results


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
