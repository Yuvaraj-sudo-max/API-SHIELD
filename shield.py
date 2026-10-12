"""
shield.py - Enterprise API Shield Reusable Module & Middleware.
Provides pluggable Flask extension, route decorators, and standalone
programmatic rate-limiting interfaces for any Python application or microservice.
"""

from functools import wraps
from typing import Optional, Callable, Dict, Any, Tuple
from flask import Flask, request, jsonify, g

from redis_store import RedisStore
from policy import PolicyManager, RateLimitRule
from limiter import RateLimiter, LimitResult
from blocking import BlockManager
from identity import get_client_id, get_client_tier, get_tier_multiplier
from logging_utils import RequestLogger, setup_logger


class APIShield:
    """
    Pluggable API Shield Rate Limiting & Threat Defense Extension.
    
    Usage as Flask Extension:
        app = Flask(__name__)
        shield = APIShield(app, redis_host="localhost", redis_port=6379)

        @app.route("/api/orders")
        @shield.limit(limit=10, window=60, algorithm="sliding_window")
        def get_orders():
            return jsonify({"orders": []})

    Usage as Standalone Limiter (FastAPI, Django, Celery, or Scripts):
        shield = APIShield(redis_host="localhost", redis_port=6379)
        result = shield.check_limit(
            client_id="user_123",
            endpoint="/api/orders",
            limit=10,
            window=60,
            algorithm="token_bucket"
        )
        if not result.allowed:
            print(f"Rate limited! Retry after {result.retry_after}s")
    """

    def __init__(
        self,
        app: Optional[Flask] = None,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_client: Optional[Any] = None,
        policies_file: str = "policies.json",
        default_limit: int = 10,
        default_window: int = 60,
        enable_global_middleware: bool = True,
    ):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.default_limit = default_limit
        self.default_window = default_window
        self.enable_global_middleware = enable_global_middleware

        # Initialize core components
        self.store = RedisStore(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            client=redis_client,
        )
        self.policy_manager = PolicyManager(storage_file=policies_file)
        self.limiter = RateLimiter(redis_store=self.store)
        self.block_manager = BlockManager(redis_store=self.store)
        self.logger = setup_logger()
        self.request_logger = RequestLogger(logger=self.logger)

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Binds API Shield to a Flask application instance."""
        app.extensions = getattr(app, "extensions", {})
        app.extensions["api_shield"] = self

        app.redis_store = self.store
        app.policy_manager = self.policy_manager
        app.rate_limiter = self.limiter
        app.block_manager = self.block_manager
        app.request_logger = self.request_logger

        if self.enable_global_middleware:
            from routes import create_rate_limiter_middleware
            create_rate_limiter_middleware(
                app=app,
                policy_manager=self.policy_manager,
                rate_limiter=self.limiter,
                block_manager=self.block_manager,
                request_logger=self.request_logger,
            )

    def limit(
        self,
        limit: int,
        window: int,
        algorithm: str = "fixed_window",
        key_func: Optional[Callable[[], str]] = None,
    ):
        """
        Route-level decorator for granular endpoint rate limiting.
        
        Example:
            @app.route("/checkout")
            @shield.limit(limit=3, window=60, algorithm="token_bucket")
            def checkout():
                return {"status": "paid"}
        """
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                endpoint = request.path
                client_id = key_func() if key_func else get_client_id(request)
                tier = get_client_tier(request)

                multiplier = get_tier_multiplier(tier)
                effective_limit = max(1, int(limit * multiplier))

                rule = RateLimitRule(
                    name=f"route_{endpoint.replace('/', '_')}",
                    endpoint=endpoint,
                    limit=effective_limit,
                    window=window,
                    algorithm=algorithm,
                    active=True,
                )

                # Check if temporarily blocked
                blocked, block_ttl = self.block_manager.is_blocked(client_id)
                if blocked:
                    resp = jsonify({
                        "error": "Rate limit exceeded",
                        "message": "Client temporarily blocked for repeated violations.",
                        "retry_after": block_ttl,
                    })
                    resp.status_code = 429
                    resp.headers["X-RateLimit-Limit"] = str(effective_limit)
                    resp.headers["X-RateLimit-Remaining"] = "0"
                    resp.headers["Retry-After"] = str(block_ttl)
                    resp.headers["X-Client-Tier"] = tier
                    return resp

                res = self.limiter.is_allowed(client_id, endpoint, rule)
                if not res.allowed:
                    _, block_dur = self.block_manager.record_violation(client_id)
                    retry_after = res.retry_after or block_dur
                    resp = jsonify({
                        "error": "Rate limit exceeded",
                        "message": "Please try again later",
                        "retry_after": retry_after,
                    })
                    resp.status_code = 429
                    resp.headers["X-RateLimit-Limit"] = str(effective_limit)
                    resp.headers["X-RateLimit-Remaining"] = "0"
                    resp.headers["Retry-After"] = str(retry_after)
                    resp.headers["X-Client-Tier"] = tier
                    return resp

                # Pass through response and inject headers
                response = f(*args, **kwargs)
                if not hasattr(response, "headers"):
                    response = jsonify(response)
                response.headers["X-RateLimit-Limit"] = str(effective_limit)
                response.headers["X-RateLimit-Remaining"] = str(res.remaining)
                response.headers["X-Client-Tier"] = tier
                return response
            return decorated_function
        return decorator

    def check_limit(
        self,
        client_id: str,
        endpoint: str = "default",
        limit: Optional[int] = None,
        window: Optional[int] = None,
        algorithm: str = "fixed_window",
        tier: str = "free",
    ) -> LimitResult:
        """
        Programmatic check for standalone usage without Flask request context.
        """
        lim = limit if limit is not None else self.default_limit
        win = window if window is not None else self.default_window

        multiplier = get_tier_multiplier(tier)
        effective_limit = max(1, int(lim * multiplier))

        rule = RateLimitRule(
            name=f"manual_{endpoint}",
            endpoint=endpoint,
            limit=effective_limit,
            window=win,
            algorithm=algorithm,
            active=True,
        )

        blocked, block_ttl = self.block_manager.is_blocked(client_id)
        if blocked:
            return LimitResult(
                allowed=False,
                limit=effective_limit,
                remaining=0,
                reset_after=block_ttl,
                retry_after=block_ttl,
                count=effective_limit,
            )

        res = self.limiter.is_allowed(client_id, endpoint, rule)
        if not res.allowed:
            self.block_manager.record_violation(client_id)
        return res

    def is_blocked(self, client_id: str) -> Tuple[bool, int]:
        """Checks if client is temporarily blocked."""
        return self.block_manager.is_blocked(client_id)

    def block_client(self, client_id: str, duration_seconds: int = 300) -> bool:
        """Explicitly blocks client for a duration in seconds."""
        return self.store.block(client_id, duration_seconds)

    def unblock_client(self, client_id: str) -> bool:
        """Unblocks a client immediately and clears violation count."""
        keys = [
            f"block:{client_id}",
            f"violation:{client_id}",
            f"block:key:{client_id}",
            f"violation:key:{client_id}",
            f"block:ip:{client_id}",
            f"violation:ip:{client_id}",
        ]
        return bool(self.store.delete(*keys))

    def get_redis_health(self) -> Dict[str, Any]:
        """Returns live Redis health and server telemetry."""
        return self.store.get_server_info()
