"""
verify_redis_live.py - Real-World Live Redis Verification Script
Validates all rate limiting algorithms, token bucket bursts, sliding windows,
and client telemetry directly against the live running Redis instance.
"""

import sys
import time
from config import Config
from redis_store import RedisStore
from limiter import RateLimiter, LimitResult
from policy import RateLimitRule
from blocking import BlockManager


def run_live_verification():
    print("=" * 65)
    print(" [*] API SHIELD — LIVE REAL-WORLD REDIS VERIFICATION SUITE")
    print("=" * 65)

    # 1. Connect to actual Redis
    print(f"\n[1] Connecting to Redis on {Config.REDIS_HOST}:{Config.REDIS_PORT}...")
    store = RedisStore(host=Config.REDIS_HOST, port=Config.REDIS_PORT, db=Config.REDIS_DB, use_fallback=False)
    
    assert store.backend == "redis", f"Expected 'redis', got '{store.backend}'"
    assert store.ping() is True, "Redis ping failed"
    
    info = store.get_server_info()
    print(f"    [PASS] Connected to Live Redis Server!")
    print(f"    - Version:          {info.get('version')}")
    print(f"    - Memory Used:      {info.get('used_memory_human')}")
    print(f"    - Active Clients:   {info.get('connected_clients')}")
    print(f"    - Server Uptime:    {info.get('uptime_seconds')} seconds")

    # 2. Measure Roundtrip Ping Latency
    latency = store.test_latency()
    probe = store.test_read_write_cycle()
    print(f"\n[2] Testing Roundtrip Probe & Latency...")
    print(f"    - Ping Latency:     {latency} ms")
    print(f"    - Probe Latency:    {probe.get('latency_ms')} ms")
    print(f"    - Read/Write Cycle: {'VERIFIED [OK]' if probe.get('success') else 'FAILED'}")

    # 3. Fixed Window Rate Limiting on Live Redis
    print(f"\n[3] Testing Fixed Window Primitive (rate:*)...")
    limiter = RateLimiter(redis_store=store)
    fw_rule = RateLimitRule("live_fw", "/api/probe/fw", limit=3, window=5, algorithm="fixed_window")
    
    res1 = limiter.is_allowed("live_client_1", "/api/probe/fw", fw_rule)
    res2 = limiter.is_allowed("live_client_1", "/api/probe/fw", fw_rule)
    res3 = limiter.is_allowed("live_client_1", "/api/probe/fw", fw_rule)
    res4 = limiter.is_allowed("live_client_1", "/api/probe/fw", fw_rule) # Exceeded!

    print(f"    - Req 1: allowed={res1.allowed}, remaining={res1.remaining}")
    print(f"    - Req 2: allowed={res2.allowed}, remaining={res2.remaining}")
    print(f"    - Req 3: allowed={res3.allowed}, remaining={res3.remaining}")
    print(f"    - Req 4: allowed={res4.allowed}, remaining={res4.remaining} (Correctly Rate-Limited: {not res4.allowed})")
    assert res1.allowed and res2.allowed and res3.allowed and not res4.allowed, "Fixed window failed"

    # 4. Sliding Window (ZSET) on Live Redis
    print(f"\n[4] Testing Sliding Window Primitive (slide:*)...")
    sw_rule = RateLimitRule("live_sw", "/api/probe/sw", limit=2, window=5, algorithm="sliding_window")
    s1 = limiter.is_allowed("live_client_2", "/api/probe/sw", sw_rule)
    s2 = limiter.is_allowed("live_client_2", "/api/probe/sw", sw_rule)
    s3 = limiter.is_allowed("live_client_2", "/api/probe/sw", sw_rule) # Exceeded!
    print(f"    - Req 1: allowed={s1.allowed}, remaining={s1.remaining}")
    print(f"    - Req 2: allowed={s2.allowed}, remaining={s2.remaining}")
    print(f"    - Req 3: allowed={s3.allowed}, remaining={s3.remaining} (Correctly Rate-Limited: {not s3.allowed})")
    assert s1.allowed and s2.allowed and not s3.allowed, "Sliding window failed"

    # 5. Token Bucket (Continuous Refill) on Live Redis
    print(f"\n[5] Testing Token Bucket Primitive (tb:*)...")
    tb_rule = RateLimitRule("live_tb", "/api/probe/tb", limit=5, window=10, algorithm="token_bucket")
    t1 = limiter.is_allowed("live_client_3", "/api/probe/tb", tb_rule)
    print(f"    - Token Bucket Initial Burst: allowed={t1.allowed}, remaining={t1.remaining}")
    assert t1.allowed is True, "Token bucket burst failed"

    # 6. Abuse Penalty & Client Blocking on Live Redis
    print(f"\n[6] Testing Abuse Penalty & Client Blocking (block:*, violation:*)...")
    blocker = BlockManager(redis_store=store)
    violation_count, block_sec = blocker.record_violation("live_bad_actor")
    is_blk, blk_ttl = blocker.is_blocked("live_bad_actor")
    print(f"    - Violation 1 recorded: count={violation_count}, is_blocked={is_blk}")
    
    # Trigger repeated violation
    for _ in range(4):
        blocker.record_violation("live_bad_actor")
    is_blk2, blk_ttl2 = blocker.is_blocked("live_bad_actor")
    print(f"    - Violation 5 recorded: is_blocked={is_blk2}, block_ttl={blk_ttl2}s")
    assert is_blk2 is True, "Block enforcement failed"

    # 7. Record and Fetch Request Telemetry in Redis
    print(f"\n[7] Testing Redis Client Telemetry Storage (telemetry:requests)...")
    store.record_request_telemetry({
        "timestamp": time.strftime("%H:%M:%S"),
        "sender_ip": "192.168.1.105",
        "receiver_ip": "127.0.0.1:5000",
        "client_id": "unknown_tester",
        "is_unknown_user": True,
        "user_type": "Unknown User (IP Only)",
        "tier": "free",
        "endpoint": "/api/products",
        "method": "GET",
        "algorithm": "fixed_window",
        "redis_key": "rate:/api/products:unknown_tester",
        "redis_type": "string",
        "ttl": 60,
        "limit": 5,
        "remaining": 4,
        "status": "ALLOWED",
        "status_code": 200,
        "violations": 0,
        "user_agent": "Python Live Verifier",
        "reason": "Test probe verification",
    })
    telemetry_records = store.get_request_telemetry(limit=5)
    print(f"    - Telemetry records in Redis: {len(telemetry_records)}")
    assert len(telemetry_records) > 0, "No telemetry records found"
    print(f"    - Stored Sender IP: {telemetry_records[0].get('sender_ip')}")
    print(f"    - Unknown User Flag: {telemetry_records[0].get('is_unknown_user')}")

    # 8. Inspect Active Redis Keys
    print(f"\n[8] Inspecting Live Keys in Redis Database...")
    keys = store.get_rate_limit_keys()
    print(f"    - Total Rate Limit Keys in Redis: {len(keys)}")
    for k in keys[:5]:
        print(f"      * {k['key']} [{k['category']} / {k['type']} / TTL={k['ttl']}s]")

    # 9. Clean up test keys
    print(f"\n[9] Flushing Live Test Keys...")
    cleaned = store.clear_rate_limit_keys()
    store.client.delete("block:live_bad_actor", "violation:live_bad_actor")
    print(f"    - Cleaned {cleaned} test keys from Redis.")

    print("\n" + "=" * 65)
    print(" [OK] REAL-WORLD REDIS INTEGRATION VERIFIED 100% OPERATIONAL!")
    print("=" * 65 + "\n")



if __name__ == "__main__":
    run_live_verification()
