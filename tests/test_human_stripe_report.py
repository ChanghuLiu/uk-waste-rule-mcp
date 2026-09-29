import asyncio

import httpx

from uk_waste_rule_mcp.commercial import CommercialCheckout, CommercialPlatformClient
from uk_waste_rule_mcp.human_report import render_page, validate_form


def _valid_form():
    return {
        "role": "carrier",
        "activity_transport_waste": "true",
        "site_location": "Leeds",
        "waste_types": "mixed controlled waste",
        "hazardous_status": "no",
        "authorisation_status": "permit",
        "facts_complete": "true",
    }


def test_human_report_form_builds_strict_waste_payload():
    payload, errors = validate_form(_valid_form())
    assert errors == []
    assert payload == {
        "nation": "England",
        "role": "carrier",
        "activities": ["transport_waste"],
        "site_location": "Leeds",
        "waste_types": ["mixed controlled waste"],
        "hazardous_status": False,
        "authorisation_status": "permit",
    }


def test_human_report_requires_role_activity_and_fact_confirmation():
    payload, errors = validate_form({})
    assert payload is None
    assert len(errors) == 3


def test_human_report_readiness_hides_full_decision_and_offers_stripe_report():
    payload, _ = validate_form(_valid_form())
    html = render_page(form="<form></form>", payload=payload, src="direct", run_class="owner_test")
    assert "£19.00" in html
    assert "/compliance-report/checkout" in html
    assert "full deterministic evidence-linked waste-rule preflight" in html
    assert '"decision"' not in html


def test_commercial_client_checkout_entitlement_and_event_contracts(monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/v1/checkout/session":
            return httpx.Response(200, json={
                "checkout_id": "checkout_123",
                "stripe_session_id": "cs_test_123",
                "checkout_url": "https://checkout.stripe.test/session",
            })
        if request.url.path == "/v1/entitlements/verify":
            return httpx.Response(200, json={
                "active": True,
                "entitlement_code": "waste_compliance_report",
                "token": "x" * 64,
            })
        if request.url.path == "/v1/events":
            return httpx.Response(200, json={"accepted": True, "event_id": "evt_1"})
        raise AssertionError(request.url.path)

    monkeypatch.setenv("WASTE_COMMERCIAL_PLATFORM_URL", "https://commercial.test")
    client = CommercialPlatformClient(transport=httpx.MockTransport(handler))

    async def run():
        checkout = await client.create_checkout(
            principal_ref="waste_human_wrs_12345678",
            source_channel="direct",
            external_classification="owner_test",
            owner_test=True,
            success_url="https://waste.example/success",
            cancel_url="https://waste.example/cancel",
            idempotency_key="waste-human-test-123",
        )
        assert checkout == CommercialCheckout("checkout_123", "cs_test_123", "https://checkout.stripe.test/session")
        entitlement = await client.verify_entitlement(principal_ref="waste_human_wrs_12345678")
        assert entitlement["active"] is True
        await client.record_event(
            event_type="checkout_started",
            source_channel="direct",
            external_classification="owner_test",
            owner_test=True,
        )

    asyncio.run(run())
    checkout_request = next(item for item in seen if item.url.path == "/v1/checkout/session")
    assert checkout_request.headers["Idempotency-Key"] == "waste-human-test-123"
