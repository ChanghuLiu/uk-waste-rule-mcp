from uk_waste_rule_mcp.sources import REVIEWED_BASELINE_UPDATES, apply_reviewed_baseline_updates


def test_reviewed_baseline_migrations_require_exact_previous_hash_and_do_not_clear_status():
    update = REVIEWED_BASELINE_UPDATES["govuk-report-receipt-of-waste"]
    records = [
        {"id": "govuk-report-receipt-of-waste", "baseline_sha256": update["previous"], "last_status": "CHANGED"},
        {"id": "govuk-digital-waste-tracking-service", "baseline_sha256": "unexpected", "last_status": "CHANGED"},
    ]

    migrated = apply_reviewed_baseline_updates(records)

    assert migrated[0]["baseline_sha256"] == update["reviewed"]
    assert migrated[0]["last_status"] == "CHANGED"
    assert migrated[0]["review_note"] == update["basis"]
    assert migrated[1] == records[1]
