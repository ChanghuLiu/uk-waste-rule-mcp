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

def test_all_six_reviewed_source_baselines_migrate_only_on_exact_match():
    records = [
        {"id": source_id, "baseline_sha256": update["previous"], "last_status": "CHANGED"}
        for source_id, update in REVIEWED_BASELINE_UPDATES.items()
        if source_id != "govuk-digital-waste-tracking-service"
    ]
    records.append({
        "id": "govuk-digital-waste-tracking-service",
        "baseline_sha256": "unchanged-dwt-baseline",
        "last_status": "UNCHANGED",
    })

    migrated = apply_reviewed_baseline_updates(records)

    assert len([row for row in migrated if row["baseline_sha256"] in {
        REVIEWED_BASELINE_UPDATES[source_id]["reviewed"]
        for source_id in REVIEWED_BASELINE_UPDATES
        if source_id != "govuk-digital-waste-tracking-service"
    }]) == 6
    assert all(row["last_status"] == "CHANGED" for row in migrated[:6])
    assert all(row["baseline_captured_at"] == "2026-11-06T21:55:25Z" for row in migrated[:6])
    assert migrated[-1] == records[-1]


def test_legacy_reviewed_hash_is_an_explicit_migration_match():
    update = REVIEWED_BASELINE_UPDATES["govuk-report-receipt-of-waste"]
    record = {
        "id": "govuk-report-receipt-of-waste",
        "baseline_sha256": update["previous_hashes"][0],
        "last_status": "CHANGED",
    }

    migrated = apply_reviewed_baseline_updates([record])[0]

    assert migrated["baseline_sha256"] == update["reviewed"]
    assert migrated["last_status"] == "CHANGED"
