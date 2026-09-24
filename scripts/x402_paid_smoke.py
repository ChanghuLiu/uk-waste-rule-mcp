#!/usr/bin/env python3
"""One-shot buyer-side Base-mainnet x402 smoke for RegEvidenceHub Waste.

Default mode is challenge-only. Real payment requires --pay and EVM_PRIVATE_KEY
in the local process. The script refuses any unexpected network, asset, amount,
or payee and performs exactly one paid tool call with no retry loop.
"""
from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import os
from types import SimpleNamespace
from typing import Any

from eth_account import Account
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from x402 import x402Client
from x402.mcp import x402MCPClient
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact.register import register_exact_evm_client

ENDPOINT = os.getenv(
    "WASTE_PAID_MCP_URL",
    "https://waste-rule-mcp-production.up.railway.app/mcp",
)
TOOL = "waste_rule_preflight"
NETWORK = "eip155:8453"
SCHEME = "exact"
AMOUNT_ATOMIC = "20000"  # $0.02 USDC, 6 decimals
BASE_USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
EXPECTED_PAY_TO = os.getenv(
    "WASTE_EXPECTED_PAY_TO",
    "0xDAAef0FD525278aAD0bA11066A96c338642A3d1A",
).lower()
ARGS = {
    "scenario": {
        "nation": "England",
        "role": "receiver",
        "activities": ["receive_waste"],
        "site_location": "Owner paid smoke site",
        "waste_types": ["non_hazardous_general"],
        "hazardous_status": False,
        "authorisation_status": "permit",
    }
}


def _dump(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True, exclude_none=True)
    if isinstance(value, dict):
        return {str(k): _dump(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_dump(v) for v in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _validated_requirement(ctx: Any) -> dict[str, Any]:
    payment_required = _dump(ctx.payment_required)
    if int(payment_required.get("x402Version", 0)) != 2:
        raise RuntimeError("Refusing unexpected x402 version")
    accepts = payment_required.get("accepts")
    if not isinstance(accepts, list) or len(accepts) != 1:
        raise RuntimeError("Refusing payment: expected exactly one payment option")
    req = accepts[0]
    checks = {
        "scheme": str(req.get("scheme", "")) == SCHEME,
        "network": str(req.get("network", "")) == NETWORK,
        "amount": str(req.get("amount", "")) == AMOUNT_ATOMIC,
        "asset": str(req.get("asset", "")).lower() == BASE_USDC,
        "payTo": str(req.get("payTo", "")).lower() == EXPECTED_PAY_TO,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        safe = {k: req.get(k) for k in ("scheme", "network", "amount", "asset", "payTo")}
        raise RuntimeError(f"Refusing unexpected payment requirement ({', '.join(failed)}): {safe}")
    return req


class ClientSessionAdapter:
    def __init__(self, session: ClientSession):
        self.session = session

    async def call_tool(self, params: dict[str, Any], **kwargs: Any) -> Any:
        call_kwargs = dict(kwargs)
        meta = params.get("_meta")
        signature = inspect.signature(self.session.call_tool)
        if meta is not None:
            if "meta" in signature.parameters:
                call_kwargs["meta"] = meta
            elif "_meta" in signature.parameters:
                call_kwargs["_meta"] = meta
        raw = await self.session.call_tool(
            str(params["name"]),
            arguments=params.get("arguments") or {},
            **call_kwargs,
        )
        return SimpleNamespace(
            content=getattr(raw, "content", []),
            isError=getattr(raw, "is_error", getattr(raw, "isError", False)),
            _meta=getattr(raw, "meta", getattr(raw, "_meta", {})) or {},
            structuredContent=getattr(raw, "structured_content", getattr(raw, "structuredContent", None)),
        )


async def probe() -> None:
    async with streamable_http_client(ENDPOINT) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            result = await session.call_tool(TOOL, arguments=ARGS)
            dumped = _dump(result)
            structured = dumped.get("structuredContent") or dumped.get("structured_content") or {}
            serialized = json.dumps(structured, default=str)
            if "x402Version" not in serialized or "accepts" not in serialized:
                raise RuntimeError(f"Expected x402 challenge, got: {serialized[:2000]}")
            print("WASTE_X402_CHALLENGE=PASS")
            print(serialized[:4000])


async def pay() -> None:
    key = os.getenv("EVM_PRIVATE_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "EVM_PRIVATE_KEY is not set. Keep it local; never paste it into chat or commit it."
        )
    account = Account.from_key(key)
    payment_client = x402Client().set_spend_controls({"max_amount_per_payment": "$0.02"})
    register_exact_evm_client(payment_client, EthAccountSigner(account), networks=NETWORK)

    approved: dict[str, Any] | None = None

    def approve(ctx: Any) -> bool:
        nonlocal approved
        approved = _validated_requirement(ctx)
        print(json.dumps({
            "payer": account.address,
            "network": approved["network"],
            "amount_atomic": str(approved["amount"]),
            "amount_usdc": "0.02",
            "asset": approved["asset"],
            "payTo": approved["payTo"],
        }, indent=2))
        return True

    async with streamable_http_client(ENDPOINT) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            client = x402MCPClient(
                ClientSessionAdapter(session),
                payment_client,
                auto_payment=True,
                on_payment_requested=approve,
            )
            result = await client.call_tool(TOOL, ARGS)

    payment_response = _dump(getattr(result, "payment_response", None))
    summary = {
        "payment_made": bool(getattr(result, "payment_made", False)),
        "is_error": bool(getattr(result, "is_error", False)),
        "payment_response": payment_response,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if not summary["payment_made"] or summary["is_error"]:
        raise RuntimeError("Paid Waste MCP smoke did not complete successfully")
    if isinstance(payment_response, dict) and payment_response.get("success") is False:
        raise RuntimeError("x402 settlement reported failure")
    print("WASTE_X402_REAL_PAID_BUYER_SMOKE=PASS")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--pay", action="store_true", help="Authorize exactly one real $0.02 Base USDC call")
    modes.add_argument("--probe", action="store_true", help="Challenge only; no signing or payment (default)")
    args = parser.parse_args()
    asyncio.run(pay() if args.pay else probe())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
