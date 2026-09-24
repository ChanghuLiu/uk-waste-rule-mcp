from datetime import datetime, timezone
import json

import pytest

from uk_waste_rule_mcp.engine import (carrier_broker_dealer_registration_preflight, classify_waste_route, digital_waste_tracking_receipt_readiness, list_waste_rules, permit_change_impact, waste_preflight)
from uk_waste_rule_mcp.monitor import normalise_visible_text, semantic_sha256, source_health
from uk_waste_rule_mcp.production_bridge import PRICES, service_info
from uk_waste_rule_mcp.sources import source_registry, source_registry_path
from uk_waste_rule_mcp.x402_mcp2 import MCP2X402Gate


def base_scenario(**overrides):
    value = {
        "nation": "England",
        "role": "receiver",
        "activities": ["receive_waste"],
        "site_location": "Example site, England",
        "waste_types": ["non_hazardous_general"],
        "hazardous_status": False,
        "authorisation_status": "permit",
    }
    value.update(overrides)
    return value


def test_receiver_routes_to_permit_and_digital_tracking_review(monkeypatch):
    import uk_waste_rule_mcp.engine as engine
    monkeypatch.setattr(engine, "_source_gate", lambda _ids: {"decision_usable": True})
    result = waste_preflight(base_scenario())
    assert result["decision"]["route"] == "PERMIT_OR_EXEMPTION_AND_DIGITAL_TRACKING_REVIEW"
    assert result["decision"]["status"] == "SCREENING_COMPLETE_REVIEW_REQUIRED"
    assert result["decision"]["deterministic"] is True
    assert "govuk-digital-waste-tracking-service" in {item["id"] for item in result["evidence"]}


def test_missing_authorisation_is_blocking_for_receiver():
    result = waste_preflight(base_scenario(authorisation_status=None))
    codes = {item["code"] for item in result["findings"]}
    assert "AUTH-001" in codes
    assert result["decision"]["status"] == "INCOMPLETE"


def test_unknown_activity_is_never_inferred():
    result = waste_preflight(base_scenario(activities=["special_waste_process"]))
    assert result["decision"]["route"] == "UNKNOWN_ACTIVITY"
    assert any(item["status"] == "unknown" for item in result["findings"])


def test_scotland_is_out_of_scope():
    result = waste_preflight(base_scenario(nation="Scotland"))
    assert result["decision"]["route"] == "OUT_OF_SCOPE"
    assert result["decision"]["status"] == "REVIEW_REQUIRED"


def test_missing_jurisdiction_is_incomplete():
    result = waste_preflight({"role": "receiver", "activities": ["receive_waste"]})
    assert result["decision"]["route"] == "MISSING_NATION"
    assert result["decision"]["status"] == "INCOMPLETE"


def test_missing_role_is_incomplete():
    result = waste_preflight({"nation": "England", "activities": ["receive_waste"]})
    assert result["decision"]["route"] == "MISSING_ROLE"
    assert result["decision"]["status"] == "INCOMPLETE"


def test_carrier_has_duty_of_care_review():
    result = waste_preflight({
        "nation": "England",
        "role": "carrier",
        "activities": ["transport_waste"],
        "site_location": "Example depot",
        "waste_types": ["non_hazardous_general"],
        "hazardous_status": False,
    })
    assert any(item["code"] == "DUTY-001" for item in result["findings"])
    assert result["decision"]["status"] == "REVIEW_REQUIRED"
    assert any(item["code"] == "SOURCE-001" for item in result["findings"])


def test_change_impact_requires_current_and_proposed_facts():
    result = permit_change_impact({"nation": "England"})
    assert result["decision"]["status"] == "INCOMPLETE"
    assert any(item["code"] == "CHANGE-001" for item in result["findings"])


