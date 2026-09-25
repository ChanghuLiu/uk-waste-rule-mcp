"""x402-v2 MCP adapter with fail-closed maintenance mode and payment telemetry."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
from typing import Any, Callable

DEFAULT_PUBLIC_MCP_URL = "https://waste.regevidencehub.com/mcp"
BAZAAR_SERVICE_NAME = "RegEvidenceHub Waste"
BAZAAR_TAGS = ["waste","england","permit","carrier","compliance"]
BASE_MAINNET = "eip155:8453"

@dataclass(frozen=True)
class PaidToolSpec:
    name: str
    price: str
    description: str
    input_schema: dict[str, Any]
    example: dict[str, Any] | None = None

def _payment_mode() -> str:
    mode = os.getenv("WASTE_PAYMENT_MODE", "paid").strip().lower()
    if mode not in {"paid","maintenance"}:
        raise RuntimeError("WASTE_PAYMENT_MODE must be 'paid' or 'maintenance'")
    return mode

class MCP2X402Gate:
    def __init__(self) -> None:
        self.network = os.getenv("WASTE_X402_NETWORK", BASE_MAINNET).strip() or BASE_MAINNET
        self.pay_to = os.getenv("WASTE_X402_PAY_TO", "").strip()
        self.facilitator_url = os.getenv("WASTE_X402_FACILITATOR_URL", "").strip()
        self.public_mcp_url = os.getenv("WASTE_PUBLIC_MCP_URL", DEFAULT_PUBLIC_MCP_URL).strip()
        self.mode = _payment_mode()
        self.resource_server = None
        if not self.pay_to:
            raise RuntimeError("WASTE_X402_PAY_TO is required when payment enforcement is enabled")
        if not self.public_mcp_url.startswith("https://"):
            raise RuntimeError("WASTE_PUBLIC_MCP_URL must be an absolute https:// URL")
        if self.mode == "maintenance":
            return
        if not self.facilitator_url:
            raise RuntimeError("WASTE_X402_FACILITATOR_URL is required when payment enforcement is enabled")
        from x402 import x402ResourceServerSync
        from x402.http import FacilitatorConfig, HTTPFacilitatorClientSync
        from x402.mechanisms.evm.exact import ExactEvmServerScheme
        from x402.extensions.bazaar import bazaar_resource_server_extension
        facilitator = HTTPFacilitatorClientSync(FacilitatorConfig(url=self.facilitator_url))
        self.resource_server = x402ResourceServerSync(facilitator)
        self.resource_server.register(self.network, ExactEvmServerScheme())
        self.resource_server.register_extension(bazaar_resource_server_extension)
        self.resource_server.initialize()

    def build(self, spec: PaidToolSpec, execute: Callable[[dict[str, Any]], dict[str, Any]]):
        from x402.mcp import MCPToolResult
        if self.mode == "maintenance":
            def maintenance_handler(_args: dict[str, Any], _ctx: Any) -> MCPToolResult:
                payload = {
                    "status":"PAYMENT_MAINTENANCE","tool":spec.name,
                    "message":"Paid Waste decision execution is temporarily unavailable. No regulatory decision was executed and no payment was requested.",
                }
                return MCPToolResult(content=[{"type":"text","text":json.dumps(payload)}],structured_content=payload,is_error=True)
            return maintenance_handler
        if self.resource_server is None:
            raise RuntimeError("x402 resource server unavailable")
        from x402.extensions.bazaar import DeclareMcpDiscoveryConfig, declare_mcp_discovery_extension
        from x402.mcp import ResourceInfo, SyncPaymentWrapperConfig, create_payment_wrapper_sync
        from x402.schemas import ResourceConfig
        accepts = self.resource_server.build_payment_requirements(ResourceConfig(
            scheme="exact", network=self.network, pay_to=self.pay_to, price=spec.price
        ))
        extensions = declare_mcp_discovery_extension(DeclareMcpDiscoveryConfig(
            tool_name=spec.name, description=spec.description, transport="streamable-http",
            input_schema=spec.input_schema, example=spec.example,
        ))
        wrapper = create_payment_wrapper_sync(self.resource_server, SyncPaymentWrapperConfig(
            accepts=accepts,
            resource=ResourceInfo(
                url=self.public_mcp_url,description=spec.description,mime_type="application/json",
                service_name=BAZAAR_SERVICE_NAME,tags=BAZAAR_TAGS,
            ),
            extensions=extensions,
        ))
        def business_handler(args: dict[str, Any], _tool_ctx: Any) -> MCPToolResult:
            payload=execute(args)
            return MCPToolResult(content=[{"type":"text","text":json.dumps(payload,ensure_ascii=False)}],structured_content=payload,is_error=False)
        return wrapper(business_handler)

    def info(self, prices: dict[str,str]) -> dict[str,Any]:
        return {
            "protocol":"x402-v2","network":self.network,"prices":dict(prices),
            "payment_mode":self.mode,"bazaar_discovery":self.mode=="paid","bazaar_resource":self.public_mcp_url,
        }

def _as_dict(value: Any) -> dict[str,Any]:
    if isinstance(value,dict): return dict(value)
    dump=getattr(value,"model_dump",None)
    if callable(dump):
        try: result=dump(by_alias=True,exclude_none=True)
        except TypeError: result=dump()
        return dict(result) if isinstance(result,dict) else {}
    try: return dict(value)
    except Exception: return {}

def _structured(value: Any) -> dict[str,Any]:
    return _as_dict(value)

def invoke_mcp2_paid_handler(wrapped: Callable[...,Any], *, tool_name: str, arguments: dict[str,Any], ctx: Any):
    from mcp.types import CallToolResult, TextContent
    from .analytics import attribution_context, record_payment_event
    request_context=getattr(ctx,"request_context",None)
    meta=_as_dict(getattr(request_context,"meta",None))
    network=os.getenv("WASTE_X402_NETWORK",BASE_MAINNET).strip() or BASE_MAINNET
    try:
        with attribution_context(meta):
            result=wrapped(arguments,{"toolName":tool_name,"_meta":meta})
    except Exception:
        record_payment_event(tool_name,"payment_error",network,meta=meta)
        raise
    structured=_structured(getattr(result,"structured_content",None))
    is_error=bool(getattr(result,"is_error",False))
    if is_error:
        if structured.get("status")=="PAYMENT_MAINTENANCE":
            record_payment_event(tool_name,"maintenance_block",network,meta=meta)
        elif structured.get("x402Version")==2 and structured.get("accepts"):
            record_payment_event(tool_name,"challenge",network,meta=meta)
        else:
            record_payment_event(tool_name,"payment_error",network,meta=meta)
    else:
        record_payment_event(tool_name,"settled",network,meta=meta)
    content=[
        TextContent(type="text",text=str(block.get("text","")))
        for block in getattr(result,"content",[]) or []
        if isinstance(block,dict) and block.get("type")=="text"
    ]
    if not content: content=[TextContent(type="text",text="")]
    return CallToolResult(
        content=content,structured_content=getattr(result,"structured_content",None),
        is_error=is_error,_meta=getattr(result,"meta",None) or None,
    )
