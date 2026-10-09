"""
logging_utils.py - Logging utilities for API Shield.
Implements SRS Section 10.1, 11 (RequestLogger), and 12 (Security: masked API keys).
"""

import logging
import sys
from collections import deque
from typing import List, Dict, Any
from identity import mask_client_id

# Recent activity buffer for inspection/dashboard
_RECENT_LOGS = deque(maxlen=100)


def setup_logger(name: str = "api_shield", level: str = "INFO") -> logging.Logger:
    """Configures application logger."""
    logger = logging.getLogger(name)
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [API-SHIELD] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


class RequestLogger:
    """
    RequestLogger records allowed and blocked request decisions (SRS Section 11 & 12).
    Enforces security requirement that API keys are masked in plain text logs.
    """

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or setup_logger()

    def log_allowed(self, client_id: str, endpoint: str, remaining: int) -> None:
        """
        Records an allowed request decision (SRS Section 5.1 step 14).
        """
        masked_id = mask_client_id(client_id)
        msg = f"ALLOWED | Client: {masked_id} | Endpoint: {endpoint} | Remaining: {remaining}"
        self.logger.info(msg)
        _RECENT_LOGS.append({
            "status": "ALLOWED",
            "client": masked_id,
            "endpoint": endpoint,
            "remaining": remaining,
            "reason": "Within limit"
        })

    def log_blocked(
        self, client_id: str, endpoint: str, reason: str, retry_after: int
    ) -> None:
        """
        Records a blocked request decision (SRS Section 5.1 step 14).
        """
        masked_id = mask_client_id(client_id)
        msg = (
            f"BLOCKED | Client: {masked_id} | Endpoint: {endpoint} | "
            f"Reason: {reason} | Retry-After: {retry_after}s"
        )
        self.logger.warning(msg)
        _RECENT_LOGS.append({
            "status": "BLOCKED",
            "client": masked_id,
            "endpoint": endpoint,
            "reason": reason,
            "retry_after": retry_after
        })

    @staticmethod
    def get_recent_logs() -> List[Dict[str, Any]]:
        """Returns snapshot of recent logged requests for admin inspection."""
        return list(_RECENT_LOGS)

    @staticmethod
    def clear_logs() -> None:
        """Clears recent logged requests."""
        _RECENT_LOGS.clear()
