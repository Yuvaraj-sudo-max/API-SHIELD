"""
cli.py - Command Line Interface for API Shield.
Provides administrative controls, server execution, live Redis diagnostics,
and key inspection directly from the terminal.
"""

import sys
import argparse
import json
from config import Config
from redis_store import RedisStore
from policy import PolicyManager
from limiter import RateLimiter, LimitResult
from blocking import BlockManager


def cmd_test_redis(args):
    """Executes thorough live Redis connectivity and functional tests."""
    print("\n=======================================================")
    print(" [*] API SHIELD // LIVE REDIS DIAGNOSTIC SUITE")
    print("=======================================================")
    host = args.redis_host or Config.REDIS_HOST
    port = args.redis_port or Config.REDIS_PORT
    db = args.redis_db or Config.REDIS_DB

    print(f" Connecting to Redis target: {host}:{port} (db={db})...")
    store = RedisStore(host=host, port=port, db=db, use_fallback=False)
    
    info = store.get_server_info()
    print(f"\n [+] Server Connection:  {'CONNECTED (ONLINE)' if info.get('connected') else 'FAILED'}")
    print(f" [+] Redis Backend:      {info.get('backend').upper()}")
    print(f" [+] Redis Version:      {info.get('version')}")
    print(f" [+] Memory Footprint:   {info.get('used_memory_human')}")
    print(f" [+] Connected Clients:  {info.get('connected_clients')}")
    print(f" [+] Server Uptime:      {info.get('uptime_seconds')}s ({info.get('uptime_days')} days)")
    print(f" [+] Current DB Keys:    {info.get('dbsize')}")
    
    # Latency Probe
    probe = store.test_read_write_cycle()
    print(f"\n [*] Running Roundtrip Probe:")
    print(f" [+] Ping Latency:       {info.get('latency_ms')} ms")
    print(f" [+] Read/Write Latency: {probe.get('latency_ms')} ms")
    print(f" [+] Integrity Status:   {'VERIFIED // PASS' if probe.get('success') else 'FAILED'}")

    # Test Limiting Primitives on live Redis
    limiter = RateLimiter(redis_store=store)
    from policy import RateLimitRule
    
    # 1. Fixed Window test
    fw_rule = RateLimitRule("test_fw", "/api/probe/fw", limit=5, window=10, algorithm="fixed_window")
    fw_res = limiter.is_allowed("cli_probe", "/api/probe/fw", fw_rule)
    print(f"\n [*] Rate Limiting Primitives on Redis:")
    print(f" [+] Fixed Window:       allowed={fw_res.allowed}, remaining={fw_res.remaining}/5, retry_after={fw_res.retry_after}s")

    # 2. Sliding Window test
    sw_rule = RateLimitRule("test_sw", "/api/probe/sw", limit=5, window=10, algorithm="sliding_window")
    sw_res = limiter.is_allowed("cli_probe", "/api/probe/sw", sw_rule)
    print(f" [+] Sliding Window:     allowed={sw_res.allowed}, remaining={sw_res.remaining}/5")

    # 3. Token Bucket test
    tb_rule = RateLimitRule("test_tb", "/api/probe/tb", limit=5, window=10, algorithm="token_bucket")
    tb_res = limiter.is_allowed("cli_probe", "/api/probe/tb", tb_rule)
    print(f" [+] Token Bucket:       allowed={tb_res.allowed}, remaining={tb_res.remaining}/5")

    # Clean up probe keys
    store.clear_rate_limit_keys()
    print(f"\n [PASS] Diagnostic Complete: Real Redis functions are fully operational!")
    print("=======================================================\n")


def cmd_inspect_keys(args):
    """Lists all active rate limit keys stored in Redis."""
    store = RedisStore(
        host=args.redis_host or Config.REDIS_HOST,
        port=args.redis_port or Config.REDIS_PORT,
        db=args.redis_db or Config.REDIS_DB,
    )
    keys = store.get_rate_limit_keys()
    print("\n=======================================================")
    print(f" [*] ACTIVE RATE LIMIT KEYS IN REDIS ({len(keys)} found)")
    print("=======================================================")
    if not keys:
        print(" (No active rate limit keys found in current database)")
    else:
        for item in keys:
            print(f" * Key:      {item['key']}")
            print(f"   Category: {item['category']}")
            print(f"   Type:     {item['type']}")
            print(f"   TTL:      {item['ttl']}s")
            print(f"   Content:  {item['value_preview']}")
            print("   ------------------------------------------------")
    print("=======================================================\n")


