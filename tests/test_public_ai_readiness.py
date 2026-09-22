from __future__ import annotations

import asyncio
import json

import pytest


def _body(response) -> str:
    return response.body.decode("utf-8")


def test_public_ai_mcp_is_payment_free_and_read_only(monkeypatch):
    pytest.importorskip("mcp.server")
    pytest.importorskip("starlette.testclient")
    from starlette.testclient import TestClient

    monkeypatch.setenv("WASTE_PAYMENT_ENFORCED", "1")

    from uk_waste_rule_mcp import public_ai_server

    server = public_ai_server.build_public_ai_server()
    app = server.streamable_http_app(
        json_response=True,
        stateless_http=True,
        host="testserver",
    )

    with TestClient(app) as client:
        listing = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        )
        info = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "waste_rule_info", "arguments": {}},
            },
        )

    assert listing.status_code == 200
    tools = listing.json()["result"]["tools"]
    assert [tool["name"] for tool in tools] == list(public_ai_server.PUBLIC_AI_TOOL_NAMES)
    for tool in tools:
        annotations = tool["annotations"]
        assert annotations["readOnlyHint"] is True
        assert annotations["destructiveHint"] is False
        assert annotations["idempotentHint"] is True
        assert annotations["openWorldHint"] is False
        serialized = json.dumps(tool, sort_keys=True).lower()
        assert "x402" not in serialized
        assert "stripe" not in serialized
        assert "checkout" not in serialized
        assert "$0.02" not in serialized
        assert "$0.03" not in serialized

    assert info.status_code == 200
    assert "none_on_public_ai_surface" in info.text
    assert "x402" not in info.text.lower()
    assert "stripe" not in info.text.lower()
    assert "checkout" not in info.text.lower()


def test_public_ai_mount_aliases_are_stable():
    pytest.importorskip("starlette.routing")
    from starlette.applications import Starlette

    from uk_waste_rule_mcp.production_bridge import safe_mcp_surface_mounts

    app = Starlette()
    mounts = safe_mcp_surface_mounts(app)
    assert [route.path for route in mounts] == ["/openai", "/ai"]


def test_submission_pages_are_public_ai_scoped_and_payment_free(monkeypatch):
    pytest.importorskip("starlette.responses")
    from uk_waste_rule_mcp import submission_pages

    product = asyncio.run(submission_pages.plugin_product_page(None))
    privacy = asyncio.run(submission_pages.privacy_page(None))
    terms = asyncio.run(submission_pages.terms_page(None))
    support = asyncio.run(submission_pages.support_page(None))

    for response in (product, privacy, terms, support):
        assert response.status_code == 200
        assert "RegEvidenceHub Waste" in _body(response)

    assert "payment-free" in _body(product)
    assert "x402 payment flows" in _body(product)
    assert "does not issue Environment Agency decisions" in _body(terms)

    monkeypatch.delenv("OPENAI_APPS_CHALLENGE", raising=False)
    response = asyncio.run(submission_pages.openai_apps_challenge(None))
    assert response.status_code == 404

    monkeypatch.setenv("OPENAI_APPS_CHALLENGE", "waste-openai-domain-proof")
    response = asyncio.run(submission_pages.openai_apps_challenge(None))
    assert response.status_code == 200
    assert _body(response) == "waste-openai-domain-proof"
    assert response.media_type == "text/plain"
