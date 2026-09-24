"""Privacy-minimal machine-discovery attribution for RegEvidenceHub Waste."""
from __future__ import annotations

from collections import Counter
import json
import os
import re
import time
from typing import Any, Awaitable, Callable

from . import analytics

DISCOVERY_SURFACES = {
    "/": "root",
    "/robots.txt": "robots",
    "/sitemap.xml": "sitemap",
    "/llms.txt": "llms",
    "/openapi.json": "openapi",
    "/.well-known/x402": "x402",
    "/.well-known/agent-card.json": "agent_card",
    "/.well-known/agent.json": "agent_json",
    "/agents.json": "agent_json",
    "/.well-known/mcp.json": "mcp_metadata",
    "/.well-known/mcp/server-card.json": "mcp_server_card",
    "/mcp": "commercial_mcp",
    "/openai/mcp": "public_ai_mcp",
    "/ai/mcp": "public_ai_mcp",
}

_SOURCE_RULES: tuple[tuple[str, str, str], ...] = (
    ("smitherybot", "smithery", "indexer"),
    ("smithery", "smithery", "indexer"),
    ("glama", "glama", "indexer"),
    ("modelcontextprotocol", "official_registry", "indexer"),
    ("mcp-registry", "official_registry", "indexer"),
    ("openai", "openai", "agent"),
    ("chatgpt", "openai", "agent"),
    ("anthropic", "claude", "agent"),
    ("claude", "claude", "agent"),
    ("grok", "grok", "agent"),
    ("x.ai", "grok", "agent"),
    ("xai", "grok", "agent"),
    ("payai", "payai", "router"),
    ("agent402", "agent402", "router"),
    ("402explorer", "402explorer", "router"),
    ("mcpbeat", "mcpbeat", "indexer"),
    ("agentindexbot", "agentindex", "indexer"),
    ("mcplookup.com", "mcplookup", "indexer"),
    ("agent-tools.cloud", "agent_tools_cloud", "indexer"),
    ("aive-mcp-endpointprobe", "aive", "indexer"),
    ("sentineloracle", "sentinel_oracle", "indexer"),
    ("mcp-stats-prober", "mcp_stats", "indexer"),
    ("proofbench", "proofbench", "indexer"),
    ("golemreachtrustbot", "golemreach", "indexer"),
    ("mcpscan", "mcpscan", "indexer"),
    ("rokmcp-collector", "rokmcp", "indexer"),
    ("wellknownbot", "wellknown", "indexer"),
    ("oai-searchbot", "openai_search", "search_engine"),
    ("gptbot", "openai_gptbot", "search_engine"),
    ("semrushbot", "semrush", "search_engine"),
    ("mcp-product-console-commercial-funnel", "owner_monitor", "owner_monitor"),
    ("mcp-selection-lab-railway-monitor", "owner_monitor", "owner_monitor"),
)
_MACHINE_TOKENS = ("python-httpx", "undici", "go-http-client", "curl/", "wget/")
_STRONG_SURFACES = {
    "llms", "openapi", "x402", "agent_card", "agent_json", "mcp_metadata",
    "mcp_server_card", "commercial_mcp", "public_ai_mcp",
}
_OWNER_MARKER = "x-mcp-commercial-actor"


def _safe(value: str | None) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", str(value or "unknown_machine").strip().lower())[:40] or "unknown_machine"


def _revision() -> str:
    raw = (os.getenv("RAILWAY_GIT_COMMIT_SHA") or os.getenv("WASTE_DEPLOY_REV") or "unknown").strip()
    return re.sub(r"[^A-Za-z0-9._-]", "_", raw)[:40] or "unknown"


