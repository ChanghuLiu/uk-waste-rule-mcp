"""Official source metadata for the conservative England MVP."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any


_RUNTIME_SOURCES: list[dict[str, Any]] | None = None

# Explicit, reviewed migrations for existing durable registries. A migration only
# applies while the persisted value exactly matches the previously reviewed hash;
# the normal live source check still has to confirm the new hash before a source is
# decision-usable.
REVIEWED_BASELINE_UPDATES: dict[str, dict[str, Any]] = {
    "govuk-environmental-permits": {
        "previous": "e5f5579321598896b0c7c638ac928e7abd8db056774b84996f5a1d6cc284ce40",
        "previous_hashes": ["a1182a899db3dc14c6cc63194288d9645a3226aca5d6f9f0bc2875ba6ccf81c6"],
        "reviewed": "47756da9536d96ac049f110a196299d0fdae43bfa937c77a90b9f74cf02f8558",
        "reviewed_on": "2026-11-06",
        "reviewed_at": "2026-11-06T21:55:25Z",
        "basis": "Reviewed current official guidance on 2026-11-06. The 2026-03-02 update adds links to separate water abstraction/impounding licences; waste operations and mobile plant route to waste-specific permit guidance. No change to this product's conservative permit-routing logic."
    },
    "govuk-waste-exemptions": {
        "previous": "1319fcec7d1463b828898b742fa33ac8e57a27c305650c86e37374a5299961db",
        "previous_hashes": [],
        "reviewed": "7afe2780fd82873feb13bb617570a82936a56fc30ae068b320974f819b8ba7e5",
        "reviewed_on": "2026-11-06",
        "reviewed_at": "2026-11-06T21:55:25Z",
        "basis": "Reviewed current official exemption chooser and 2026-10-21 reform announcement on 2026-11-06. Activity-specific registration, waste-type and quantity limits remain; announced reforms are subject to Parliamentary approval and expected 2027-01-06, with staged withdrawals/transitions. Product does not determine exemption eligibility; a new scenario warning directs users to confirm activity/site status and reform transition."
    },
    "govuk-waste-duty-of-care": {
        "previous": "1e009634e741eca6ae67d5b278c45c023108e7205ce2509c3a7d7c3ff92e2a88",
        "previous_hashes": ["7046a5290b40e8760c383d0804d6ffdaa674c3da3b1010eb0c59b203d34ecd5f"],
        "reviewed": "57949be0f82c145811967844c207105d3113fa4dec183dcebbf047378ef05ac1",
        "reviewed_on": "2026-11-06",
        "reviewed_at": "2026-11-06T21:55:25Z",
        "basis": "Reviewed current official code on 2026-11-06. Scope remains producers, carriers, brokers, keepers, disposers, treaters, importers and controllers in England/Wales, with safe handling and transfer only to authorised businesses. Product only routes roles and controls."
    },
    "govuk-digital-waste-tracking-service": {
        "previous": "d705ffd548a24a5f6ea6f75d5d08e9f084c86b03cac194ef6729f67129f18093",
        "reviewed": "7fde9575a08ae946bd6d3a50e0228b2e0655945cd1b7d779730e2ff8db8fdb7f",
        "reviewed_on": "2026-10-14",
        "basis": "Reviewed the live DEFRA policy paper updated 2026-10-01. It confirms phase 1 applies to permitted/licensed receiving sites from October 2026 in England and Wales (January 2027 in Scotland and Northern Ireland); carriers, brokers and dealers are phase 2 with an October 2027 mandatory date; exemptions and green-list exports are later phases. A spreadsheet alternative is expected to remain available until at least October 2027. The existing England receiving-site rule matches this scope.",
    },
    "govuk-report-receipt-of-waste": {
        "previous": "39a11073ce5bd28038b3592839e66c6fb1d786fd95f50b00a6ae4e99b3bc89b5",
        "previous_hashes": ["2e7849fa8f892fbea4d2cca69b75ffe31ba80f554d298563a735cdb85c6d7cda"],
        "reviewed": "28686156b1b1b7f98a67f1f249b6600808377dca6d02957713ee86dc6e12a095",
        "reviewed_on": "2026-11-06",
        "reviewed_at": "2026-11-06T21:55:25Z",
        "basis": "Reviewed current official guidance on 2026-11-06. Includes permitted receiving organisations, API or prescribed spreadsheet reporting, £26 annual charge per organisation and 2027-01-31 first payment deadline. New production DWT organisation-account confirmation remains required; no change to route determination."
    },
    "govuk-waste-software-providers": {
        "previous": "309f1759f164881807250251a0cf1656e5eca579e68c1da1b9669d6654f7519a",
        "previous_hashes": ["7aed9fdac9dd0f2c1a69bc98ee9f81eb97101458d294ff8ca59917a95b5d97cf"],
        "reviewed": "74714ca7458adbffc891095789711a105a68662454cda3ef0ef9a64f588e5c46",
        "reviewed_on": "2026-11-06",
        "reviewed_at": "2026-11-06T21:55:25Z",
        "basis": "Reviewed current official provider guidance on 2026-11-06. 14 PAT scenarios, provider disclosures, self-certified non-exhaustive listing; customers remain responsible for suitability. Product does not endorse providers or claim compatibility."
    },
    "govuk-waste-environmental-permits": {
        "previous": "ace68eed5d8ec494cbbba6c7514a5e6bab163ac59d5d6b6a9118156fce65f864",
        "previous_hashes": ["67b0fe6fc436f7c6f0a5b9f2a1d477439391355cd18a15c1f646fbf4420881af"],
        "reviewed": "f8a78fd2952ee0df293849efa3b9bc19925fe86b3bf72e143be2a493a3673b68",
        "reviewed_on": "2026-11-06",
        "reviewed_at": "2026-11-06T21:55:25Z",
        "basis": "Reviewed current official waste permits guidance on 2026-11-06. Current distinctions remain RPS, exemption, standard and bespoke permits, including site/mobile plant routes. Product routes to review and does not determine eligibility or conditions."
    },
}


SOURCES: list[dict[str, Any]] = [
    {
        "id": "govuk-cbd-registration",
        "title": "Register or renew as a waste carrier, broker or dealer",
        "url": "https://www.gov.uk/register-renew-waste-carrier-broker-dealer-england",
        "authority": "Environment Agency / GOV.UK",
        "last_checked": "2026-09-24",
    },
    {
        "id": "govuk-waste-environmental-permits",
        "title": "Waste: environmental permits",
        "url": "https://www.gov.uk/guidance/waste-environmental-permits",
        "authority": "Environment Agency / GOV.UK",
        "last_checked": "2026-10-14",
    },
    {
        "id": "govuk-environmental-permits",
        "title": "Check if you need an environmental permit",
        "url": "https://www.gov.uk/guidance/check-if-you-need-an-environmental-permit",
        "authority": "Environment Agency / GOV.UK",
        "last_checked": "2026-10-14",
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
        "last_checked": "2026-10-14",
    },
    {
        "id": "govuk-digital-waste-tracking-service",
        "title": "Digital waste tracking service",
        "url": "https://www.gov.uk/government/publications/digital-waste-tracking-service/digital-waste-tracking-service",
        "authority": "DEFRA / GOV.UK",
        "last_checked": "2026-10-14",
    },
    {
        "id": "govuk-report-receipt-of-waste",
        "title": "Report receipt of waste",
        "url": "https://www.gov.uk/guidance/report-receipt-of-waste",
        "authority": "DEFRA / GOV.UK",
        "last_checked": "2026-10-14",
    },
    {
        "id": "govuk-waste-software-providers",
        "title": "Report receipt of waste: choose a software provider",
        "url": "https://www.gov.uk/government/publications/report-receipt-of-waste-choose-a-software-provider/report-receipt-of-waste-choose-a-software-provider",
        "authority": "DEFRA / GOV.UK",
        "last_checked": "2026-10-14",
    },
]


def _seed_registry_candidates() -> list[Path]:
    module_path = Path(__file__).resolve()
    return [
        module_path.parents[2] / "data" / "source_registry.json",
        Path.cwd() / "data" / "source_registry.json",
        Path(sys.prefix) / "share" / "uk-waste-rule-mcp" / "source_registry.json",
    ]


def source_registry_path() -> Path:
    """Resolve durable registry state and seed a new explicit path fail-safely."""

    override = os.getenv("WASTE_SOURCE_REGISTRY_PATH", "").strip()
    volume = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
    candidates = _seed_registry_candidates()
    target = Path(override).expanduser() if override else (Path(volume) / "source_registry.json" if volume else None)
    if target is not None:
        if not target.is_file():
            seed = next((candidate for candidate in candidates if candidate.is_file()), None)
            if seed is not None and seed.resolve() != target.resolve():
                try:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(seed, target)
                except OSError:
                    # Leave the missing durable path visible to source_registry(),
                    # which then fails closed rather than silently inventing state.
                    pass
        return target

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[-1]


def set_runtime_source_registry(sources: list[dict[str, Any]]) -> None:
    """Publish the latest observed source state for this running process."""

    global _RUNTIME_SOURCES
    _RUNTIME_SOURCES = [dict(source) for source in sources]


def clear_runtime_source_registry() -> None:
    """Clear process-local monitoring state; intended for tests and clean shutdowns."""

    global _RUNTIME_SOURCES
    _RUNTIME_SOURCES = None


def source_registry() -> list[dict[str, Any]]:
    """Return runtime observations when available, otherwise durable reviewed state."""

    if _RUNTIME_SOURCES is not None:
        return [dict(source) for source in _RUNTIME_SOURCES]

    registry_path = source_registry_path()
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
        sources = payload.get("sources", [])
        if isinstance(sources, list) and sources:
            return apply_reviewed_baseline_updates(sources)
    except (OSError, ValueError, TypeError):
        pass
    return [dict(source) for source in SOURCES]


def apply_reviewed_baseline_updates(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply one-time exact-match reviewed baseline migrations to durable state."""
    result: list[dict[str, Any]] = []
    for source in sources:
        updated = dict(source)
        migration = REVIEWED_BASELINE_UPDATES.get(str(updated.get("id", "")))
        if migration and updated.get("baseline_sha256") in {migration["previous"], *migration.get("previous_hashes", [])}:
            updated["baseline_sha256"] = migration["reviewed"]
            updated["last_checked"] = migration["reviewed_on"]
            updated["baseline_captured_at"] = migration.get("reviewed_at")
            updated["review_note"] = migration["basis"]
        result.append(updated)
    return result
