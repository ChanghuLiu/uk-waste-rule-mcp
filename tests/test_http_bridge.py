import pytest


def test_http_discovery_routes_when_mcp_runtime_is_available(monkeypatch):
    pytest.importorskip("mcp.server")
    pytest.importorskip("starlette.testclient")

    monkeypatch.delenv("WASTE_PAYMENT_ENFORCED", raising=False)
    from starlette.testclient import TestClient

    from uk_waste_rule_mcp.production_bridge import build_server

    with TestClient(build_server().streamable_http_app()) as client:
        for path in ("/health", "/status", "/version", "/metrics", "/robots.txt", "/sitemap.xml", "/llms.txt", "/.well-known/mcp.json", "/.well-known/mcp/server-card.json", "/.well-known/agent-card.json", "/.well-known/x402", "/openapi.json"):
            response = client.get(path)
            assert response.status_code == 200, (path, response.text)
        assert client.get("/status").json()["payment_enforced"] is False


def test_commercial_decision_tools_publish_strict_field_level_schemas(monkeypatch):
    pytest.importorskip("mcp.server")
    pytest.importorskip("starlette.testclient")
    from starlette.testclient import TestClient
    from uk_waste_rule_mcp.production_bridge import build_server

    monkeypatch.delenv("WASTE_PAYMENT_ENFORCED", raising=False)
    with TestClient(build_server().streamable_http_app(json_response=True, stateless_http=True, host="testserver")) as client:
        listing=client.post("/mcp",json={"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}})
    assert listing.status_code==200
    tools={item["name"]:item for item in listing.json()["result"]["tools"]}
    for name in (
        "waste_rule_preflight",
        "waste_carrier_broker_dealer_preflight",
        "waste_digital_tracking_readiness",
        "waste_permit_change_preflight",
    ):
        schema=tools[name]["inputSchema"]
        assert "scenario" in schema["properties"], name
        scenario=schema["properties"]["scenario"]
        assert "$ref" in scenario or "properties" in scenario or "allOf" in scenario, name
        assert "additionalProperties" not in scenario or scenario["additionalProperties"] is not True, name
        assert len(tools[name].get("description","")) >= 180, name