def _headers(scope: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in scope.get("headers") or []:
        try:
            key, value = item
            result[key.decode("latin1").lower()] = value.decode("latin1")
        except Exception:
            continue
    return result


def classify_source(user_agent: str, surface: str) -> tuple[str, str] | None:
    ua = str(user_agent or "").strip().lower()
    for token, family, category in _SOURCE_RULES:
        if token in ua:
            return family, category
    if any(token in ua for token in _MACHINE_TOKENS):
        return "unknown_machine", "unknown_machine"
    if surface in _STRONG_SURFACES:
        return "unknown_machine", "unknown_machine"
    return None


def _conn():
    conn = analytics._conn()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS discovery_observability_v2(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            surface TEXT NOT NULL,
            source_family TEXT NOT NULL,
            source_category TEXT NOT NULL,
            observed_revision TEXT
        )"""
    )
    return conn


def record(surface: str, family: str, category: str) -> None:
    if category == "owner_monitor" or family == "owner_monitor":
        return
    try:
        with _conn() as conn:
            conn.execute(
                "INSERT INTO discovery_observability_v2(ts,surface,source_family,source_category,observed_revision) VALUES(?,?,?,?,?)",
                (int(time.time()), _safe(surface), _safe(family), _safe(category), _revision()),
            )
    except Exception:
        pass


def summary(hours: int) -> dict[str, Any]:
    since = int(time.time()) - hours * 3600
    try:
        with _conn() as conn:
            rows = conn.execute(
                "SELECT ts,surface,source_family,source_category,observed_revision FROM discovery_observability_v2 WHERE ts>=? ORDER BY ts ASC",
                (since,),
            ).fetchall()
    except Exception:
        rows = []

    surfaces = Counter(str(row[1]) for row in rows)
    families = Counter(str(row[2]) for row in rows)
    categories = Counter(str(row[3]) for row in rows)
    current = _revision()
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        family = str(row[2])
        observed = str(row[4] or "unknown")
        latest[family] = {
            "last_seen_at_unix": int(row[0]),
            "observed_revision": observed,
            "current_revision_seen": observed != "unknown" and current != "unknown" and observed == current,
        }
    stale = sorted(
        family for family, row in latest.items()
        if current != "unknown" and not row["current_revision_seen"]
    )
    return {
        "machine_discovery_non_owner_hits": len(rows),
        "machine_discovery_confirmed_external": None,
        "distinct_source_families": len(families),
        "by_surface": dict(sorted(surfaces.items())),
        "by_source_family": dict(sorted(families.items())),
        "by_source_category": dict(sorted(categories.items())),
        "current_revision": current,
        "index_freshness_by_source_family": dict(sorted(latest.items())),
        "source_families_not_seen_on_current_revision": stale,
        "revision_drift_detected": bool(stale),
        "privacy": "bounded labels plus deployment revision only; no IP, raw user-agent, query, payload, signature, wallet or address",
        "interpretation": "Machine discovery activity only; not a customer, buyer-intent, settlement or revenue count.",
    }


def overlay_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    windows = payload.get("windows") if isinstance(payload, dict) else None
    if not isinstance(windows, dict):
        return payload
    for key, hours in (("24h", 24), ("7d", 168)):
        window = windows.get(key)
        if not isinstance(window, dict):
            continue
        discovery = summary(hours)
        window["discovery_observability"] = discovery
        window["machine_discovery_non_owner_hits"] = discovery["machine_discovery_non_owner_hits"]
        window["machine_discovery_by_route"] = discovery["by_surface"]
        window["machine_discovery_by_source_family"] = discovery["by_source_family"]
        window["machine_discovery_by_source_category"] = discovery["by_source_category"]
        window["machine_discovery_distinct_source_families"] = discovery["distinct_source_families"]
        window["machine_discovery_current_revision"] = discovery["current_revision"]
        window["machine_discovery_index_freshness_by_source_family"] = discovery["index_freshness_by_source_family"]
        window["machine_discovery_source_families_not_seen_on_current_revision"] = discovery["source_families_not_seen_on_current_revision"]
        window["machine_discovery_revision_drift_detected"] = discovery["revision_drift_detected"]
        funnel = window.get("business_funnel")
        if isinstance(funnel, dict):
            funnel["machine_discovery_non_owner_hits"] = discovery["machine_discovery_non_owner_hits"]
            funnel["machine_discovery_confirmed_external"] = None
    payload["discovery_observability_version"] = "3.0"
    return payload


class DiscoveryObservabilityASGI:
    def __init__(self, app: Callable[..., Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        path = str(scope.get("path") or "").split("?", 1)[0] if scope.get("type") == "http" else ""
        if scope.get("type") == "http" and path in DISCOVERY_SURFACES:
            surface = DISCOVERY_SURFACES[path]
            method = str(scope.get("method") or "GET").upper()
            headers = _headers(scope)
            owner = str(headers.get(_OWNER_MARKER, "")).strip().lower() in {"owned", "owned_ci", "owner", "test", "smoke"}
            classified = classify_source(headers.get("user-agent", ""), surface)
            if classified and not owner and classified[1] != "owner_monitor":
                if path not in {"/mcp", "/openai/mcp", "/ai/mcp"} or method in {"GET", "HEAD"} or classified[0] != "unknown_machine":
                    record(surface, classified[0], classified[1])

        if scope.get("type") != "http" or path != "/metrics":
            await self.app(scope, receive, send)
            return

        start_message = None
        body_parts: list[bytes] = []

        async def capture(message):
            nonlocal start_message
            if message.get("type") == "http.response.start":
                start_message = message
                return
            if message.get("type") == "http.response.body":
                body_parts.append(message.get("body", b""))
                if message.get("more_body"):
                    return
                body = b"".join(body_parts)
                try:
                    payload = json.loads(body.decode("utf-8"))
                    if isinstance(payload, dict):
                        body = json.dumps(overlay_metrics(payload), separators=(",", ":"), sort_keys=True).encode("utf-8")
                except Exception:
                    pass
                start = dict(start_message or {"type": "http.response.start", "status": 200, "headers": []})
                headers = [(k, v) for k, v in start.get("headers", []) if k.lower() != b"content-length"]
                headers.append((b"content-length", str(len(body)).encode("ascii")))
                start["headers"] = headers
                await send(start)
                await send({"type": "http.response.body", "body": body, "more_body": False})
                return
            await send(message)

        await self.app(scope, receive, capture)
