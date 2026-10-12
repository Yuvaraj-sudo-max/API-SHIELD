"""
routes.py - API route definitions and rate-limiting middleware for API Shield.
Implements SRS Section 7.1, 8.1, 8.2, 8.3, 10.1, 13, and 23.
"""

from flask import Blueprint, request, jsonify, g, render_template, Response
from identity import get_client_id, get_client_tier, get_tier_multiplier
from policy import PolicyManager, RateLimitRule
from limiter import RateLimiter
from blocking import BlockManager
from logging_utils import RequestLogger
from metrics import global_metrics

api_bp = Blueprint("api", __name__)


def create_rate_limiter_middleware(
    app,
    policy_manager: PolicyManager,
    rate_limiter: RateLimiter,
    block_manager: BlockManager,
    request_logger: RequestLogger,
    redis_store=None,
):
    """
    Registers Flask before_request and after_request hooks implementing
    the exact Request Decision Logic flow from SRS Section 5.1 and Section 23
    with multi-tenant client tiering, Prometheus metrics, and live Redis telemetry tracking.
    """

    @app.before_request
    def check_rate_limits():
        import time as _t
        endpoint = request.path
        client_id = get_client_id(request)
        tier = get_client_tier(request)

        # Telemetry Metadata Extraction
        sender_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1").split(",")[0].strip()
        receiver_ip = request.host or "127.0.0.1:5000"
        has_api_key = bool(request.headers.get("X-API-Key"))
        user_type = "Identified Client" if has_api_key else "Unknown User (IP Only)"
        user_agent = request.headers.get("User-Agent", "Unknown-Agent")[:60]
        time_str = _t.strftime("%H:%M:%S")

        current_store = redis_store or getattr(app, "redis_store", None)

        # 1. Find active policy for the endpoint (BR-01, BR-02)
        policy = policy_manager.get_policy_for_endpoint(endpoint)
        if not policy:
            # If no active policy exists, allow request without limiting
            return None

        # Multi-Tenant Client Tier Scaling
        multiplier = get_tier_multiplier(tier)
        effective_limit = max(1, int(policy.limit * multiplier))
        if multiplier != 1.0:
            effective_policy = RateLimitRule(
                name=policy.name,
                endpoint=policy.endpoint,
                limit=effective_limit,
                window=policy.window,
                algorithm=policy.algorithm,
                active=policy.active,
            )
        else:
            effective_policy = policy

        key_prefix = "slide" if policy.algorithm == "sliding_window" else "tb" if policy.algorithm == "token_bucket" else "rate"
        current_redis_key = f"{key_prefix}:{endpoint}:{client_id}"
        redis_type = "zset" if policy.algorithm == "sliding_window" else "hash" if policy.algorithm == "token_bucket" else "string"
        ttl_val = getattr(current_store, "ttl", lambda k: policy.window)(current_redis_key) if current_store else policy.window
        violation_count = getattr(current_store, "get_violation_count", lambda k: 0)(client_id) if current_store else 0

        def log_redis_telemetry(status, status_code, remaining, reason):
            if current_store and hasattr(current_store, "record_request_telemetry"):
                current_store.record_request_telemetry({
                    "timestamp": time_str,
                    "sender_ip": sender_ip,
                    "receiver_ip": receiver_ip,
                    "client_id": client_id,
                    "is_unknown_user": not has_api_key,
                    "user_type": user_type,
                    "tier": tier,
                    "endpoint": endpoint,
                    "method": request.method,
                    "algorithm": policy.algorithm,
                    "redis_key": current_redis_key,
                    "redis_type": redis_type,
                    "ttl": max(0, ttl_val) if ttl_val > 0 else policy.window,
                    "limit": effective_policy.limit,
                    "remaining": remaining,
                    "status": status,
                    "status_code": status_code,
                    "violations": violation_count,
                    "user_agent": user_agent,
                    "reason": reason,
                })

        # 2. Check if client is temporarily blocked (SRS Section 6.2 & 23)
        blocked, block_ttl = block_manager.is_blocked(client_id)
        if blocked:
            global_metrics.record_block(endpoint, policy.algorithm)
            global_metrics.record_request(endpoint, 429, tier)
            request_logger.log_blocked(
                client_id=client_id,
                endpoint=endpoint,
                reason="Temporary client block active",
                retry_after=block_ttl,
            )
            log_redis_telemetry(
                status="BLOCKED",
                status_code=429,
                remaining=0,
                reason=f"Temporary client block active ({block_ttl}s remaining)"
            )
            response = jsonify({
                "error": "Rate limit exceeded",
                "message": "Please try again later",
                "details": f"Client temporarily blocked for repeated violations. Retry in {block_ttl}s."
            })
            response.status_code = 429
            response.headers["X-RateLimit-Limit"] = str(effective_policy.limit)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["Retry-After"] = str(block_ttl)
            response.headers["X-Client-Tier"] = tier
            return response

        # 3. Evaluate rate limit algorithm (Fixed Window, Sliding Window, or Token Bucket)
        res = rate_limiter.is_allowed(client_id, endpoint, effective_policy)

        if not res.allowed:
            global_metrics.record_block(endpoint, policy.algorithm)
            global_metrics.record_request(endpoint, 429, tier)

            # 4. Record violation and trigger temporary blocking if necessary
            violation_count, block_duration = block_manager.record_violation(client_id)
            retry_after = res.retry_after or block_duration

            request_logger.log_blocked(
                client_id=client_id,
                endpoint=endpoint,
                reason=f"Limit exceeded ({res.count}/{effective_policy.limit} in {effective_policy.window}s)",
                retry_after=retry_after,
            )
            log_redis_telemetry(
                status="LIMITED",
                status_code=429,
                remaining=0,
                reason=f"Limit exceeded ({res.count}/{effective_policy.limit} in {effective_policy.window}s)"
            )

            response = jsonify({
                "error": "Rate limit exceeded",
                "message": "Please try again later"
            })
            response.status_code = 429
            response.headers["X-RateLimit-Limit"] = str(effective_policy.limit)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["Retry-After"] = str(retry_after)
            response.headers["X-Client-Tier"] = tier
            return response

        # 5. Request allowed: pass metadata to after_request to inject headers
        g.rate_limit_info = {
            "limit": effective_policy.limit,
            "remaining": res.remaining,
            "client_id": client_id,
            "endpoint": endpoint,
            "tier": tier,
        }
        request_logger.log_allowed(client_id, endpoint, res.remaining)
        log_redis_telemetry(
            status="ALLOWED",
            status_code=200,
            remaining=res.remaining,
            reason="Rate limit quota verified & allowed"
        )
        return None

    @app.after_request
    def inject_rate_limit_headers(response):
        tier = "free"
        if hasattr(g, "rate_limit_info"):
            response.headers["X-RateLimit-Limit"] = str(g.rate_limit_info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(g.rate_limit_info["remaining"])
            tier = g.rate_limit_info.get("tier", "free")
            response.headers["X-Client-Tier"] = tier
        global_metrics.record_request(request.path, response.status_code, tier)
        return response


def register_routes(
    app,
    policy_manager: PolicyManager,
    redis_store,
    request_logger: RequestLogger,
    ai_service=None,
):
    """Registers all API and dashboard routes on the Flask application."""
    if ai_service is None:
        from ai_service import AIService
        ai_service = AIService()

    # ------------------------------------------------------------------
    # Unprotected Health Check & Prometheus Metrics (SRS Section 8.1)
    # ------------------------------------------------------------------
    @app.route("/health", methods=["GET"])
    def health_check():
        redis_alive = redis_store.ping()
        status = "healthy" if redis_alive else "degraded"
        return jsonify({
            "status": status,
            "redis": "connected" if redis_alive else "disconnected",
            "backend": getattr(redis_store, "backend", "unknown"),
        }), 200

    @app.route("/metrics", methods=["GET"])
    def prometheus_metrics():
        """Exports Prometheus standard exposition metrics (version 0.0.4)."""
        text = global_metrics.export_prometheus(policy_manager=policy_manager)
        return Response(text, mimetype="text/plain; version=0.0.4")


    # ------------------------------------------------------------------
    # Policy Management Endpoints (SRS Section 7.1 & FR-11, FR-12)
    # ------------------------------------------------------------------
    @app.route("/api/policies", methods=["GET"])
    def list_policies():
        policies = policy_manager.list_policies()
        return jsonify({"policies": policies, "total": len(policies)}), 200

    @app.route("/api/policies", methods=["POST"])
    def create_policy():
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({"error": "Invalid policy", "message": "JSON body is required"}), 400

        try:
            rule = policy_manager.create_policy(data)
            return jsonify({
                "message": "Policy created successfully",
                "policy": rule.to_dict()
            }), 201
        except ValueError as e:
            return jsonify({"error": "Invalid policy", "message": str(e)}), 400

    @app.route("/api/policies/<name>", methods=["GET"])
    def get_policy(name):
        rule = policy_manager.get_policy(name)
        if not rule:
            return jsonify({"error": "Policy not found", "message": f"No policy named '{name}'"}), 404
        return jsonify({"policy": rule.to_dict()}), 200

    @app.route("/api/policies/<name>", methods=["PUT"])
    def update_policy(name):
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({"error": "Invalid policy", "message": "JSON body is required"}), 400

        try:
            rule = policy_manager.update_policy(name, data)
            return jsonify({
                "message": "Policy updated successfully",
                "policy": rule.to_dict()
            }), 200
        except KeyError:
            return jsonify({"error": "Policy not found", "message": f"No policy named '{name}'"}), 404
        except ValueError as e:
            return jsonify({"error": "Invalid policy", "message": str(e)}), 400

    @app.route("/api/policies/<name>/activate", methods=["POST"])
    def activate_policy(name):
        try:
            rule = policy_manager.activate_policy(name)
            return jsonify({
                "message": "Policy activated successfully",
                "policy": rule.to_dict()
            }), 200
        except KeyError:
            return jsonify({"error": "Policy not found", "message": f"No policy named '{name}'"}), 404

    @app.route("/api/policies/<name>/deactivate", methods=["POST"])
    def deactivate_policy(name):
        try:
            rule = policy_manager.deactivate_policy(name)
            return jsonify({
                "message": "Policy deactivated successfully",
                "policy": rule.to_dict()
            }), 200
        except KeyError:
            return jsonify({"error": "Policy not found", "message": f"No policy named '{name}'"}), 404

    @app.route("/api/policies/<name>", methods=["DELETE"])
    def delete_policy_endpoint(name):
        deleted = policy_manager.delete_policy(name)
        if not deleted:
            return jsonify({"error": "Policy not found", "message": f"No policy named '{name}'"}), 404
        return jsonify({"message": f"Policy '{name}' deleted successfully"}), 200

    @app.route("/api/unblock", methods=["POST"])
    def unblock_client_endpoint():
        data = request.get_json(silent=True) or {}
        client_key = data.get("client_id") or data.get("key")
        if not client_key:
            client_key = get_client_id(request)
        keys_to_clear = [
            f"block:{client_key}",
            f"violation:{client_key}",
            f"block:key:{client_key}",
            f"violation:key:{client_key}",
            f"block:ip:{client_key}",
            f"violation:ip:{client_key}",
        ]
        redis_store.delete(*keys_to_clear)
        return jsonify({"message": f"Client '{client_key}' unblocked successfully", "unblocked": True}), 200

    @app.route("/api/reset-counters", methods=["POST"])
    def reset_counters_endpoint():
        redis_store.flushdb()
        return jsonify({"message": "Redis rate-limiting counters reset successfully"}), 200

    @app.route("/api/stats", methods=["GET"])
    def get_stats_endpoint():
        policies = policy_manager.list_policies()
        active_count = sum(1 for p in policies if p.get("active", True))
        logs = request_logger.get_recent_logs()
        allowed = sum(1 for l in logs if l.get("status") == "ALLOWED")
        limited = sum(1 for l in logs if l.get("status") == "LIMITED")
        blocked = sum(1 for l in logs if l.get("status") == "BLOCKED")
        ai_info = ai_service.check_status() if ai_service else {}
        redis_info = redis_store.get_server_info() if hasattr(redis_store, "get_server_info") else {}
        return jsonify({
            "policies_total": len(policies),
            "policies_active": active_count,
            "total_requests": len(logs),
            "allowed_requests": allowed,
            "limited_requests": limited,
            "blocked_requests": blocked,
            "backend": getattr(redis_store, "backend", "redis"),
            "health": "healthy" if redis_store.ping() else "degraded",
            "redis_info": redis_info,
            "redis_version": redis_info.get("version", "unknown"),
            "redis_memory": redis_info.get("used_memory_human", "0K"),
            "redis_latency_ms": redis_info.get("latency_ms", 0.0),
            "redis_keys_count": redis_info.get("dbsize", 0),
            "ai_status": ai_info.get("status", "not_configured"),
            "ai_connected": ai_info.get("connected", False),
            "ai_provider": ai_info.get("provider", "DeepSeek"),
            "ai_model": ai_info.get("model", "deepseek-flash"),
            "ai_key_masked": ai_info.get("key_masked", "none"),
        }), 200

    # ------------------------------------------------------------------
    # Live Redis Diagnostics & Real-World Inspection Endpoints
    # ------------------------------------------------------------------
    @app.route("/api/redis/info", methods=["GET"])
    def get_redis_info_endpoint():
        """Returns live server metrics from Redis (Version, Memory, Uptime, Clients)."""
        info = redis_store.get_server_info() if hasattr(redis_store, "get_server_info") else {}
        return jsonify(info), 200

    @app.route("/api/redis/keys", methods=["GET"])
    def get_redis_keys_endpoint():
        """Inspects all rate limit and client tracking keys active in Redis."""
        keys = redis_store.get_rate_limit_keys() if hasattr(redis_store, "get_rate_limit_keys") else []
        return jsonify({"keys": keys, "total": len(keys)}), 200

    @app.route("/api/redis/clear", methods=["POST"])
    def clear_redis_keys_endpoint():
        """Cleanses only API Shield rate limiter keys, preserving foreign DB keys."""
        deleted = redis_store.clear_rate_limit_keys() if hasattr(redis_store, "clear_rate_limit_keys") else 0
        return jsonify({
            "message": f"Flushed {deleted} rate-limiting key(s) from Redis.",
            "deleted_count": deleted
        }), 200

    @app.route("/api/redis/test", methods=["POST"])
    def test_redis_connection_endpoint():
        """Performs full write/read/delete cycle against Redis and measures roundtrip latency."""
        res = redis_store.test_read_write_cycle() if hasattr(redis_store, "test_read_write_cycle") else {"success": False}
        return jsonify(res), 200

    @app.route("/api/redis/telemetry", methods=["GET"])
    def get_redis_telemetry_endpoint():
        """
        Returns full live Redis storage inspection details:
        - Live Redis server metadata & health
        - Real-time client request ledger (sender IP, receiver IP, unknown user status, endpoint, quota, Redis key, TTL)
        - All active rate limiting keys in Redis DB 0
        """
        info = redis_store.get_server_info() if hasattr(redis_store, "get_server_info") else {}
        requests_list = redis_store.get_request_telemetry(limit=100) if hasattr(redis_store, "get_request_telemetry") else []
        keys = redis_store.get_rate_limit_keys() if hasattr(redis_store, "get_rate_limit_keys") else []
        unknown_users = sum(1 for r in requests_list if r.get("is_unknown_user"))
        return jsonify({
            "server_info": info,
            "requests": requests_list,
            "keys": keys,
            "total_requests": len(requests_list),
            "unknown_users_count": unknown_users,
            "total_keys": len(keys),
        }), 200

    @app.route("/api/redis/delete-key", methods=["POST"])
    def delete_single_redis_key_endpoint():
        """Deletes a specific key from Redis storage."""
        data = request.get_json(silent=True) or {}
        key = data.get("key")
        if not key:
            return jsonify({"error": "Bad request", "message": "Key name is required."}), 400
        deleted = redis_store.delete(key)
        return jsonify({
            "message": f"Key '{key}' deleted from Redis.",
            "deleted": bool(deleted),
            "key": key
        }), 200



    # ------------------------------------------------------------------
    # Protected API Endpoints (SRS Section 8.1 & 8.2)
    # ------------------------------------------------------------------
    @app.route("/api/products", methods=["GET"])
    def get_products():
        return jsonify({
            "message": "Request successful",
            "data": [
                {"id": 1, "name": "Laptop Pro 15", "price": 1299.99, "stock": 45},
                {"id": 2, "name": "Wireless Noise-Cancelling Headphones", "price": 199.50, "stock": 120},
                {"id": 3, "name": "Mechanical Gaming Keyboard", "price": 89.00, "stock": 78},
            ]
        }), 200

    @app.route("/api/users", methods=["GET"])
    def get_users():
        return jsonify({
            "message": "Request successful",
            "data": [
                {"id": 1, "username": "alice", "role": "admin"},
                {"id": 2, "username": "bob", "role": "developer"},
                {"id": 3, "username": "charlie", "role": "viewer"},
            ]
        }), 200

    @app.route("/api/stream", methods=["GET"])
    def get_stream():
        """Demonstration endpoint protected by Token Bucket algorithm."""
        return jsonify({
            "message": "Real-time telemetry event stream active",
            "algorithm": "token_bucket",
            "stream_id": "strm_live_quantum_channel",
            "events": [
                {"event": "GATEWAY_PULSE", "severity": "LOW"},
                {"event": "SHIELD_SYNCHRONIZED", "severity": "INFO"},
            ]
        }), 200

    @app.route("/api/login", methods=["POST"])
    def login():
        data = request.get_json(silent=True) or {}
        username = data.get("username", "guest")
        password = data.get("password")

        # Sample roles mapped to known accounts
        roles = {
            "alice": "Security Administrator",
            "bob": "Lead Gateway Engineer",
            "charlie": "Security Compliance Auditor",
            "admin": "System Administrator",
        }
        role = roles.get(str(username).lower(), "Standard Client")

        return jsonify({
            "message": "Request successful",
            "status": "authenticated",
            "user": username,
            "role": role,
            "token": f"shld_{abs(hash(str(username) + 'token')) % 100000000:08d}",
            "clearance": "LEVEL 4 // CIPHER CLEARANCE" if str(username).lower() in ("alice", "admin") else "LEVEL 2 // STANDARD ACCESS"
        }), 200

    # ------------------------------------------------------------------
    # Activity Logs Endpoint (for inspection & dashboard)
    # ------------------------------------------------------------------
    @app.route("/api/logs", methods=["GET"])
    def get_logs():
        return jsonify({"logs": request_logger.get_recent_logs()}), 200

    @app.route("/api/logs", methods=["DELETE"])
    def clear_logs_route():
        request_logger.clear_logs()
        return jsonify({"message": "Logs cleared successfully"}), 200

    # ------------------------------------------------------------------
    # DeepSeek AI Integration Endpoints
    # ------------------------------------------------------------------
    @app.route("/api/ai/status", methods=["GET"])
    def ai_status_endpoint():
        if not ai_service:
            return jsonify({"status": "unavailable", "message": "AI service not initialized"}), 503
        return jsonify(ai_service.check_status()), 200

    @app.route("/api/ai/chat", methods=["POST"])
    def ai_chat_endpoint():
        """
        Protected AI Gateway endpoint (rate-limited by API Shield).
        Demonstrates rate-limiting live LLM completions using DeepSeek API key.
        """
        if not ai_service:
            return jsonify({"error": "Service unavailable", "message": "AI service not configured"}), 503

        data = request.get_json(silent=True) or {}
        prompt = data.get("prompt") or data.get("message")
        if not prompt or not str(prompt).strip():
            return jsonify({
                "error": "Bad request",
                "message": "Field 'prompt' or 'message' is required in JSON body."
            }), 400

        system_prompt = data.get("system_prompt")
        max_tokens = int(data.get("max_tokens", 250))
        result = ai_service.chat_completion(
            prompt=str(prompt),
            system_prompt=system_prompt,
            max_tokens=max_tokens,
        )

        global_metrics.record_ai(
            model=result.get("model", "deepseek-flash"),
            status="success" if result.get("success") else "error"
        )

        return jsonify({
            "message": "AI completion processed successfully",
            "prompt": prompt,
            "response": result.get("content"),
            "model": result.get("model"),
            "source": result.get("source"),
            "key_used": ai_service.get_masked_key(),
        }), 200

    @app.route("/api/ai/analyze-threat", methods=["POST"])
    def ai_threat_endpoint():
        """
        Analyzes recent logs and abuse violations using DeepSeek intelligence.
        """
        if not ai_service:
            return jsonify({"error": "Service unavailable", "message": "AI service not configured"}), 503

        logs = request_logger.get_recent_logs()
        analysis = ai_service.analyze_traffic_threat(logs)
        return jsonify(analysis), 200

    @app.route("/api/ai/generate-policy", methods=["POST"])
    def ai_generate_policy_endpoint():
        """
        Uses DeepSeek to convert natural language rules into structured rate-limit policies.
        """
        if not ai_service:
            return jsonify({"error": "Service unavailable", "message": "AI service not configured"}), 503

        data = request.get_json(silent=True) or {}
        intent = data.get("intent", "Protect sensitive checkout endpoint from carding attack")

        prompt = (
            f"Based on this security requirement: '{intent}', output a JSON rate limiting policy. "
            f"Requirements: name (lowercase string), endpoint (path starting with /), "
            f"limit (integer > 0), window (seconds integer > 0), algorithm ('fixed_window' or 'sliding_window'), active (true). "
            f"Output ONLY the JSON object, nothing else."
        )
        ai_resp = ai_service.chat_completion(prompt, max_tokens=150)
        content = ai_resp.get("content", "").strip()

        # Try to parse JSON from AI response, fallback to structured defaults
        import re, json as py_json
        policy_dict = None
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            try:
                policy_dict = py_json.loads(json_match.group(0))
            except Exception:
                pass

        if not policy_dict or not isinstance(policy_dict, dict):
            safe_name = re.sub(r'[^a-z0-9_]', '', intent.lower().replace(" ", "_"))[:20] or "custom_policy"
            policy_dict = {
                "name": f"ai_{safe_name}",
                "endpoint": "/api/checkout" if "checkout" in intent.lower() else "/api/sensitive",
                "limit": 5 if "strict" in intent.lower() or "brute" in intent.lower() else 20,
                "window": 300 if "login" in intent.lower() or "brute" in intent.lower() else 60,
                "algorithm": "sliding_window",
                "active": True,
            }

        return jsonify({
            "message": "AI policy generated successfully",
            "policy": policy_dict,
            "raw_ai_output": content,
            "model_used": ai_resp.get("model"),
        }), 200

    # ------------------------------------------------------------------
    # Interactive Web Dashboard & Login Portal
    # ------------------------------------------------------------------
    @app.route("/login", methods=["GET"])
    def login_page():
        policy = policy_manager.get_policy_for_endpoint("/api/login")
        limit = policy.limit if policy else 5
        window = policy.window if policy else 300
        backend = getattr(redis_store, "backend", "redis")
        return render_template("login.html", limit=limit, window=window, backend=backend)

    @app.route("/", methods=["GET"])
    def index():
        policies = policy_manager.list_policies()
        recent_logs = request_logger.get_recent_logs()
        backend = getattr(redis_store, "backend", "redis")
        return render_template("index.html", policies=policies, logs=recent_logs, backend=backend)

    # ------------------------------------------------------------------
    # Global Error Handlers (SRS Section 13)
    # ------------------------------------------------------------------
    @app.errorhandler(404)
    def handle_not_found(e):
        return jsonify({"error": "Not found", "message": "The requested endpoint does not exist."}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        return jsonify({"error": "Method not allowed", "message": "HTTP method not allowed for this route."}), 405

    @app.errorhandler(500)
    def handle_server_error(e):
        return jsonify({"error": "Internal server error", "message": "An unexpected error occurred."}), 500


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>API Shield - Interactive Rate Limiter</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-base: #0b0f19;
      --bg-card: rgba(18, 24, 38, 0.85);
      --bg-card-border: rgba(255, 255, 255, 0.08);
      --accent: #6366f1;
      --accent-glow: rgba(99, 102, 241, 0.25);
      --accent-green: #10b981;
      --accent-red: #ef4444;
      --accent-yellow: #f59e0b;
      --text-main: #f3f4f6;
      --text-muted: #9ca3af;
      --mono: 'JetBrains Mono', monospace;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg-base);
      background-image: radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.12) 0%, transparent 40%),
                        radial-gradient(circle at 90% 80%, rgba(16, 185, 129, 0.08) 0%, transparent 40%);
      color: var(--text-main);
      font-family: 'Outfit', sans-serif;
      min-height: 100vh;
      padding: 2rem 1.5rem;
    }
    .container { max-width: 1200px; margin: 0 auto; }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 2rem;
      border-bottom: 1px solid var(--bg-card-border);
      margin-bottom: 2rem;
    }
    .brand { display: flex; align-items: center; gap: 0.75rem; }
    .shield-badge {
      background: linear-gradient(135deg, #4f46e5, #06b6d4);
      padding: 0.6rem 0.8rem;
      border-radius: 12px;
      font-weight: 700;
      font-size: 1.2rem;
      box-shadow: 0 4px 15px var(--accent-glow);
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.35rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.8rem;
      font-weight: 600;
      background: rgba(16, 185, 129, 0.15);
      color: var(--accent-green);
      border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge.redis-status { font-family: var(--mono); }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2rem; }
    @media (max-width: 860px) { .grid { grid-template-columns: 1fr; } }
    .card {
      background: var(--bg-card);
      border: 1px solid var(--bg-card-border);
      border-radius: 16px;
      padding: 1.5rem;
      backdrop-filter: blur(12px);
      box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    h2 { font-size: 1.25rem; font-weight: 600; margin-bottom: 1rem; color: #fff; }
    .form-group { margin-bottom: 1rem; }
    label { display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.35rem; }
    select, input {
      width: 100%;
      padding: 0.75rem 1rem;
      background: rgba(0, 0, 0, 0.35);
      border: 1px solid var(--bg-card-border);
      border-radius: 8px;
      color: #fff;
      font-family: inherit;
      font-size: 0.95rem;
      outline: none;
      transition: all 0.2s ease;
    }
    select:focus, input:focus { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-glow); }
    .btn-row { display: flex; gap: 0.75rem; margin-top: 1.25rem; }
    button {
      flex: 1;
      padding: 0.8rem 1.2rem;
      border-radius: 8px;
      border: none;
      font-weight: 600;
      font-size: 0.95rem;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-primary {
      background: linear-gradient(135deg, #6366f1, #4f46e5);
      color: white;
      box-shadow: 0 4px 12px var(--accent-glow);
    }
    .btn-primary:hover { transform: translateY(-1px); filter: brightness(1.1); }
    .btn-secondary {
      background: rgba(255,255,255,0.08);
      color: var(--text-main);
      border: 1px solid var(--bg-card-border);
    }
    .btn-secondary:hover { background: rgba(255,255,255,0.15); }
    .console-box {
      background: #060911;
      border: 1px solid var(--bg-card-border);
      border-radius: 8px;
      padding: 1rem;
      font-family: var(--mono);
      font-size: 0.85rem;
      max-height: 280px;
      overflow-y: auto;
      white-space: pre-wrap;
      color: #38bdf8;
    }
    .headers-badge-box { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.75rem; }
    .header-tag {
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.1);
      padding: 0.35rem 0.65rem;
      border-radius: 6px;
      font-family: var(--mono);
      font-size: 0.8rem;
    }
    .table-container { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem; }
    th { padding: 0.75rem 1rem; color: var(--text-muted); border-bottom: 1px solid var(--bg-card-border); }
    td { padding: 0.75rem 1rem; border-bottom: 1px solid rgba(255,255,255,0.04); font-family: var(--mono); font-size: 0.85rem; }
    .status-allowed { color: var(--accent-green); }
    .status-blocked { color: var(--accent-red); font-weight: 700; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <div class="shield-badge">🛡️</div>
        <div>
          <h1>API Shield</h1>
          <p style="font-size: 0.85rem; color: var(--text-muted);">Simple API Rate Limiting System (Flask & Redis)</p>
        </div>
      </div>
      <div>
        <span class="badge redis-status">Backend: {{ backend|upper }}</span>
      </div>
    </header>

    <div class="grid">
      <!-- Tester Box -->
      <div class="card">
        <h2>Live Request Tester</h2>
        <div class="form-group">
          <label>Target Endpoint</label>
          <select id="endpointSelect">
            <option value="/api/products" data-method="GET">GET /api/products (Limit: 5/60s, Fixed)</option>
            <option value="/api/users" data-method="GET">GET /api/users (Limit: 10/60s, Sliding)</option>
            <option value="/api/login" data-method="POST">POST /api/login (Limit: 5/300s, Fixed)</option>
            <option value="/health" data-method="GET">GET /health (Unprotected)</option>
          </select>
        </div>
        <div class="form-group">
          <label>X-API-Key Header (Optional)</label>
          <input type="text" id="apiKeyInput" value="test-client-alpha" placeholder="e.g. dev-user-123">
        </div>
        <div class="btn-row">
          <button class="btn-primary" onclick="sendTestRequest()">Send 1 Request</button>
          <button class="btn-secondary" onclick="sendBurstRequests(6)">Burst 6 Requests</button>
        </div>

        <div style="margin-top: 1.5rem;">
          <div class="headers-badge-box" id="headersBox">
            <span class="header-tag">Status: --</span>
            <span class="header-tag">Limit: --</span>
            <span class="header-tag">Remaining: --</span>
            <span class="header-tag">Retry-After: --</span>
          </div>
          <div class="console-box" id="responseConsole">Click "Send 1 Request" to start testing...</div>
        </div>
      </div>

      <!-- Configured Policies -->
      <div class="card">
        <h2>Active Rate Limit Policies</h2>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Endpoint</th>
                <th>Limit</th>
                <th>Window</th>
                <th>Algorithm</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {% for p in policies %}
              <tr>
                <td><strong>{{ p.name }}</strong></td>
                <td>{{ p.endpoint }}</td>
                <td>{{ p.limit }}</td>
                <td>{{ p.window }}s</td>
                <td>{{ p.algorithm }}</td>
                <td>
                  {% if p.active %}
                  <span style="color: var(--accent-green);">Active</span>
                  {% else %}
                  <span style="color: var(--accent-red);">Inactive</span>
                  {% endif %}
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Activity Log -->
    <div class="card">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
        <h2>Recent Decision Logs</h2>
        <button class="btn-secondary" style="flex:none; padding:0.4rem 0.8rem; font-size:0.8rem;" onclick="refreshLogs()">Refresh Logs</button>
      </div>
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Status</th>
              <th>Client (Masked)</th>
              <th>Endpoint</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody id="logsTableBody">
            {% for log in logs|reverse %}
            <tr>
              <td>
                {% if log.status == 'ALLOWED' %}
                <span class="status-allowed">✓ ALLOWED</span>
                {% else %}
                <span class="status-blocked">✕ BLOCKED (429)</span>
                {% endif %}
              </td>
              <td>{{ log.client }}</td>
              <td>{{ log.endpoint }}</td>
              <td>{{ log.reason }} (Remaining: {{ log.remaining if log.remaining is defined else 0 }})</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    async function sendTestRequest() {
      const select = document.getElementById('endpointSelect');
      const endpoint = select.value;
      const method = select.options[select.selectedIndex].getAttribute('data-method');
      const apiKey = document.getElementById('apiKeyInput').value.trim();
      const consoleBox = document.getElementById('responseConsole');
      const headersBox = document.getElementById('headersBox');

      const headers = { 'Content-Type': 'application/json' };
      if (apiKey) { headers['X-API-Key'] = apiKey; }

      const options = { method, headers };
      if (method === 'POST') {
        options.body = JSON.stringify({ username: 'demo_user' });
      }

      consoleBox.innerText = `Sending ${method} ${endpoint}...`;

      try {
        const res = await fetch(endpoint, options);
        const data = await res.json();
        
        const limit = res.headers.get('X-RateLimit-Limit') || 'N/A';
        const remaining = res.headers.get('X-RateLimit-Remaining') || 'N/A';
        const retryAfter = res.headers.get('Retry-After') || 'N/A';

        headersBox.innerHTML = `
          <span class="header-tag" style="color: ${res.status === 200 ? '#10b981' : '#ef4444'}">HTTP ${res.status}</span>
          <span class="header-tag">Limit: ${limit}</span>
          <span class="header-tag">Remaining: ${remaining}</span>
          <span class="header-tag">Retry-After: ${retryAfter}</span>
        `;

        consoleBox.innerText = JSON.stringify(data, null, 2);
        refreshLogs();
      } catch (err) {
        consoleBox.innerText = 'Error: ' + err.message;
      }
    }

    async function sendBurstRequests(count) {
      for (let i = 0; i < count; i++) {
        await sendTestRequest();
        await new Promise(r => setTimeout(r, 80));
      }
    }

    async function refreshLogs() {
      try {
        const res = await fetch('/api/logs');
        const data = await res.json();
        const tbody = document.getElementById('logsTableBody');
        tbody.innerHTML = '';
        const reversed = (data.logs || []).slice().reverse();
        reversed.forEach(log => {
          const row = document.createElement('tr');
          const isAllowed = log.status === 'ALLOWED';
          row.innerHTML = `
            <td><span class="${isAllowed ? 'status-allowed' : 'status-blocked'}">${isAllowed ? '✓ ALLOWED' : '✕ BLOCKED (429)'}</span></td>
            <td>${log.client}</td>
            <td>${log.endpoint}</td>
            <td>${log.reason || ''} (Remaining: ${log.remaining ?? 0})</td>
          `;
          tbody.appendChild(row);
        });
      } catch (e) {}
    }
  </script>
</body>
</html>
"""
