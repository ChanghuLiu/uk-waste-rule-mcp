from __future__ import annotations

from uk_waste_rule_mcp.analytics import public_usage_summary, record_payment_event


def test_source_attribution_preserves_directory_challenge_without_promoting_customer(monkeypatch, tmp_path):
    monkeypatch.setenv("WASTE_ANALYTICS_DB", str(tmp_path / "usage.db"))

    record_payment_event(
        "waste_rule_preflight",
        "challenge",
        "eip155:8453",
        meta={"source_context": "directory"},
    )

    window = public_usage_summary()["windows"]["24h"]

    assert window["business_funnel"]["actual_paid_tool_challenges"] == 1
    assert window["business_funnel"]["declared_external_paid_tool_challenges"] == 0
    assert window["business_funnel"]["unattributed_paid_tool_challenges"] == 1
    assert window["source_attribution"] == [
        {
            "source_bucket": "directory",
            "event_type": "paid_challenge",
            "count": 1,
            "external_classification": "unknown",
            "owner_test": False,
            "payment_status": "challenged",
        }
    ]


def test_source_attribution_preserves_owner_smoke_separately(monkeypatch, tmp_path):
    monkeypatch.setenv("WASTE_ANALYTICS_DB", str(tmp_path / "usage.db"))

    record_payment_event(
        "waste_rule_preflight",
        "challenge",
        "eip155:8453",
        meta={
            "source_context": "unknown",
            "owner_test_marker": "portfolio_owner_probe_v21",
        },
    )

    window = public_usage_summary()["windows"]["24h"]

    assert window["business_funnel"]["actual_paid_tool_challenges"] == 1
    assert window["business_funnel"]["owned_paid_tool_challenges"] == 1
    assert window["business_funnel"]["declared_external_paid_tool_challenges"] == 0
    assert window["source_attribution"][0]["owner_test"] is True
    assert window["source_attribution"][0]["external_classification"] == "owner_test"


def test_public_source_attribution_contains_no_sensitive_request_fields(monkeypatch, tmp_path):
    monkeypatch.setenv("WASTE_ANALYTICS_DB", str(tmp_path / "usage.db"))

    record_payment_event(
        "waste_rule_preflight",
        "challenge",
        "eip155:8453",
        meta={"source_context": "directory"},
    )

    row = public_usage_summary()["windows"]["24h"]["source_attribution"][0]
    assert set(row) == {
        "source_bucket",
        "event_type",
        "count",
        "external_classification",
        "owner_test",
        "payment_status",
    }
