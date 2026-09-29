from __future__ import annotations
import os
from typing import Any
import httpx

class CommercialPlatformError(RuntimeError):
    pass

class CommercialPlatformClient:
    def __init__(self) -> None:
        self.platform_url = os.getenv("WASTE_COMMERCIAL_PLATFORM_URL", "http://127.0.0.1:8000").strip().rstrip("/")
        self.product_id = os.getenv("WASTE_COMMERCIAL_PRODUCT_ID", "waste").strip()
        self.timeout = float(os.getenv("WASTE_COMMERCIAL_TIMEOUT_SECONDS", "5"))

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