def test_change_impact_routes_changed_quantity_to_review():
    result = permit_change_impact({
        "nation": "England",
        "current": {"site_location": "A", "activities": ["store_waste"], "waste_types": ["wood"], "hazardous_status": False, "maximum_quantity": "10 tonnes"},
        "proposed": {"site_location": "A", "activities": ["store_waste"], "waste_types": ["wood"], "hazardous_status": False, "maximum_quantity": "20 tonnes"},
    })
    assert result["decision"]["status"] == "REVIEW_REQUIRED"
    assert "maximum_quantity" in result["decision"]["changed_fields"]


def test_rule_catalog_is_available_for_discovery():
    result = list_waste_rules()
    ids = {item["id"] for item in result["activities"]}
    assert {"receive_waste", "store_waste", "transport_waste"}.issubset(ids)


def test_classification_requires_activity():
    result = classify_waste_route({"nation": "England", "role": "producer", "activities": []})
    assert result["route"] == "NO_ACTIVITY_IDENTIFIED"


def test_source_health_requires_baseline_and_unchanged_state():
    result = source_health([{"id": "source-a", "baseline_sha256": "abc", "last_status": "CHANGED", "last_checked_at": "2026-09-22T00:00:00Z", "max_age_hours": 48}])
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["decision_usable"] is False
    assert result["blocking_sources"][0]["last_status"] == "CHANGED"


def test_source_health_marks_stale_source_blocking():
    result = source_health([{"id": "source-a", "baseline_sha256": "abc", "last_status": "UNCHANGED", "last_checked_at": "2026-09-19T00:00:00Z", "max_age_hours": 24}], now=datetime(2026, 9, 22, tzinfo=timezone.utc))
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["blocking_sources"][0]["stale"] is True


def test_visible_text_fingerprint_ignores_scripts_and_whitespace():
    left = b"<html><body><p>Permit\n route</p><script>dynamic(1)</script></body></html>"
    right = b"<html><body> Permit route <script>dynamic(2)</script></body></html>"
    assert normalise_visible_text(left, "text/html") == normalise_visible_text(right, "text/html")
    assert semantic_sha256(left, "text/html") == semantic_sha256(right, "text/html")


def test_commercial_bridge_defaults_to_free_discovery_and_fail_closed():
    info = service_info()
    assert info["payment_enforced"] is False
    assert info["payment_protocol"] is None
    assert info["fail_closed"] is True
    assert info["prices"] == PRICES


