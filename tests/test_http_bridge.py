import pytest


def test_http_discovery_routes_when_mcp_runtime_is_available(monkeypatch):
    pytest.importorskip("mcp.server")
    pytest.importorskip("starlette.testclient")

    monkeypatch.delenv("WASTE_PAYMENT_ENFORCED", raising=False)
    from starlette.testclient import TestClient

    from uk_waste_rule_mcp.production_bridge import build_server

    with TestClient(build_server().streamable_http_app()) as client:
        for path in ("/health", "/status", "/version", "/.well-known/mcp.json", "/.well-known/x402"):
            response = client.get(path)
            assert response.status_code == 200, (path, response.text)
        assert client.get("/status").json()["payment_enforced"] is False
