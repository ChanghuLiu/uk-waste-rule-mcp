"""Small x402-v2 adapter for the Waste MCP commercial surface.

The payment gate is constructed only when explicitly enabled.  Business
handlers remain unchanged and therefore retain the source fail-closed gate.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Callable


BAZAAR_SERVICE_NAME = "England Waste Rule Preflight"
BAZAAR_TAGS = ["waste", "environment", "england", "permit", "compliance"]


@dataclass(frozen=True)
class PaidToolSpec:
    name: str
    price: str
    description: str
    input_schema: dict[str, Any]
    example: dict[str, Any] | None = None


class MCP2X402Gate:
    def __init__(self) -> None:
        self.network = os.getenv("WASTE_X402_NETWORK", "").strip()
        self.pay_to = os.getenv("WASTE_X402_PAY_TO", "").strip()
        self.facilitator_url = os.getenv("WASTE_X402_FACILITATOR_URL", "").strip()
        self.public_mcp_url = os.getenv("WASTE_PUBLIC_MCP_URL", "").strip()
        for name, value in (("WASTE_X402_NETWORK", self.network), ("WASTE_X402_PAY_TO", self.pay_to), ("WASTE_X402_FACILITATOR_URL", self.facilitator_url), ("WASTE_PUBLIC_MCP_URL", self.public_mcp_url)):
            if not value:
                raise RuntimeError(f"{name} is required when payment enforcement is enabled")
        if not self.public_mcp_url.startswith("https://"):
            raise RuntimeError("WASTE_PUBLIC_MCP_URL must be an absolute https:// URL")

        from x402 import x402ResourceServerSync
        from x402.http import FacilitatorConfig, HTTPFacilitatorClientSync
        from x402.mechanisms.evm.exact import ExactEvmServerScheme

        facilitator = HTTPFacilitatorClientSync(FacilitatorConfig(url=self.facilitator_url))
        self.resource_server = x402ResourceServerSync(facilitator)
        self.resource_server.register(self.network, ExactEvmServerScheme())
        self.resource_server.initialize()

    def build(self, spec: PaidToolSpec, execute: Callable[[dict[str, Any]], dict[str, Any]]):
        from x402.extensions.bazaar import DeclareMcpDiscoveryConfig, declare_mcp_discovery_extension
        from x402.mcp import MCPToolResult, ResourceInfo, SyncPaymentWrapperConfig, create_payment_wrapper_sync
        from x402.schemas import ResourceConfig

        accepts = self.resource_server.build_payment_requirements(ResourceConfig(scheme="exact", network=self.network, pay_to=self.pay_to, price=spec.price))
        extensions = declare_mcp_discovery_extension(DeclareMcpDiscoveryConfig(tool_name=spec.name, description=spec.description, transport="streamable-http", input_schema=spec.input_schema, example=spec.example))
        wrapper = create_payment_wrapper_sync(self.resource_server, SyncPaymentWrapperConfig(accepts=accepts, resource=ResourceInfo(url=self.public_mcp_url, description=spec.description, mime_type="application/json", service_name=BAZAAR_SERVICE_NAME, tags=BAZAAR_TAGS), extensions=extensions))

        def business_handler(args: dict[str, Any], _tool_ctx: Any) -> MCPToolResult:
            payload = execute(args)
            return MCPToolResult(content=[{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}], structured_content=payload, is_error=False)

        return wrapper(business_handler)

    def info(self, prices: dict[str, str]) -> dict[str, Any]:
        return {"protocol": "x402-v2", "network": self.network, "prices": dict(prices), "bazaar_discovery": True, "bazaar_resource": self.public_mcp_url}


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        try:
            result = dump(by_alias=True, exclude_none=True)
        except TypeError:
            result = dump()
        return dict(result) if isinstance(result, dict) else {}
    try:
        return dict(value)
    except Exception:
        return {}


def invoke_mcp2_paid_handler(wrapped: Callable[..., Any], *, tool_name: str, arguments: dict[str, Any], ctx: Any):
    from mcp.types import CallToolResult, TextContent

    request_context = getattr(ctx, "request_context", None)
    meta = _as_dict(getattr(request_context, "meta", None))
    result = wrapped(arguments, {"toolName": tool_name, "_meta": meta})
    content = [TextContent(type="text", text=str(block.get("text", ""))) for block in getattr(result, "content", []) or [] if isinstance(block, dict) and block.get("type") == "text"]
    if not content:
        content = [TextContent(type="text", text="")]
    return CallToolResult(content=content, structured_content=getattr(result, "structured_content", None), is_error=bool(getattr(result, "is_error", False)), _meta=getattr(result, "meta", None) or None)
