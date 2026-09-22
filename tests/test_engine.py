from datetime import datetime, timezone

import pytest

from uk_waste_rule_mcp.engine import classify_waste_route, list_waste_rules, permit_change_impact, waste_preflight
from uk_waste_rule_mcp.monitor import normalise_visible_text, semantic_sha256, source_health
from uk_waste_rule_mcp.production_bridge import PRICES, service_info
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


def test_receiver_routes_to_permit_and_digital_tracking_review():
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
    assert result["decision"]["status"] == "SCREENING_COMPLETE_REVIEW_REQUIRED"


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
    with pytest.raises(RuntimeError, match="WASTE_X402_NETWORK is required"):
        MCP2X402Gate()
