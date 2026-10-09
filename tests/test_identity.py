"""
tests/test_identity.py - Unit tests for Client Identification and Masking.
Covers SRS Test Cases T-11, T-12, BR-07, and Section 3.1 & 12.
"""

from unittest.mock import MagicMock
from identity import get_client_id, mask_client_id


def test_api_key_identity_preferred():
    """
    T-11 & BR-07: API key identity shall be preferred over IP identity when available.
    """
    mock_request = MagicMock()
    mock_request.headers.get.return_value = "secret_key_123"
    mock_request.remote_addr = "192.168.1.10"

    client_id = get_client_id(mock_request)
    assert client_id == "key:secret_key_123"


def test_ip_fallback_when_api_key_missing():
    """
    T-12: IP is used when API key is absent.
    """
    mock_request = MagicMock()
    mock_request.headers.get.return_value = None
    mock_request.remote_addr = "192.168.1.55"

    client_id = get_client_id(mock_request)
    assert client_id == "ip:192.168.1.55"


def test_ip_fallback_when_api_key_empty():
    """
    IP is used when X-API-Key header is empty or whitespace.
    """
    mock_request = MagicMock()
    mock_request.headers.get.return_value = "   "
    mock_request.remote_addr = "10.0.0.1"

    client_id = get_client_id(mock_request)
    assert client_id == "ip:10.0.0.1"


def test_ip_default_when_remote_addr_none():
    """
    Fallback to default IP '127.0.0.1' if remote_addr is None.
    """
    mock_request = MagicMock()
    mock_request.headers.get.return_value = None
    mock_request.remote_addr = None

    client_id = get_client_id(mock_request)
    assert client_id == "ip:127.0.0.1"


def test_mask_client_id_security():
    """
    SRS Section 12: API keys must not be printed in plain text in application logs.
    """
    # Standard key masking
    masked = mask_client_id("key:secret123456")
    assert "secret123456" not in masked
    assert masked.startswith("key:sec***")

    # Short key masking
    short_masked = mask_client_id("key:abc")
    assert short_masked == "key:***"

    # IP address remains unmasked or intact
    ip_masked = mask_client_id("ip:192.168.1.1")
    assert ip_masked == "ip:192.168.1.1"

    # None or empty
    assert mask_client_id("") == "unknown"
    assert mask_client_id(None) == "unknown"
