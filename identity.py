"""
identity.py - Client identification module for API Shield.
Implements SRS Section 3.1 & Section 11.
"""

def get_client_id(request) -> str:
    """
    Identifies a client following SRS 3.1 rules:
    1. Use the X-API-Key header if present.
    2. Otherwise use the client IP address (request.remote_addr).
    3. Return identity prefix: 'key:<key>' or 'ip:<ip>'.
    """
    api_key = request.headers.get("X-API-Key")
    if api_key and api_key.strip():
        return f"key:{api_key.strip()}"
    
    # Fallback to remote_addr
    remote_addr = request.remote_addr or "127.0.0.1"
    return f"ip:{remote_addr}"


def mask_client_id(client_id: str) -> str:
    """
    Masks client identity for security compliance (SRS Section 12).
    API keys must never be logged in plain text.
    For example: 'key:secret123456' -> 'key:sec***56'
    """
    if not client_id:
        return "unknown"

    if client_id.startswith("key:"):
        key = client_id[4:]
        if len(key) <= 4:
            return "key:***"
        prefix = key[:3]
        suffix = key[-2:] if len(key) > 5 else "*"
        return f"key:{prefix}***{suffix}"

    return client_id


def get_client_tier(request) -> str:
    """
    Resolves client tier: 'free', 'pro', or 'enterprise'.
    1. Checks X-Client-Tier header if provided.
    2. Infers from API key prefix ('ent_', 'pro_').
    3. Defaults to 'free'.
    """
    header_tier = request.headers.get("X-Client-Tier", "").strip().lower()
    if header_tier in ("free", "pro", "enterprise"):
        return header_tier

    api_key = request.headers.get("X-API-Key", "").strip()
    if api_key.startswith("ent_") or api_key.startswith("enterprise_"):
        return "enterprise"
    elif api_key.startswith("pro_"):
        return "pro"

    return "free"


def get_tier_multiplier(tier: str) -> float:
    """
    Returns rate limit quota multiplier for a given client tier.
    - Free: 1.0x (standard policy limit)
    - Pro: 3.0x quota
    - Enterprise: 10.0x quota
    """
    multipliers = {
        "free": 1.0,
        "pro": 3.0,
        "enterprise": 10.0,
    }
    return multipliers.get((tier or "free").lower(), 1.0)

