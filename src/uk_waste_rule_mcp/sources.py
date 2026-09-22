"""Official source metadata for the conservative England MVP."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SOURCES: list[dict[str, Any]] = [
    {
        "id": "govuk-environmental-permits",
        "title": "Check if you need an environmental permit",
        "url": "https://www.gov.uk/guidance/check-if-you-need-an-environmental-permit",
        "authority": "Environment Agency / GOV.UK",
        "last_checked": "2026-09-22",
    },
    {
        "id": "govuk-waste-exemptions",
        "title": "Choosing the right waste exemptions for your activity",
        "url": "https://www.gov.uk/government/publications/waste-exemptions-how-to-choose-register-and-pay/choosing-the-right-waste-exemptions-for-your-activity",
        "authority": "Environment Agency / GOV.UK",
        "last_checked": "2026-09-22",
    },
    {
        "id": "govuk-waste-duty-of-care",
        "title": "Waste duty of care: code of practice",
        "url": "https://www.gov.uk/government/publications/waste-duty-of-care-code-of-practice",
        "authority": "DEFRA / GOV.UK",
        "last_checked": "2026-09-22",
    },
    {
        "id": "govuk-digital-waste-tracking-service",
        "title": "Digital waste tracking service",
        "url": "https://www.gov.uk/government/publications/digital-waste-tracking-service/digital-waste-tracking-service",
        "authority": "DEFRA / GOV.UK",
        "last_checked": "2026-09-22",
    },
    {
        "id": "govuk-report-receipt-of-waste",
        "title": "Report receipt of waste",
        "url": "https://www.gov.uk/guidance/report-receipt-of-waste",
        "authority": "DEFRA / GOV.UK",
        "last_checked": "2026-09-22",
    },
    {
        "id": "govuk-waste-software-providers",
        "title": "Report receipt of waste: choose a software provider",
        "url": "https://www.gov.uk/government/publications/report-receipt-of-waste-choose-a-software-provider/report-receipt-of-waste-choose-a-software-provider",
        "authority": "DEFRA / GOV.UK",
        "last_checked": "2026-09-22",
    },
]


def source_registry() -> list[dict[str, Any]]:
    """Return the checked-in registry, including monitoring state when available."""

    registry_path = Path(__file__).resolve().parents[2] / "data" / "source_registry.json"
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
        sources = payload.get("sources", [])
        if isinstance(sources, list) and sources:
            return [dict(source) for source in sources]
    except (OSError, ValueError, TypeError):
        pass
    return [dict(source) for source in SOURCES]
