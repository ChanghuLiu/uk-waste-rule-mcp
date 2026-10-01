from __future__ import annotations
import os
import secrets
import httpx
import json
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4


def _absolute_url(name: str, value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.netloc or parts.username or parts.password:
        raise ValueError(f"{name} must be an absolute http(s) URL without credentials")
    return value.rstrip("/") if parts.path in {"", "/"} and not parts.query and not parts.fragment else value

class CommercialPlatformError(RuntimeError):
    pass


class PendingWasteReportStore:
    """Persist short-lived case state locally so checkout/recovery survives restarts."""

    def __init__(self, path: str | Path, ttl_seconds: int = 604800) -> None:
        self.path = Path(path)
        self.ttl_seconds = ttl_seconds
        self._lock = threading.RLock()
        self._rows: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            rows = raw.get("rows", {}) if isinstance(raw, dict) else {}
            if isinstance(rows, dict):
                now = int(time.time())
                self._rows = {key: value for key, value in rows.items()
                              if isinstance(value, dict) and int(value.get("expires_at", 0)) > now}
        except (OSError, ValueError, TypeError):
            self._rows = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(f".{self.path.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps({"version": 1, "rows": self._rows}, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.path)

    def create(self, *, workflow: str, payload: dict[str, Any]) -> str:
        with self._lock:
            token = secrets.token_urlsafe(32)
            self._rows[token] = {"workflow": workflow, "payload": payload, "checkout_id": None, "expires_at": int(time.time()) + self.ttl_seconds}
            self._save()
            return token

    def attach_checkout(self, token: str, checkout_id: str) -> None:
        with self._lock:
            row = self._rows.get(token)
            if row is None:
                raise KeyError("pending report unavailable")
            row["checkout_id"] = checkout_id
            self._save()

    def get_by_checkout_id(self, checkout_id: str) -> dict[str, Any] | None:
        with self._lock:
            now = int(time.time())
            self._rows = {key: value for key, value in self._rows.items() if int(value.get("expires_at", 0)) > now}
            for row in self._rows.values():
                if row.get("checkout_id") == checkout_id:
                    return dict(row)
            self._save()
            return None

    def discard(self, token: str) -> None:
        with self._lock:
            self._rows.pop(token, None)
            self._save()

class CommercialPlatformClient:
    def __init__(self) -> None:
        self.platform_url = _absolute_url("WASTE_COMMERCIAL_PLATFORM_URL", os.getenv("WASTE_COMMERCIAL_PLATFORM_URL", "http://127.0.0.1:8000").strip()).rstrip("/")
        self.product_id = os.getenv("WASTE_COMMERCIAL_PRODUCT_ID", "waste").strip()
        self.timeout = float(os.getenv("WASTE_COMMERCIAL_TIMEOUT_SECONDS", "5"))

    async def create_report_checkout(self, *, contact_email: str, success_url: str, cancel_url: str, source_channel: str = "regevidencehub") -> dict[str, str]:
        async with httpx.AsyncClient(base_url=self.platform_url, timeout=self.timeout) as client:
            response = await client.post("/v1/report-checkout/session", headers={"Idempotency-Key": secrets.token_urlsafe(32)}, json={
                "product_id": self.product_id, "contact_email": contact_email,
                "source_channel": source_channel, "success_url": success_url, "cancel_url": cancel_url,
            })
        if response.status_code != 200:
            raise CommercialPlatformError(f"report checkout service returned {response.status_code}")
        data = response.json()
        keys = ("checkout_id", "stripe_session_id", "checkout_url", "report_claim_token")
        if not isinstance(data, dict) or not all(isinstance(data.get(key), str) and data[key] for key in keys):
            raise CommercialPlatformError("report checkout service returned incomplete checkout")
        if not data["checkout_url"].startswith("https://"):
            raise CommercialPlatformError("report checkout service returned invalid checkout URL")
        return {key: data[key] for key in keys}

    async def claim_report_access(self, *, checkout_id: str, report_claim_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.platform_url, timeout=self.timeout) as client:
            response = await client.post("/v1/report-access/claim", headers={"X-Report-Claim": report_claim_token}, json={"product_id": self.product_id, "checkout_id": checkout_id})
        if response.status_code != 200:
            raise CommercialPlatformError(f"report access claim returned {response.status_code}")
        data = response.json()
        if not isinstance(data, dict) or data.get("active") is not True or not isinstance(data.get("report_session"), str):
            raise CommercialPlatformError("report access claim returned invalid response")
        return data

    async def verify_report_access(self, *, checkout_id: str, report_session: str) -> bool:
        async with httpx.AsyncClient(base_url=self.platform_url, timeout=self.timeout) as client:
            response = await client.post("/v1/report-access/verify", json={"product_id": self.product_id, "checkout_id": checkout_id, "report_session": report_session})
        if response.status_code != 200:
            return False
        data = response.json()
        return data.get("active") is True and data.get("product_id") == self.product_id and data.get("checkout_id") == checkout_id

    async def start_report_recovery(self, *, checkout_id: str, contact_email: str) -> bool:
        async with httpx.AsyncClient(base_url=self.platform_url, timeout=self.timeout) as client:
            response = await client.post("/v1/report-access/recovery/start", json={"checkout_id": checkout_id, "contact_email": contact_email})
        return response.status_code == 200

    async def issue_continuation(self, *, case_ref: str, state_ref: str) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.platform_url, timeout=self.timeout) as client:
            response = await client.post("/v1/continuations/issue", json={
                "product_id": self.product_id,
                "case_ref": case_ref,
                "state_ref": state_ref,
            })
        if response.status_code != 200:
            raise CommercialPlatformError(f"continuation service returned {response.status_code}")
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("continuation_token"), str):
            raise CommercialPlatformError("continuation service returned invalid response")
        return data
