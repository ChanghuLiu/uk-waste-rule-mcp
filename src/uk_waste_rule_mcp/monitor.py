"""Fingerprint and freshness monitoring for official waste sources."""

from __future__ import annotations

import hashlib
import json
import re
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .sources import source_registry, source_registry_path

DEFAULT_MAX_AGE_HOURS = 48.0
USER_AGENT = "RegEvidenceHub-Waste-Source-Monitor/0.1"


class _VisibleTextParser(HTMLParser):
    """Extract visible HTML text while ignoring presentation and scripts."""

    _ignored = {"script", "style", "noscript", "template", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self._ignored:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._ignored and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


def normalise_visible_text(body: bytes, content_type: str = "") -> str:
    """Return stable visible text for semantic fingerprints."""

    decoded = body.decode("utf-8", errors="replace")
    if "html" in content_type.lower() or re.search(r"<html|<body|<main|<article", decoded, re.I):
        parser = _VisibleTextParser()
        parser.feed(decoded)
        decoded = " ".join(parser.parts)
    return re.sub(r"\s+", " ", decoded).strip()


def semantic_sha256(body: bytes, content_type: str = "") -> str:
    return hashlib.sha256(normalise_visible_text(body, content_type).encode("utf-8")).hexdigest()


def _now_iso(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _age_hours(last_checked_at: str | None, now: datetime) -> float | None:
    if not last_checked_at:
        return None
    try:
        parsed = datetime.fromisoformat(last_checked_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    return round(max(0.0, (now - parsed.astimezone(timezone.utc)).total_seconds() / 3600), 3)


def check_source(source: dict[str, Any], *, timeout: float = 20.0, now: datetime | None = None) -> dict[str, Any]:
    """Fetch one source and compare it with its reviewed baseline."""

    checked_at = _now_iso(now)
    baseline = source.get("baseline_sha256")
    try:
        request = Request(source["url"], headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
            status_code = int(response.status)
            content_type = response.headers.get_content_type()
        observed = semantic_sha256(body, content_type)
        if not baseline:
            status = "MISSING_BASELINE"
        elif observed == baseline:
            status = "UNCHANGED"
        else:
            status = "CHANGED"
        return {
            **source,
            "last_checked_at": checked_at,
            "last_http_status": status_code,
            "last_content_type": content_type,
            "last_observed_sha256": observed,
            "last_status": status,
            "last_error": None,
        }
    except HTTPError as exc:
        return {**source, "last_checked_at": checked_at, "last_http_status": exc.code, "last_status": "FETCH_ERROR", "last_error": f"HTTP {exc.code}"}
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        return {**source, "last_checked_at": checked_at, "last_status": "FETCH_ERROR", "last_error": str(exc)[:300]}


def check_all_sources(*, timeout: float = 20.0, now: datetime | None = None) -> list[dict[str, Any]]:
    sources = source_registry()
    with ThreadPoolExecutor(max_workers=min(4, len(sources))) as executor:
        futures = [executor.submit(check_source, source, timeout=timeout, now=now) for source in sources]
        return [future.result() for future in futures]


def source_health(sources: list[dict[str, Any]] | None = None, *, now: datetime | None = None) -> dict[str, Any]:
    """Summarise whether every decision-bearing source can be used safely."""

    current = now or datetime.now(timezone.utc)
    records = sources if sources is not None else source_registry()
    blocking: list[dict[str, Any]] = []
    output: list[dict[str, Any]] = []
    for source in records:
        max_age = float(source.get("max_age_hours", DEFAULT_MAX_AGE_HOURS))
        age = _age_hours(source.get("last_checked_at"), current)
        last_status = source.get("last_status", "MISSING_BASELINE")
        stale = age is None or age > max_age
        usable = bool(source.get("baseline_sha256")) and last_status == "UNCHANGED" and not stale
        record = {"id": source.get("id"), "last_status": last_status, "age_hours": age, "max_age_hours": max_age, "stale": stale, "decision_usable": usable, "last_error": source.get("last_error")}
        output.append(record)
        if not usable:
            blocking.append(record)
    return {
        "status": "READY" if not blocking else "REVIEW_REQUIRED",
        "source_count": len(output),
        "decision_usable": not blocking,
        "blocking_source_count": len(blocking),
        "blocking_sources": blocking,
        "sources": output,
    }


def establish_baselines(sources: list[dict[str, Any]], *, now: datetime | None = None) -> list[dict[str, Any]]:
    """Convert a successful live fetch into an explicit reviewed baseline."""

    captured_at = _now_iso(now)
    result: list[dict[str, Any]] = []
    for source in sources:
        observed = source.get("last_observed_sha256")
        if not observed:
            result.append(source)
            continue
        updated = dict(source)
        updated["baseline_sha256"] = observed
        updated["baseline_captured_at"] = captured_at
        updated["last_status"] = "UNCHANGED"
        result.append(updated)
    return result


def write_registry(path: str | Path, sources: list[dict[str, Any]]) -> None:
    """Atomically write monitoring records to the checked-in registry."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"product": "UK Waste Rule & Permit Change-Impact MCP", "scope": "England only in the 0.1 MVP", "sources": sources}
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(target)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check official Waste MCP sources without changing reviewed baselines.")
    parser.add_argument("--write", action="store_true", help="Persist observed status and fingerprints; never changes baseline_sha256.")
    parser.add_argument("--establish-baseline", action="store_true", help="Explicitly establish baselines only when every source fetch succeeds.")
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()
    checked = check_all_sources(timeout=args.timeout)
    if args.establish_baseline:
        if any(source.get("last_status") != "UNCHANGED" for source in checked):
            raise SystemExit("Refusing to establish baseline: one or more source fetches did not succeed.")
        checked = establish_baselines(checked)
    if args.write or args.establish_baseline:
        write_registry(source_registry_path(), checked)
    print(json.dumps(source_health(checked), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