def test_x402_gate_rejects_missing_configuration_before_importing_provider(monkeypatch):
    for key in ("WASTE_X402_NETWORK", "WASTE_X402_PAY_TO", "WASTE_X402_FACILITATOR_URL", "WASTE_PUBLIC_MCP_URL"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(RuntimeError, match="WASTE_X402_PAY_TO is required"):
        MCP2X402Gate()


def test_source_registry_contains_reviewed_baselines():
    records = source_registry()
    assert len(records) == 8
    reviewed = [record for record in records if record.get("baseline_sha256")]
    pending = [record for record in records if not record.get("baseline_sha256")]
    assert len(reviewed) == 8
    assert pending == []
    software = next(record for record in records if record["id"] == "govuk-waste-software-providers")
    assert software["last_status"] == "CHANGED"
    assert software["decision_critical"] is False


def test_source_registry_path_honours_explicit_override(monkeypatch, tmp_path):
    registry = tmp_path / "source_registry.json"
    registry.write_text(
        json.dumps({
            "sources": [{
                "id": "override-source",
                "baseline_sha256": "abc",
                "last_status": "UNCHANGED",
            }]
        }),
        encoding="utf-8",
    )
    monkeypatch.setenv("WASTE_SOURCE_REGISTRY_PATH", str(registry))
    assert source_registry_path() == registry
    assert source_registry()[0]["id"] == "override-source"


def test_cbd_registration_preflight_requires_carrier_own_waste_fact():
    result = carrier_broker_dealer_registration_preflight({
        "nation": "England", "role": "carrier", "action": "new_registration"
    })
    assert result["decision"]["registration_required"] is True
    assert any(item["code"] == "CBD-FACT-001" for item in result["findings"])


def test_cbd_broker_routes_to_standard_registration_fee_when_source_reviewed(monkeypatch):
    import uk_waste_rule_mcp.engine as engine
    monkeypatch.setattr(engine, "_source_gate", lambda _ids: {"decision_usable": True})
    monkeypatch.setattr(engine, "_source_subset", lambda _ids: [])
    result = engine.carrier_broker_dealer_registration_preflight({
        "nation": "England", "role": "broker", "action": "new_registration"
    })
    assert result["decision"]["status"] == "SCREENING_COMPLETE"
    assert result["decision"]["fee_route"] == "STANDARD_REGISTRATION_FEE_ROUTE"
    assert result["current_published_fees_gbp"]["standard_registration"] == 191.02


def test_dwt_permitted_receiving_site_is_mandatory_from_october_2026(monkeypatch):
    import uk_waste_rule_mcp.engine as engine
    monkeypatch.setattr(engine, "_source_gate", lambda _ids: {"decision_usable": True})
    monkeypatch.setattr(engine, "_source_subset", lambda _ids: [])
    result = engine.digital_waste_tracking_receipt_readiness({
        "nation": "England",
        "receiving_authorisation": "permit",
        "receives_controlled_waste": True,
        "reporting_method_ready": True,
        "as_of_date": "2026-10-01",
    })
    assert result["decision"]["phase1_in_scope"] is True
    assert result["decision"]["requirement"] == "MANDATORY"
    assert result["decision"]["status"] == "SCREENING_COMPLETE"


def test_dwt_exemption_is_not_claimed_as_phase1_mandatory(monkeypatch):
    import uk_waste_rule_mcp.engine as engine
    monkeypatch.setattr(engine, "_source_gate", lambda _ids: {"decision_usable": True})
    monkeypatch.setattr(engine, "_source_subset", lambda _ids: [])
    result = engine.digital_waste_tracking_receipt_readiness({
        "nation": "England",
        "receiving_authorisation": "exemption",
        "receives_controlled_waste": True,
        "as_of_date": "2026-10-01",
    })
    assert result["decision"]["phase1_in_scope"] is False
    assert result["decision"]["requirement"] == "NOT_INCLUDED_IN_PHASE_1_CURRENT_MODEL"


def test_informational_source_drift_does_not_block_global_decision_health():
    from datetime import datetime, timezone
    from uk_waste_rule_mcp.monitor import source_health
    now = datetime(2026, 9, 24, 14, 0, tzinfo=timezone.utc)
    records = [
        {
            "id": "critical",
            "baseline_sha256": "abc",
            "last_status": "UNCHANGED",
            "last_checked_at": "2026-09-24T13:55:00Z",
            "decision_critical": True,
        },
        {
            "id": "informational",
            "baseline_sha256": "old",
            "last_status": "CHANGED",
            "last_checked_at": "2026-09-24T13:55:00Z",
            "decision_critical": False,
        },
    ]
    health = source_health(records, now=now)
    assert health["decision_usable"] is True
    assert health["status"] == "READY_WITH_ADVISORIES"
    assert health["blocking_source_count"] == 0
    assert health["advisory_source_count"] == 1


def test_explicit_source_promotion_updates_only_reviewed_ids():
    from datetime import datetime, timezone
    from uk_waste_rule_mcp.monitor import promote_source_baselines
    records = [
        {"id": "a", "last_http_status": 200, "last_observed_sha256": "new-a", "last_status": "MISSING_BASELINE"},
        {"id": "b", "last_http_status": 200, "last_observed_sha256": "new-b", "last_status": "CHANGED", "baseline_sha256": "old-b"},
    ]
    promoted = promote_source_baselines(records, {"a"}, now=datetime(2026, 9, 24, 14, 0, tzinfo=timezone.utc))
    assert promoted[0]["baseline_sha256"] == "new-a"
    assert promoted[0]["last_status"] == "UNCHANGED"
    assert promoted[1]["baseline_sha256"] == "old-b"
    assert promoted[1]["last_status"] == "CHANGED"
