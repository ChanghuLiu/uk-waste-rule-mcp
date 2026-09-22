"""Commercial HTTP/MCP bridge for the Waste MVP.

Free discovery remains available without payment.  Decision tools are free in
local mode and x402-gated when ``WASTE_PAYMENT_ENFORCED=1``.
"""

from __future__ import annotations

import os
from typing import Any

from . import __version__
from .engine import PRODUCT, list_waste_rules as catalogue, permit_change_impact as impact, waste_preflight
from .monitor import check_all_sources, source_health
from .sources import source_registry


PRICES = {
    "waste_rule_preflight": "$0.02",
    "permit_change_impact": "$0.03",
}


def payment_enforced() -> bool:
    return os.getenv("WASTE_PAYMENT_ENFORCED", "0").strip() == "1"


def service_info(x402: Any = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "product": PRODUCT,
        "version": __version__,
        "jurisdiction": "England",
        "transport": "streamable-http",
        "decision_tools": list(PRICES),
        "free_discovery_tools": ["waste_rule_info", "list_waste_rules", "waste_source_status", "check_waste_sources", "get_source_registry"],
        "payment_enforced": payment_enforced(),
        "payment_protocol": "x402-v2" if payment_enforced() else None,
        "prices": dict(PRICES),
        "fail_closed": True,
        "source_health": source_health(),
    }
    if x402 is not None:
        result["x402"] = x402.info(PRICES)
    return result


def build_server():
    try:
        from mcp.server import MCPServer
        from mcp.server.mcpserver.context import Context
        from mcp.types import CallToolResult
        from starlette.responses import JSONResponse
    except ImportError as exc:
        raise RuntimeError("Install the MCP extra and the deployment-pinned x402 v2 package separately") from exc

    globals()["Context"] = Context
    globals()["CallToolResult"] = CallToolResult
    server = MCPServer(PRODUCT, instructions="Evidence-linked England waste-rule and permit-change preflight. Decision tools are conservative and fail closed when official source evidence is changed, stale, unavailable or incomplete. This is not a permit, exemption, registration, approval or legal advice.")
    enforced = payment_enforced()
    gate = None
    paid_handlers: dict[str, Any] = {}
    if enforced:
        from .x402_mcp2 import MCP2X402Gate, PaidToolSpec
        gate = MCP2X402Gate()
        schemas = {
            "waste_rule_preflight": {"type": "object", "additionalProperties": True, "description": "England waste facts for conservative rule and authorisation preflight."},
            "permit_change_impact": {"type": "object", "required": ["nation", "current", "proposed"], "additionalProperties": True},
        }
        descriptions = {
            "waste_rule_preflight": "Run an evidence-linked England waste-rule and authorisation preflight.",
            "permit_change_impact": "Screen whether current and proposed waste-operation facts require permit or exemption change review.",
        }
        executors = {"waste_rule_preflight": lambda args: waste_preflight(args), "permit_change_impact": lambda args: impact(args)}
        for name in PRICES:
            paid_handlers[name] = gate.build(PaidToolSpec(name=name, price=os.getenv("WASTE_X402_PRICE_" + name.upper(), PRICES[name]), description=descriptions[name], input_schema=schemas[name]), executors[name])

    @server.custom_route("/status", methods=["GET"], include_in_schema=False)
    async def status(_request):
        return JSONResponse(service_info(gate))

    @server.custom_route("/health", methods=["GET"], include_in_schema=False)
    async def health(_request):
        health_state = source_health()
        return JSONResponse({"status": "ok" if health_state["decision_usable"] else "review_required", "service": PRODUCT, "version": __version__, "source_health": health_state})

    @server.custom_route("/version", methods=["GET"], include_in_schema=False)
    async def version(_request):
        return JSONResponse({"product": PRODUCT, "version": __version__})

    @server.custom_route("/.well-known/mcp.json", methods=["GET"], include_in_schema=False)
    async def mcp_discovery(_request):
        return JSONResponse({"name": "io.github.ChanghuLiu/uk-waste-rule-mcp", "title": PRODUCT, "version": __version__, "transport": "streamable-http", "url": os.getenv("WASTE_PUBLIC_MCP_URL", "") or None, "payment_protocol": "x402-v2" if enforced else None})

    @server.custom_route("/.well-known/x402", methods=["GET"], include_in_schema=False)
    async def x402_discovery(_request):
        return JSONResponse({"payment_enforced": enforced, "protocol": "x402-v2" if enforced else None, "prices": dict(PRICES), "resource": os.getenv("WASTE_PUBLIC_MCP_URL", "") or None})

    @server.tool()
    def waste_rule_info() -> dict[str, Any]:
        """Free service, scope, payment and source-health metadata."""
        return service_info(gate)

    @server.tool()
    def list_waste_rules() -> dict[str, Any]:
        """Free catalogue of modelled waste roles, activities and bounded routes."""
        return catalogue()

    @server.tool()
    def waste_source_status() -> dict[str, Any]:
        """Free persisted source fingerprint and freshness gate."""
        return source_health()

    @server.tool()
    def check_waste_sources() -> dict[str, Any]:
        """Free live check of official sources; does not update baselines."""
        checked = check_all_sources()
        return source_health(checked) | {"checked_sources": checked}

    @server.tool()
    def get_source_registry() -> list[dict[str, Any]]:
        """Free official source registry and monitoring metadata."""
        return source_registry()

    if not enforced:
        @server.tool(name="waste_rule_preflight")
        def waste_rule_preflight(scenario: dict[str, Any]) -> dict[str, Any]:
            """Run the free local/dev version of the conservative waste preflight."""
            return waste_preflight(scenario)

        @server.tool(name="permit_change_impact")
        def permit_change_impact_tool(scenario: dict[str, Any]) -> dict[str, Any]:
            """Run the free local/dev version of permit-change impact screening."""
            return impact(scenario)
    else:
        @server.tool(name="waste_rule_preflight")
        def waste_rule_preflight_paid(scenario: dict[str, Any], ctx: Context) -> CallToolResult:
            return __import__("uk_waste_rule_mcp.x402_mcp2", fromlist=["invoke_mcp2_paid_handler"]).invoke_mcp2_paid_handler(paid_handlers["waste_rule_preflight"], tool_name="waste_rule_preflight", arguments=scenario, ctx=ctx)

        @server.tool(name="permit_change_impact")
        def permit_change_impact_paid(scenario: dict[str, Any], ctx: Context) -> CallToolResult:
            return __import__("uk_waste_rule_mcp.x402_mcp2", fromlist=["invoke_mcp2_paid_handler"]).invoke_mcp2_paid_handler(paid_handlers["permit_change_impact"], tool_name="permit_change_impact", arguments=scenario, ctx=ctx)

    return server


