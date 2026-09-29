import pytest


def test_shared_execution_case_round_trip(monkeypatch, tmp_path):
    pytest.importorskip("mcp.server")
    pytest.importorskip("starlette.testclient")
    from starlette.testclient import TestClient

    from uk_waste_rule_mcp import production_bridge as bridge
    from uk_waste_rule_mcp.case_state import DurableCaseStore

    class FakeCommercial:
        product_id = "waste"
        platform_url = "https://platform.test"

        async def issue_continuation(self, *, case_ref, state_ref):
            assert case_ref.startswith("waste_")
            assert state_ref.startswith("wrs_")
            return {"continuation_token": "opaque-waste-token", "expires_in_seconds": 1800}

    async def verified(token, *, platform_url, expected_product_id):
        assert token == "signed-entitlement"
        assert expected_product_id == "waste"
        return {"entitlement_code": "waste_regulatory_report"}

    monkeypatch.setenv("WASTE_SHARED_EXECUTION_ENABLED", "1")
    monkeypatch.delenv("WASTE_PAYMENT_ENFORCED", raising=False)
    monkeypatch.setattr(bridge, "COMMERCIAL_CLIENT", FakeCommercial())
    monkeypatch.setattr(bridge, "DURABLE_CASES", DurableCaseStore(tmp_path / "runtime"))
    monkeypatch.setattr(bridge, "verify_entitlement_token", verified)

    app = bridge.build_server().streamable_http_app(json_response=True, stateless_http=True, host="testserver")
    with TestClient(app) as client:
        created = client.post("/api/v1/continuation-case", json={
            "action": "waste_case_preflight",
            "workflow": "waste_rule_preflight",
            "payload": {
                "nation": "England",
                "role": "carrier",
                "activities": ["transport_waste"],
                "site_location": "Example depot",
                "waste_types": ["non_hazardous_general"],
                "hazardous_status": False,
            },
            "source_bucket": "chatgpt",
            "classification": "synthetic",
            "owner_test": True,
        })
        assert created.status_code == 200, created.text
        case = created.json()
        assert case["product_id"] == "waste"
        assert case["workflow"] == "waste_rule_preflight"

        wrong = client.post("/api/v1/execute-restored-case", json={
            "contract_version": "reh-execution-v1",
            "product_id": "waste",
            "action": "wrong_action",
            "state_ref": case["state_ref"],
            "entitlement_token": "signed-entitlement",
        })
        assert wrong.status_code == 422

        executed = client.post("/api/v1/execute-restored-case", json={
            "contract_version": "reh-execution-v1",
            "product_id": "waste",
            "action": "waste_case_preflight",
            "state_ref": case["state_ref"],
            "entitlement_token": "signed-entitlement",
        })
        assert executed.status_code == 200, executed.text
        body = executed.json()
        assert body["contract_version"] == "reh-execution-v1"
        assert body["product_id"] == "waste"
        assert body["status"] == "executed"
        assert body["execution_id"].startswith("waste_")
        assert body["result"]["workflow"] == "waste_rule_preflight"
        assert body["result"]["decision"]["product"]
