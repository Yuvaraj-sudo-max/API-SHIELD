import os
from pathlib import Path

# Load .env file
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=env_path, override=True)
    except ImportError:
        # Fallback parser if python-dotenv is not installed
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip("'\"")
                    if k not in os.environ:
                        os.environ[k] = v


class Config:
    """
    Configuration settings for API Shield.
    Values can be overridden by environment variables (SRS Section 16).
    """
    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("APP_PORT", 5000))
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    DEFAULT_LIMIT = int(os.getenv("DEFAULT_LIMIT", 10))
    DEFAULT_WINDOW = int(os.getenv("DEFAULT_WINDOW", 60))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    POLICIES_FILE = os.getenv("POLICIES_FILE", "policies.json")
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")

    # API Keys & AI Integration Configuration
    API_KEY = os.getenv("API_KEY", "sk-fc02e982d5934be9a510598120f2b1df")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", API_KEY)
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
