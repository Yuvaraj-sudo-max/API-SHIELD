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
