from __future__ import annotations

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from uk_waste_rule_mcp.http_x402 import (
    CARRIER_PATH,
    DWT_PATH,
    PERMIT_PATH,
    RULE_PATH,
    SPECS,
    paid_openapi_paths,
    wrap_http_x402,
)


PAY_TO = "0xDAAef0FD525278aAD0bA11066A96c338642A3d1A"


def test_paid_openapi_paths_declare_all_four_x402_prices(monkeypatch):
    paths = paid_openapi_paths()

    assert paths[RULE_PATH]["post"]["x-payment-info"]["price"]["amount"] == "0.02"
    assert paths[CARRIER_PATH]["post"]["x-payment-info"]["price"]["amount"] == "0.02"
    assert paths[DWT_PATH]["post"]["x-payment-info"]["price"]["amount"] == "0.03"
    assert paths[PERMIT_PATH]["post"]["x-payment-info"]["price"]["amount"] == "0.03"
    for path in (RULE_PATH, CARRIER_PATH, DWT_PATH, PERMIT_PATH):
        assert paths[path]["post"]["x-payment-info"]["protocols"] == [{"x402": {}}]
        assert "402" in paths[path]["post"]["responses"]


def test_unpaid_waste_http_route_stops_at_x402(monkeypatch):
    monkeypatch.setenv("WASTE_PAYMENT_ENFORCED", "1")
    monkeypatch.setenv("WASTE_X402_PAY_TO", PAY_TO)
    monkeypatch.setenv("WASTE_X402_NETWORK", "eip155:8453")
    monkeypatch.setenv("WASTE_X402_FACILITATOR_URL", "https://facilitator.payai.network")

    executed = {"value": False}

    async def endpoint(_request):
        executed["value"] = True
        return JSONResponse({"unexpected": True})

    app = Starlette(routes=[Route(RULE_PATH, endpoint, methods=["POST"])])
    wrapped = wrap_http_x402(app)

    with TestClient(wrapped) as client:
        response = client.post(RULE_PATH, json=SPECS["waste_rule_preflight"]["example"])

    assert response.status_code == 402
    assert executed["value"] is False
    assert response.headers.get("payment-required")


def test_permit_discovery_schema_has_no_local_defs_or_refs():
    schema = SPECS["waste_permit_change_preflight"]["schema"]
    serialized = str(schema)
    assert "$defs" not in serialized
    assert "$ref" not in serialized