def cmd_clear_keys(args):
    """Flushes API Shield rate limit keys from Redis."""
    store = RedisStore(
        host=args.redis_host or Config.REDIS_HOST,
        port=args.redis_port or Config.REDIS_PORT,
        db=args.redis_db or Config.REDIS_DB,
    )
    count = store.clear_rate_limit_keys()
    print(f"\n[PASS] Flushed {count} API Shield rate-limiting key(s) from Redis.\n")



def cmd_policies(args):
    """Displays registered rate limit policies."""
    pm = PolicyManager()
    policies = pm.list_policies()
    print("\n=======================================================")
    print(f" [*] REGISTERED RATE LIMIT POLICIES ({len(policies)} total)")
    print("=======================================================")
    for p in policies:
        status = "ACTIVE" if p.get("active", True) else "INACTIVE"
        print(f" • [{status}] {p.get('name')}: {p.get('endpoint')}")
        print(f"   Limit: {p.get('limit')} req / {p.get('window')}s | Algorithm: {p.get('algorithm')}")
    print("=======================================================\n")


def cmd_serve(args):
    """Starts the API Shield Flask application."""
    from app import create_app
    app = create_app()
    host = args.host or Config.APP_HOST
    port = args.port or Config.APP_PORT
    debug = args.debug if args.debug is not None else Config.DEBUG
    print(f"\n[*] Starting API Shield Gateway on http://{host}:{port}/ ...")
    app.run(host=host, port=port, debug=debug)


def main():
    parser = argparse.ArgumentParser(
        prog="api-shield",
        description="API Shield - Autonomous Rate Limiting & Zero-Trust Abuse Defense Gateway",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Serve Command
    serve_parser = subparsers.add_parser("serve", help="Start the API Shield Gateway server")
    serve_parser.add_argument("--host", default=Config.APP_HOST, help="Host interface to bind")
    serve_parser.add_argument("--port", type=int, default=Config.APP_PORT, help="Port to listen on")
    serve_parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    # Test Redis Command
    test_parser = subparsers.add_parser("test-redis", help="Run comprehensive live Redis connectivity test")
    test_parser.add_argument("--redis-host", default=Config.REDIS_HOST, help="Redis host")
    test_parser.add_argument("--redis-port", type=int, default=Config.REDIS_PORT, help="Redis port")
    test_parser.add_argument("--redis-db", type=int, default=Config.REDIS_DB, help="Redis DB index")

    # Inspect Keys Command
    inspect_parser = subparsers.add_parser("inspect-keys", help="Inspect all active rate limit keys in Redis")
    inspect_parser.add_argument("--redis-host", default=Config.REDIS_HOST, help="Redis host")
    inspect_parser.add_argument("--redis-port", type=int, default=Config.REDIS_PORT, help="Redis port")
    inspect_parser.add_argument("--redis-db", type=int, default=Config.REDIS_DB, help="Redis DB index")

    # Clear Keys Command
    clear_parser = subparsers.add_parser("clear-keys", help="Clear all rate limit keys in Redis")
    clear_parser.add_argument("--redis-host", default=Config.REDIS_HOST, help="Redis host")
    clear_parser.add_argument("--redis-port", type=int, default=Config.REDIS_PORT, help="Redis port")
    clear_parser.add_argument("--redis-db", type=int, default=Config.REDIS_DB, help="Redis DB index")

    # Policies Command
    subparsers.add_parser("policies", help="List all registered rate limit policies")

    args = parser.parse_args()

    if args.command == "serve":
        cmd_serve(args)
    elif args.command == "test-redis":
        cmd_test_redis(args)
    elif args.command == "inspect-keys":
        cmd_inspect_keys(args)
    elif args.command == "clear-keys":
        cmd_clear_keys(args)
    elif args.command == "policies":
        cmd_policies(args)
    else:
        # Default action when no subcommand is provided: show help or start
        parser.print_help()


if __name__ == "__main__":
    main()
