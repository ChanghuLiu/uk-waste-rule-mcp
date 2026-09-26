"""Privacy-minimal production analytics for RegEvidenceHub Waste."""
from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Mapping
from urllib.parse import parse_qs
from uuid import uuid4

_DEFAULT_DB = "/tmp/uk_waste_rule_usage.db"
_REQUEST_META: ContextVar[dict[str, Any]] = ContextVar("waste_request_meta", default={})
OWNER_ACTORS = {"owned", "owned_ci", "owner", "test", "smoke"}
OWNED_CLIENTS = {"waste-owned-paid-smoke", "github-production-smoke", "payai-production-smoke"}
SOURCE_BUCKETS = {
    "openai","claude","grok","official_registry","glama","smithery","payai","directory",
    "organic","regevidencehub","direct","unknown","mcpindex","mcpso","wellknown","agent402",
}
COMMERCIAL_ATTRIBUTION_EVENTS = {
    "free_business_call",
    "paid_challenge",
    "paid_executed",
    "payment_error",
}
ALIASES = {
    "chatgpt":"openai","chatgpt_app":"openai","openai_chatgpt":"openai",
    "claude_connector":"claude","claude_connectors":"claude","xai_grok":"grok",
    "google":"organic","bing":"organic","search":"organic","seo":"organic",
}

def _db_path() -> Path:
    explicit = os.getenv("WASTE_ANALYTICS_DB", "").strip()
    if explicit:
        return Path(explicit)
    volume = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
    if volume:
        return Path(volume) / "usage.db"
    return Path(_DEFAULT_DB)

def _revision() -> str:
    return (os.getenv("RAILWAY_GIT_COMMIT_SHA") or os.getenv("WASTE_DEPLOY_REV") or "unknown").strip() or "unknown"

def _safe(value: Any, length: int = 96) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return re.sub(r"[^A-Za-z0-9._:/+@-]", "_", value.strip())[:length] or None

def normalize_source(value: Any) -> str:
    candidate = str(value or "").strip().lower()
    candidate = ALIASES.get(candidate, candidate)
    return candidate if candidate in SOURCE_BUCKETS else "unknown"

def source_from_query(query: str | None) -> str:
    if not query:
        return "unknown"
    parsed = parse_qs(query, keep_blank_values=True)
    for key in ("src","source","ref","utm_source","campaign_source"):
        if parsed.get(key):
            return normalize_source(parsed[key][0])
    return "unknown"

def source_from_meta(meta: Mapping[str, Any] | None) -> str:
    meta = meta or {}
    for key in ("source_context","source","ref","utm_source","campaign_source"):
        if key in meta:
            return normalize_source(meta.get(key))
    return "unknown"

def request_id(meta: Mapping[str, Any] | None) -> str:
    meta = meta or {}
    for key in ("commercial/request_id","request_id","requestId","x-request-id"):
        token = _safe(meta.get(key))
        if token:
            return token
    return uuid4().hex

def declared_client(meta: Mapping[str, Any] | None) -> tuple[str | None, str | None]:
    info = (meta or {}).get("io.modelcontextprotocol/clientInfo")
    if not isinstance(info, Mapping):
        return None, None
    return _safe(info.get("name"), 80), _safe(info.get("version"), 32)

def classify(meta: Mapping[str, Any] | None) -> tuple[str, bool]:
    meta = meta or {}
    actor = str(meta.get("mcp-commercial-actor") or meta.get("waste/actor") or "").strip().lower()
    marker = str(meta.get("owner_test_marker") or "").strip().lower()
    client, _ = declared_client(meta)
    if actor in OWNER_ACTORS or marker in {"portfolio_owner_probe_v21","portfolio_ci_probe_v21"} or client in OWNED_CLIENTS:
        return "owner_test", True
    if actor == "declared_external":
        return "confirmed_external", False
    return "unknown", False

@contextmanager
def attribution_context(meta: Mapping[str, Any] | None):
    token = _REQUEST_META.set(dict(meta or {}))
    try:
        yield
    finally:
        _REQUEST_META.reset(token)

def _conn() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE IF NOT EXISTS events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        tool TEXT,
        status TEXT,
        latency_ms REAL,
        source_bucket TEXT NOT NULL DEFAULT 'unknown',
        external_classification TEXT NOT NULL DEFAULT 'unknown',
        owner_test INTEGER NOT NULL DEFAULT 0,
        payment_status TEXT NOT NULL DEFAULT 'not_applicable',
        network TEXT,
        request_id TEXT,
        declared_client_name TEXT,
        declared_client_version TEXT,
        deployment_revision TEXT NOT NULL DEFAULT 'unknown'
    )""")
    conn.commit()
    return conn

def _emit(event_type: str, **fields: Any) -> None:
    safe_fields = {k:v for k,v in fields.items() if k not in {"arguments","payload","scenario"}}
    print("WASTE_ANALYTICS " + json.dumps({"event":event_type,"ts":int(time.time()),**safe_fields}, separators=(",",":"), sort_keys=True), flush=True)

def _insert(
    event_type: str, *, tool: str | None = None, status: str | None = None, latency_ms: float | None = None,
    meta: Mapping[str, Any] | None = None, payment_status: str = "not_applicable", network: str | None = None,
    source_override: str | None = None, classification_override: str | None = None, owner_override: bool | None = None,
) -> None:
    request_meta = dict(_REQUEST_META.get() if meta is None else meta)
    classification, owner = classify(request_meta)
    if classification_override is not None:
        classification = classification_override
    if owner_override is not None:
        owner = owner_override
    client_name, client_version = declared_client(request_meta)
    source = normalize_source(source_override) if source_override is not None else source_from_meta(request_meta)
    rid = request_id(request_meta)
    _emit(event_type, tool=tool, status=status, source_bucket=source, external_classification=classification, owner_test=owner, payment_status=payment_status, network=network, request_id=rid)
    try:
        with _conn() as conn:
            conn.execute(
                """INSERT INTO events(ts,event_type,tool,status,latency_ms,source_bucket,external_classification,owner_test,payment_status,network,request_id,declared_client_name,declared_client_version,deployment_revision)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (int(time.time()),event_type,tool,status,latency_ms,source,classification,int(owner),payment_status,network,rid,client_name,client_version,_revision()),
            )
    except Exception:
        pass

