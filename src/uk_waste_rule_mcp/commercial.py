from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

import httpx


class CommercialPlatformError(RuntimeError):
    pass


@dataclass(frozen=True)
class CommercialCheckout:
    checkout_id: str
    stripe_session_id: str
    checkout_url: str


class CommercialPlatformClient:
    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.platform_url = os.getenv("WASTE_COMMERCIAL_PLATFORM_URL", "http://127.0.0.1:8000").strip().rstrip("/")
        self.product_id = os.getenv("WASTE_COMMERCIAL_PRODUCT_ID", "waste").strip()
        self.timeout = float(os.getenv("WASTE_COMMERCIAL_TIMEOUT_SECONDS", "5"))
        self.transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.platform_url, timeout=self.timeout, transport=self.transport)

    async def issue_continuation(self, *, case_ref: str, state_ref: str) -> dict[str, Any]:
        async with self._client() as client:
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

    async def create_checkout(
        self,
        *,
        principal_ref: str,
        source_channel: str,
        external_classification: str,
        owner_test: bool,
        success_url: str,
        cancel_url: str,
        idempotency_key: str,
    ) -> CommercialCheckout:
        payload: dict[str, Any] = {
            "product_id": self.product_id,
            "principal_ref": principal_ref,
            "source_channel": source_channel,
            "external_classification": external_classification,
            "owner_test": owner_test,
            "success_url": success_url,
            "cancel_url": cancel_url,
        }
        async with self._client() as client:
            response = await client.post(
                "/v1/checkout/session",
                json=payload,
                headers={"Idempotency-Key": idempotency_key},
            )
        if response.status_code != 200:
            raise CommercialPlatformError(f"checkout service returned {response.status_code}")
        data = response.json()
        if not isinstance(data, dict):
            raise CommercialPlatformError("checkout service returned invalid response")
        values = [data.get("checkout_id"), data.get("stripe_session_id"), data.get("checkout_url")]
        if not all(isinstance(value, str) and value for value in values):
            raise CommercialPlatformError("checkout service returned incomplete response")
        if not str(data["checkout_url"]).startswith("https://"):
            raise CommercialPlatformError("checkout service returned invalid checkout URL")
        return CommercialCheckout(str(data["checkout_id"]), str(data["stripe_session_id"]), str(data["checkout_url"]))

    async def verify_entitlement(self, *, principal_ref: str) -> dict[str, Any]:
        async with self._client() as client:
            response = await client.post("/v1/entitlements/verify", json={
                "product_id": self.product_id,
                "principal_ref": principal_ref,
            })
        if response.status_code != 200:
            raise CommercialPlatformError(f"entitlement service returned {response.status_code}")
        data = response.json()
        if not isinstance(data, dict):
            raise CommercialPlatformError("entitlement service returned invalid response")
        if data.get("active") is True and not isinstance(data.get("token"), str):
            raise CommercialPlatformError("active entitlement response missing token")
        return data

    async def record_event(
        self,
        *,
        event_type: str,
        source_channel: str,
        external_classification: str,
        owner_test: bool,
    ) -> None:
        async with self._client() as client:
            response = await client.post("/v1/events", json={
                "product_id": self.product_id,
                "event_type": event_type,
                "source_channel": source_channel,
                "commercial_intent": "report",
                "external_classification": external_classification,
                "owner_test": owner_test,
            })
        if response.status_code != 200:
            raise CommercialPlatformError(f"commercial telemetry returned {response.status_code}")