def safe_mcp_surface_mounts(public_ai_app: object) -> list[object]:
    """Mount one isolated payment-free MCP app under vendor-specific aliases."""
    from starlette.routing import Mount

    return [Mount("/openai", app=public_ai_app), Mount("/ai", app=public_ai_app)]


def main() -> None:
    from contextlib import AsyncExitStack, asynccontextmanager

    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route

    from .public_ai_server import build_public_ai_server
    from .submission_pages import (
        openai_apps_challenge,
        plugin_product_page,
        privacy_page,
        support_page,
        terms_page,
    )

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    commercial_server = build_server()
    commercial_app = commercial_server.streamable_http_app(
        host=host,
        json_response=True,
        stateless_http=True,
    )
    public_ai_server = build_public_ai_server()
    public_ai_app = public_ai_server.streamable_http_app(
        host=host,
        json_response=True,
        stateless_http=True,
    )

    @asynccontextmanager
    async def lifespan(_app):
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(commercial_server.session_manager.run())
            await stack.enter_async_context(public_ai_server.session_manager.run())
            yield

    app = Starlette(
        routes=[
            Route("/waste-rule-preflight", endpoint=plugin_product_page, methods=["GET"]),
            Route("/plugin/privacy", endpoint=privacy_page, methods=["GET"]),
            Route("/plugin/terms", endpoint=terms_page, methods=["GET"]),
            Route("/plugin/support", endpoint=support_page, methods=["GET"]),
            Route("/.well-known/openai-apps-challenge", endpoint=openai_apps_challenge, methods=["GET"]),
            *safe_mcp_surface_mounts(public_ai_app),
            Mount("/", app=commercial_app),
        ],
        lifespan=lifespan,
    )
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
