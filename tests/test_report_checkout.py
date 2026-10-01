from __future__ import annotations

import asyncio
import json

import httpx
import pytest


def test_pending_waste_report_store_persists_and_expires(tmp_path):
    from uk_waste_rule_mcp.commercial import PendingWasteReportStore

    path = tmp_path / "reports.json"
    store = PendingWasteReportStore(path, ttl_seconds=300)
    token = store.create(workflow="waste_rule_preflight", payload={"nation": "England"})
    store.attach_checkout(token, "co_paid")
    row = PendingWasteReportStore(path, ttl_seconds=300).get_by_checkout_id("co_paid")
    assert row is not None
    assert row["payload"] == {"nation": "England"}
    assert path.stat().st_mode & 0o777 == 0o600


def test_waste_report_checkout_claim_verify_unpaid_and_recovery(monkeypatch, tmp_path):
    pytest.importorskip("mcp.server")
    from starlette.applications import Starlette
    from uk_waste_rule_mcp import production_bridge as bridge
    from uk_waste_rule_mcp.commercial import PendingWasteReportStore

    class FakeCommercial:
        def __init__(self):
            self.paid = True
            self.recovery = []

        async def create_report_checkout(self, **kwargs):
            self.checkout_args = kwargs
            return {"checkout_id": "co_waste", "stripe_session_id": "cs_test", "checkout_url": "https://checkout.stripe.test/waste", "report_claim_token": "claim-secret"}

        async def claim_report_access(self, *, checkout_id, report_claim_token):
            if not self.paid or checkout_id != "co_waste" or report_claim_token != "claim-secret":
                raise RuntimeError("payment pending or claim invalid")
            return {"report_session": "session-secret"}

        async def verify_report_access(self, *, checkout_id, report_session):
            return self.paid and checkout_id == "co_waste" and report_session == "session-secret"

        async def start_report_recovery(self, *, checkout_id, contact_email):
            self.recovery.append((checkout_id, contact_email))
            return True

    fake = FakeCommercial()
    monkeypatch.setattr(bridge, "COMMERCIAL_CLIENT", fake)
    monkeypatch.setattr(bridge, "REPORT_CHECKOUTS", PendingWasteReportStore(tmp_path / "reports.json"))
    monkeypatch.setattr(bridge, "PUBLIC_ORIGIN", "https://waste.example.test")
    app = Starlette(routes=bridge.build_server()._custom_starlette_routes)

    async def request(method, path, **kwargs):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://waste.example.test") as client:
            return await client.request(method, path, **kwargs)

    async def scenario():
        form = {"workflow": "waste_rule_preflight", "payload": json.dumps({"nation": "England", "role": "receiver", "activities": ["receive_waste"]}), "contact_email": "buyer@example.test"}
        checkout = await request("POST", "/waste-report/checkout", data=form, follow_redirects=False)
        assert checkout.status_code == 303
        assert checkout.headers["location"] == "https://checkout.stripe.test/waste"
        assert "report_claim_" in checkout.headers["set-cookie"]
        assert "claim-secret" not in checkout.headers["location"]
        assert "?" not in fake.checkout_args["success_url"]
        assert fake.checkout_args["contact_email"] == "buyer@example.test"

        # Same checkout claim is denied while Stripe reports no paid order.
        fake.paid = False
        denied = await request("GET", "/waste-report/checkout-success", headers={"cookie": "report_claim_co_waste=claim-secret"})
        assert denied.status_code == 403
        assert "Your England Waste Compliance Report" not in denied.text

        fake.paid = True
        report = await request("GET", "/waste-report/checkout-success", headers={"cookie": "report_claim_co_waste=claim-secret"})
        assert report.status_code == 200
        assert "Your England Waste Compliance Report" in report.text
        assert "report_session_co_waste" in report.headers["set-cookie"]
        assert "claim-secret" not in report.text and "session-secret" not in report.text

        recovered = await request("POST", "/api/v1/report-access/recovery", json={"checkout_id": "co_waste", "contact_email": "buyer@example.test"})
        assert recovered.status_code == 200
        assert "If a paid report matches" in recovered.text
        assert fake.recovery == [("co_waste", "buyer@example.test")]

        wrong_session = await request("POST", "/api/v1/report-access/redeem", json={"checkout_id": "co_waste", "report_session": "another-account-session"})
        assert wrong_session.status_code == 403

    asyncio.run(scenario())