def record_call(tool: str, status: str, latency_ms: float, *, meta: Mapping[str, Any] | None = None, paid: bool = False) -> None:
    _insert("business_tool_call" if paid else "free_business_call", tool=tool, status=status, latency_ms=round(float(latency_ms),2), meta=meta)

def record_discovery(route: str, query: str | None = None, *, owned_probe: bool = False, source: str | None = None) -> None:
    if owned_probe:
        return
    normalized = _safe(str(route).split("?",1)[0],160) or "unknown"
    _insert("discovery_observed", tool=normalized, status="DISCOVERY_OBSERVED", source_override=source or source_from_query(query))

def record_payment_event(tool: str, event: str, network: str | None = None, *, meta: Mapping[str, Any] | None = None) -> None:
    mapping = {
        "challenge":("paid_challenge","challenged","CHALLENGE"),
        "settled":("paid_executed","paid","PAID_EXECUTED"),
        "payment_error":("payment_error","payment_error","PAYMENT_ERROR"),
        "maintenance_block":("maintenance_block","unknown","MAINTENANCE_BLOCK"),
    }
    if event not in mapping:
        raise ValueError(f"Unsupported payment event: {event}")
    event_type, payment_status, status = mapping[event]
    _insert(event_type, tool=tool, status=status, meta=meta, payment_status=payment_status, network=network)

def _window(hours: int) -> dict[str, Any]:
    since = int(time.time()) - hours * 3600
    try:
        with _conn() as conn:
            rows = conn.execute(
                """SELECT event_type,source_bucket,external_classification,owner_test,payment_status,COUNT(*)
                   FROM events WHERE ts>=? GROUP BY event_type,source_bucket,external_classification,owner_test,payment_status""",
                (since,),
            ).fetchall()
            tool_rows = conn.execute(
                "SELECT COALESCE(tool,'unknown'),event_type,COUNT(*) FROM events WHERE ts>=? GROUP BY COALESCE(tool,'unknown'),event_type ORDER BY COUNT(*) DESC",
                (since,),
            ).fetchall()
    except Exception:
        rows, tool_rows = [], []
    totals: Counter[str] = Counter()
    external: Counter[str] = Counter()
    owned: Counter[str] = Counter()
    unattributed: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    source_attribution: list[dict[str, Any]] = []
    for event_type, source, classification, owner, payment_status, count in rows:
        event_type = str(event_type)
        source = normalize_source(source)
        classification = str(classification or "unknown")
        owner_test = bool(owner) or classification == "owner_test"
        count = int(count)
        totals[event_type] += count
        sources[source] += count
        if owner_test:
            owned[event_type] += count
        elif classification == "confirmed_external":
            external[event_type] += count
        else:
            unattributed[event_type] += count
        if event_type in COMMERCIAL_ATTRIBUTION_EVENTS:
            source_attribution.append(
                {
                    "source_bucket": source,
                    "event_type": event_type,
                    "count": count,
                    "external_classification": classification,
                    "owner_test": owner_test,
                    "payment_status": str(payment_status or "not_applicable"),
                }
            )
    return {
        "hours":hours,
        "events":dict(totals),
        "sources":dict(sources),
        "source_attribution":source_attribution,
        "by_tool":[{"tool":t,"event_type":e,"count":int(n)} for t,e,n in tool_rows],
        "business_funnel":{
            "machine_discovery_non_owner_hits":totals.get("discovery_observed",0)-owned.get("discovery_observed",0),
            "actual_paid_tool_challenges":totals.get("paid_challenge",0),
            "owned_paid_tool_challenges":owned.get("paid_challenge",0),
            "declared_external_paid_tool_challenges":external.get("paid_challenge",0),
            "unattributed_paid_tool_challenges":unattributed.get("paid_challenge",0),
            "paid_executions":totals.get("paid_executed",0),
            "owned_paid_executions":owned.get("paid_executed",0),
            "declared_external_paid_executions":external.get("paid_executed",0),
            "unattributed_paid_executions":unattributed.get("paid_executed",0),
            "payment_errors":totals.get("payment_error",0),
        },
    }

def public_usage_summary() -> dict[str, Any]:
    return {
        "schema_version":"waste-commercial-analytics-v1",
        "product_id":"waste",
        "privacy":"aggregate operational telemetry only; scenario payloads are not intentionally persisted",
        "deployment_revision":_revision(),
        "windows":{"24h":_window(24),"7d":_window(24*7)},
    }
