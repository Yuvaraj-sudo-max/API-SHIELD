"""
blocking.py - Temporary blocking and abuse prevention module for API Shield.
Implements SRS Section 6 & Section 11 (BlockManager).
"""

from typing import Tuple
from redis_store import RedisStore


class BlockManager:
    """
    Handles repeated rate-limit violations and applies temporary client blocks
    according to SRS Section 6.1:
      - 1–3 violations: 5 minutes (300s)
      - 4–6 violations: 15 minutes (900s)
      - 7+ violations: 30 minutes (1800s)
    """

    def __init__(self, redis_store: RedisStore):
        self.redis_store = redis_store

    @staticmethod
    def get_block_duration(violations: int) -> int:
        """
        Calculates block duration in seconds based on violation count (SRS 6.1).
        """
        if violations <= 3:
            return 300   # 5 minutes
        elif violations <= 6:
            return 900   # 15 minutes
        else:
            return 1800  # 30 minutes

    def is_blocked(self, client_id: str) -> Tuple[bool, int]:
        """
        Checks whether client is currently blocked.
        Returns: (is_blocked: bool, remaining_ttl: int)
        """
        return self.redis_store.is_blocked(client_id)

    def block_client(self, client_id: str, duration: int) -> bool:
        """
        Explicitly sets block on client for duration seconds.
        """
        return self.redis_store.block(client_id, duration)

    def record_violation(self, client_id: str) -> Tuple[int, int]:
        """
        Increases client's violation count, computes block duration,
        and sets temporary block in Redis (SRS Section 6.2).
        Returns: (violation_count, block_duration_seconds)
        """
        violation_count = self.redis_store.increment_violation(client_id)
        block_duration = self.get_block_duration(violation_count)
        self.block_client(client_id, block_duration)
        return violation_count, block_duration


if __name__ == "__main__":
    print("=== API Shield - BlockManager Demo ===")
    store = RedisStore()
    manager = BlockManager(store)
    test_client = "key:sample_violator"
    print(f"Testing violation progression for client: {test_client}\n")
    for i in range(1, 8):
        count, duration = manager.record_violation(test_client)
        blocked, ttl = manager.is_blocked(test_client)
        print(f"  Violation #{count} -> Block duration: {duration}s ({duration // 60} min) | Blocked: {blocked} (TTL: {ttl}s)")
    print("\nDemonstration complete.")
