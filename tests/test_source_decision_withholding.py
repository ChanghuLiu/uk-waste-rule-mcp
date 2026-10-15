from datetime import datetime, timedelta, timezone

import pytest

from uk_waste_rule_mcp import engine
from uk_waste_rule_mcp.sources import clear_runtime_source_registry, set_runtime_source_registry, source_registry


@pytest.fixture
def source_records():
    clear_runtime_source_registry()
    now = datetime.now(timezone.utc)
    records = [{**row, "last_status": "UNCHANGED", "last_checked_at": now.isoformat()}
               for row in source_registry()]
    yield records
    clear_runtime_source_registry()


def block(records, source_id, state):
    if state == "MISSING_SOURCE":
        return [row for row in records if row["id"] != source_id]
    for row in records:
        if row["id"] == source_id:
            if state == "STALE":
                row["last_checked_at"] = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
            else:
                row["last_status"] = state
    return records


@pytest.mark.parametrize("state", ["CHANGED", "FETCH_ERROR", "MISSING_BASELINE", "STALE", "MISSING_SOURCE"])
@pytest.mark.parametrize("authorisation", ["permit", "exemption"])
def test_tracking_withholds_scope_timing_and_requirement(source_records, state, authorisation):
    set_runtime_source_registry(block(source_records, "govuk-digital-waste-tracking-service", state))
    result = engine.digital_waste_tracking_receipt_readiness({
        "nation": "England", "receiving_authorisation": authorisation,
        "receives_controlled_waste": True, "reporting_method_ready": True,
        "as_of_date": "2026-10-04",
    })
    assert result["source_health"]["decision_usable"] is False
    assert result["decision"]["status"] == "REVIEW_REQUIRED"
    assert result["decision"]["phase1_in_scope"] is None
    assert result["decision"]["requirement"] == "REVIEW_REQUIRED"
    assert result["decision"]["mandatory_from"] is None
    assert result["decision"]["reporting_timing"] is None
    assert not any(row["code"] in {"DWT-SCOPE-001", "DWT-SCOPE-002"} for row in result["findings"])


@pytest.mark.parametrize("state", ["CHANGED", "FETCH_ERROR", "MISSING_BASELINE", "STALE", "MISSING_SOURCE"])
def test_registration_withholds_requirement_fee_and_lifecycle(source_records, state):
    set_runtime_source_registry(block(source_records, "govuk-cbd-registration", state))
    result = engine.carrier_broker_dealer_registration_preflight({
        "nation": "England", "role": "carrier", "own_waste_only": False,
        "action": "renew", "existing_registration_tier": "upper",
    })
    assert result["decision"]["status"] == "REVIEW_REQUIRED"
    assert result["decision"]["registration_required"] is None
    assert result["decision"]["fee_route"] == "REVIEW_REQUIRED"
    assert result["decision"]["action"] == "REVIEW_REQUIRED"
    assert result["decision"]["requested_action"] == "renew"
    assert result["current_published_fees_gbp"] is None
    assert not any(row["code"] in {"CBD-REG-001", "CBD-RENEW-001", "CBD-RENEW-002"} for row in result["findings"])


def test_changed_tracking_source_does_not_block_unrelated_registration(source_records):
    set_runtime_source_registry(block(source_records, "govuk-digital-waste-tracking-service", "CHANGED"))
    result = engine.carrier_broker_dealer_registration_preflight({"nation": "England", "role": "broker"})
    assert result["decision"]["status"] == "SCREENING_COMPLETE"
    assert result["decision"]["registration_required"] is True


def test_empty_registry_withholds_source_dependent_decisions():
    set_runtime_source_registry([])
    try:
        result = engine.digital_waste_tracking_receipt_readiness({
            "nation": "England", "receiving_authorisation": "permit",
            "receives_controlled_waste": True, "reporting_method_ready": True,
        })
        assert result["source_health"]["decision_usable"] is False
        assert result["decision"]["requirement"] == "REVIEW_REQUIRED"
    finally:
        clear_runtime_source_registry()
