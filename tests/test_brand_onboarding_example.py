"""Offline unit tests for brand onboarding verify.py example."""
import pytest
import httpx
from unittest.mock import patch, MagicMock

import examples.brand_onboarding.verify as verify_mod


def test_verify_missing_key(monkeypatch):
    monkeypatch.delenv("BRAND_API_KEY", raising=False)
    monkeypatch.delenv("NODE_SHARED_TOKEN", raising=False)
    with pytest.raises(SystemExit) as exc:
        verify_mod.verify_product("XA000001", "NMB-P8-128", "store_a")
    assert "environment variable is required" in str(exc.value)


def test_verify_verified_response(monkeypatch):
    monkeypatch.setenv("BRAND_API_KEY", "test-token")
    monkeypatch.setenv("TRUSTLEDGER_API_URL", "http://test-brand:8001")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "verification_id": "ver_mock123",
        "result": "VERIFIED",
        "reason_code": None,
    }
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        res = verify_mod.verify_product("XA000001", "NMB-P8-128", "store_a")
        assert res["result"] == "VERIFIED"
        assert res["verification_id"] == "ver_mock123"
        assert res["reason_code"] is None

        mock_post.assert_called_once_with(
            "http://test-brand:8001/v1/verify",
            json={"serial": "XA000001", "sku": "NMB-P8-128", "store_id": "store_a"},
            headers={"X-Node-Token": "test-token", "Content-Type": "application/json"},
            timeout=10.0,
        )


def test_verify_not_verified_response(monkeypatch):
    monkeypatch.setenv("BRAND_API_KEY", "test-token")
    monkeypatch.setenv("TRUSTLEDGER_API_URL", "http://test-brand:8001")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "verification_id": "ver_mock456",
        "result": "NOT_VERIFIED",
        "reason_code": "NOT_IN_CHANNEL",
    }
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.post", return_value=mock_resp):
        res = verify_mod.verify_product("XA000001", "NMB-P8-128", "store_b")
        assert res["result"] == "NOT_VERIFIED"
        assert res["reason_code"] == "NOT_IN_CHANNEL"
        assert res["verification_id"] == "ver_mock456"
