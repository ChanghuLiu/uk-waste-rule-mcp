from datetime import datetime, timezone

import uk_waste_rule_mcp.monitor as monitor
from uk_waste_rule_mcp.engine import waste_preflight
from uk_waste_rule_mcp.sources import (
    clear_runtime_source_registry,
    set_runtime_source_registry,
    source_registry,
)


def _fresh_records(now_text: str) -> list[dict]:
    records = source_registry()
    return [
        {
            **record,
            "last_checked_at": now_text,
            "last_status": "UNCHANGED",
            "last_error": None,
        }
        for record in records
    ]


def test_refresh_source_registry_publishes_fresh_runtime_state(monkeypatch):
    clear_runtime_source_registry()
    checked_at = "2026-09-30T14:15:00Z"
    fresh = _fresh_records(checked_at)
    monkeypatch.setattr(monitor, "check_all_sources", lambda **_kwargs: fresh)

    try:
        monitor.refresh_source_registry(persist=False)
        health = monitor.source_health(now=datetime(2026, 9, 30, 14, 16, tzinfo=timezone.utc))
        assert health["status"] == "READY"
        assert health["decision_usable"] is True
        assert source_registry()[0]["last_checked_at"] == checked_at
    finally:
        clear_runtime_source_registry()


def test_waste_preflight_consumes_runtime_refresh_instead_of_stale_seed():
    clear_runtime_source_registry()
    checked_at = "2026-09-30T14:15:00Z"
    fresh = _fresh_records(checked_at)
    set_runtime_source_registry(fresh)

    try:
        result = waste_preflight({
            "nation": "England",
            "role": "carrier",
            "activities": ["transport_waste"],
        })
        assert result["source_health"]["decision_usable"] is True
        assert not any(item["code"] == "SOURCE-001" for item in result["findings"])
        assert {item["last_checked_at"] for item in result["evidence"]} == {checked_at}
    finally:
        clear_runtime_source_registry()
