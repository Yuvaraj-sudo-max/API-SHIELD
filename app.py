"""
app.py - Flask application entry point for API Shield.
Implements SRS Section 10.1, 16, and 17.
"""

from flask import Flask
from config import Config
from redis_store import RedisStore
from policy import PolicyManager
from limiter import RateLimiter
from blocking import BlockManager
from logging_utils import RequestLogger, setup_logger
from routes import register_routes, create_rate_limiter_middleware


def create_app(config_class=Config, redis_client=None) -> Flask:
    """
    Application factory for API Shield.
    Initializes dependencies, sets up middleware and registers routes.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 1. Setup Logger
    logger = setup_logger(level=app.config.get("LOG_LEVEL", "INFO"))
    request_logger = RequestLogger(logger=logger)

    # 2. Setup Redis Store
    redis_store = RedisStore(
        host=app.config.get("REDIS_HOST", "localhost"),
        port=app.config.get("REDIS_PORT", 6379),
        db=app.config.get("REDIS_DB", 0),
        client=redis_client,
    )

    # 3. Setup Policy Manager
    policies_file = app.config.get("POLICIES_FILE", "policies.json")
    policy_manager = PolicyManager(storage_file=policies_file)

    # 4. Setup Rate Limiter & Block Manager
    rate_limiter = RateLimiter(redis_store=redis_store)
    block_manager = BlockManager(redis_store=redis_store)

    # 4b. Setup AI Service (DeepSeek API Integration)
    from ai_service import AIService
    ai_service = AIService(
        api_key=app.config.get("DEEPSEEK_API_KEY", app.config.get("API_KEY")),
        base_url=app.config.get("DEEPSEEK_BASE_URL"),
        model=app.config.get("DEEPSEEK_MODEL"),
    )

    # 5. Attach shared components to app for testing/access
    app.redis_store = redis_store
    app.policy_manager = policy_manager
    app.rate_limiter = rate_limiter
    app.block_manager = block_manager
    app.request_logger = request_logger
    app.ai_service = ai_service

    # 6. Register Middleware & Routes
    create_rate_limiter_middleware(
        app=app,
        policy_manager=policy_manager,
        rate_limiter=rate_limiter,
        block_manager=block_manager,
        request_logger=request_logger,
    )

    register_routes(
        app=app,
        policy_manager=policy_manager,
        redis_store=redis_store,
        request_logger=request_logger,
        ai_service=ai_service,
    )

    return app


# Default app instance
app = create_app()

if __name__ == "__main__":
    import socket
    host = app.config.get("APP_HOST", "0.0.0.0")
    port = app.config.get("APP_PORT", 5000)
    debug = app.config.get("DEBUG", False)

    local_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    print(f"\n=======================================================")
    print(f"[*] API Shield Server Active")
    print(f"[*] Localhost:       http://127.0.0.1:{port}/")
    print(f"[*] Network / Wi-Fi:  http://{local_ip}:{port}/")
    print(f"[*] Redis Backend:   {app.redis_store.backend}")
    print(f"=======================================================\n")
    app.run(host=host, port=port, debug=debug)
