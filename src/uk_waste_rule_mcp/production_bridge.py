"""Production HTTP/MCP surface for RegEvidenceHub Waste."""
from __future__ import annotations

import json
import os
import time
from typing import Any

from . import __version__
from .analytics import public_usage_summary, record_call, record_discovery
from .engine import (
    PRODUCT,
    carrier_broker_dealer_registration_preflight,
    digital_waste_tracking_receipt_readiness,
    list_waste_rules as catalogue,
    permit_change_impact as impact,
    waste_preflight,
)
from .monitor import check_all_sources, source_health
from .sources import source_registry

PUBLIC_ORIGIN = os.getenv("WASTE_PUBLIC_ORIGIN", "https://waste.regevidencehub.com").strip().rstrip("/")
MCP_URL = os.getenv("WASTE_PUBLIC_MCP_URL", f"{PUBLIC_ORIGIN}/mcp").strip()
REGISTRY_NAME = "io.github.ChanghuLiu/uk-waste-rule-mcp"
BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

PRICES = {
    "waste_rule_preflight": "$0.02",
    "carrier_broker_dealer_registration_preflight": "$0.02",
    "digital_waste_tracking_receipt_readiness": "$0.03",
    "permit_change_impact": "$0.03",
}
TOOL_TITLES = {
    "waste_rule_info": "Waste regulatory service information",
    "list_waste_rules": "Supported waste regulatory routes",
    "waste_source_status": "Waste official-source status",
    "check_waste_sources": "Live waste source audit",
    "get_source_registry": "Waste official-source registry",
    "waste_rule_preflight": "England waste-rule preflight",
    "carrier_broker_dealer_registration_preflight": "Waste carrier/broker/dealer registration preflight",
    "digital_waste_tracking_receipt_readiness": "Digital Waste Tracking receipt readiness",
    "permit_change_impact": "Waste permit change-impact preflight",
}
TOOL_DESCRIPTIONS = {
    "waste_rule_info": "Free discovery. Returns scope, pricing, payment mode, evidence health and supported workflows; it makes no regulatory decision.",
    "list_waste_rules": "Free discovery. Lists the bounded England waste roles, activities and routes modelled by this service.",
    "waste_source_status": "Free evidence-health check. Returns persisted official-source freshness and fail-closed status without changing baselines.",
    "check_waste_sources": "Free live evidence audit. Fetches monitored official sources and compares fingerprints without accepting or mutating reviewed baselines.",
    "get_source_registry": "Free evidence catalogue. Returns monitored official-source metadata and reviewed baseline state.",
    "waste_rule_preflight": (
        "Use for a current England waste operation when the regulatory route is uncertain. "
        "Returns missing facts, permit/exemption/duty-of-care routing and official evidence. "
        "Do not use it to infer hazardous status, waste codes, permit conditions or regulator approval."
    ),
    "carrier_broker_dealer_registration_preflight": (
        "Use when an England business transports waste, acts as a waste broker or dealer, or needs to renew/change its carrier-broker-dealer registration. "
        "Returns the registration lifecycle route, current reviewed fee information and missing facts. It does not submit registration or independently assign legal tier status."
    ),
    "digital_waste_tracking_receipt_readiness": (
        "Use for an England waste receiving site preparing for phase-1 Digital Waste Tracking. "
        "Checks permitted/licensed receiving-site scope, the 1 October 2026 mandatory date, reporting-method readiness and evidence-linked review conditions."
    ),
    "permit_change_impact": (
        "Use for an existing England waste operation comparing current and proposed operating facts. "
        "Identifies changed modelled fields that require permit/exemption review; it does not decide that a variation or new permit is legally required."
    ),
}

def payment_enforced() -> bool:
    return os.getenv("WASTE_PAYMENT_ENFORCED", "0").strip() == "1"

def _meta(ctx: Any) -> dict[str, Any]:
    raw = getattr(getattr(ctx, "request_context", None), "meta", None)
    if isinstance(raw, dict):
        return dict(raw)
    dump = getattr(raw, "model_dump", None)
    if callable(dump):
        try:
            value = dump(by_alias=True, exclude_none=True)
        except TypeError:
            value = dump()
        return dict(value) if isinstance(value, dict) else {}
    return {}

def _record(tool: str, fn, *, meta: dict[str, Any] | None = None, paid: bool = False):
    started = time.perf_counter()
    status = "OK"
    try:
        return fn()
    except Exception:
        status = "ERROR"
        raise
    finally:
        record_call(tool, status, (time.perf_counter() - started) * 1000, meta=meta, paid=paid)

def service_info(x402: Any = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "product": PRODUCT,
        "brand": "RegEvidenceHub Waste",
        "version": __version__,
        "jurisdiction": "England",
        "transport": "streamable-http",
        "mcp": MCP_URL,
        "registry_name": REGISTRY_NAME,
        "decision_tools": list(PRICES),
        "free_discovery_tools": [
            "waste_rule_info","list_waste_rules","waste_source_status","check_waste_sources","get_source_registry"
        ],
        "payment_enforced": payment_enforced(),
        "payment_protocol": "x402-v2" if payment_enforced() else None,
        "prices": dict(PRICES),
        "fail_closed": True,
        "source_health": source_health(),
        "safety_boundary": "Preflight information only; not an Environment Agency permit, exemption, registration decision or legal advice.",
    }
    if x402 is not None:
        result["x402"] = x402.info(PRICES)
    return result

def _public_x402_document(gate: Any = None) -> dict[str, Any]:
    network = getattr(gate, "network", os.getenv("WASTE_X402_NETWORK", "eip155:8453"))
    return {
        "version": 1,
        "service": REGISTRY_NAME,
        "title": "RegEvidenceHub Waste",
        "mcp": MCP_URL,
        "paymentEnforced": payment_enforced(),
        "network": network,
        "scheme": "exact",
        "asset": BASE_USDC,
        "assetSymbol": "USDC",
        "facilitator": os.getenv("WASTE_X402_FACILITATOR_URL", "https://facilitator.payai.network"),
        "freeTools": ["waste_rule_info","list_waste_rules","waste_source_status","check_waste_sources","get_source_registry"],
        "paidTools": [{"name": name, "priceUSDC": price.lstrip("$")} for name, price in PRICES.items()],
    }

def _agent_card() -> dict[str, Any]:
    return {
        "name": "RegEvidenceHub Waste",
        "description": "Evidence-linked deterministic England waste-regulatory preflight for agents and workflow automation.",
        "version": __version__,
        "url": MCP_URL,
        "transport": "streamable-http",
        "registryName": REGISTRY_NAME,
        "keywords": [
            "England waste regulation","waste carrier registration","waste broker dealer registration",
            "Digital Waste Tracking","waste environmental permit","waste exemption","waste permit change",
            "Environment Agency compliance","waste duty of care",
        ],
        "recommendedWorkflow": [
            {"step":1,"tool":"waste_rule_info","billing":"free","purpose":"Inspect exact scope and pricing."},
            {"step":2,"tool":"waste_source_status","billing":"free","purpose":"Check official evidence health."},
            {"step":3,"tool":"waste_rule_preflight","billing":"x402","purpose":"Route a current waste operation."},
            {"step":4,"tool":"carrier_broker_dealer_registration_preflight OR digital_waste_tracking_receipt_readiness OR permit_change_impact","billing":"x402","purpose":"Use the narrow workflow matching the regulatory question."},
        ],
        "capabilities": {"freeDiscovery":["waste_rule_info","list_waste_rules","waste_source_status"],"paidDecisionTools":list(PRICES)},
        "safety": "Fail closed on stale, changed, unavailable, unreviewed or incomplete evidence. Informational preflight only.",
    }

def _openapi_document() -> dict[str, Any]:
    paths: dict[str, Any] = {}
    for path, summary in {
        "/":{"RegEvidenceHub Waste landing"},
        "/health":{"Operational health"},
        "/status":{"Source/payment/service status"},
        "/version":{"Release identity"},
        "/metrics":{"Aggregate commercial telemetry"},
        "/mcp":{"MCP Streamable HTTP endpoint"},
        "/.well-known/x402":{"x402 payment metadata"},
        "/.well-known/agent-card.json":{"Agent capability card"},
        "/llms.txt":{"LLM-readable capability guide"},
    }.items():
        paths[path] = {"get" if path != "/mcp" else "post":{"summary":next(iter(summary)),"responses":{"200":{"description":"OK"}}}}
    return {
        "openapi":"3.1.0",
        "info":{"title":"RegEvidenceHub Waste","version":__version__,"description":"Evidence-linked England waste regulatory decision service."},
        "servers":[{"url":PUBLIC_ORIGIN}],
        "paths":paths,
    }

def build_server():
    try:
        from mcp.server import MCPServer
        from mcp.server.mcpserver.context import Context
        from mcp.types import CallToolResult, ToolAnnotations
        from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
    except ImportError as exc:
        raise RuntimeError("Install the MCP extra and x402 v2 runtime") from exc

    globals()["Context"] = Context
    globals()["CallToolResult"] = CallToolResult

    def annotations(name: str, *, paid: bool = False) -> ToolAnnotations:
        return ToolAnnotations(
            title=TOOL_TITLES[name], readOnlyHint=True, destructiveHint=False,
            idempotentHint=not paid, openWorldHint=True,
        )

    server = MCPServer(
        "RegEvidenceHub Waste",
        title="RegEvidenceHub Waste",
        version=__version__,
        instructions=(
            "Evidence-linked England waste regulatory preflight. Prefer the narrowest workflow. "
            "Use carrier_broker_dealer_registration_preflight for carrier/broker/dealer registration lifecycle questions; "
            "digital_waste_tracking_receipt_readiness for receiving-site DWT phase-1 readiness; "
            "permit_change_impact for proposed operating changes; and waste_rule_preflight for general route selection. "
            "Check waste_source_status when evidence freshness matters. Decisions fail closed on stale, changed, unavailable, "
            "unreviewed or incomplete evidence. This is not regulator approval or legal advice."
        ),
    )

    enforced = payment_enforced()
    gate = None
    paid_handlers: dict[str, Any] = {}
    prices = {name: os.getenv("WASTE_X402_PRICE_" + name.upper(), value).strip() or value for name, value in PRICES.items()}

    if enforced:
        from .x402_mcp2 import MCP2X402Gate, PaidToolSpec
        gate = MCP2X402Gate()
        specs = {
            "waste_rule_preflight": (
                TOOL_DESCRIPTIONS["waste_rule_preflight"],
                {"type":"object","additionalProperties":True},
                {"nation":"England","role":"receiver","activities":["receive_waste"],"receives_controlled_waste":True},
                waste_preflight,
            ),
            "carrier_broker_dealer_registration_preflight": (
                TOOL_DESCRIPTIONS["carrier_broker_dealer_registration_preflight"],
                {"type":"object","required":["nation","role"],"additionalProperties":True},
                {"nation":"England","role":"carrier","action":"new_registration","own_waste_only":False},
                carrier_broker_dealer_registration_preflight,
            ),
            "digital_waste_tracking_receipt_readiness": (
                TOOL_DESCRIPTIONS["digital_waste_tracking_receipt_readiness"],
                {"type":"object","required":["nation"],"additionalProperties":True},
                {"nation":"England","receiving_authorisation":"permit","receives_controlled_waste":True,"reporting_method_ready":True},
                digital_waste_tracking_receipt_readiness,
            ),
            "permit_change_impact": (
                TOOL_DESCRIPTIONS["permit_change_impact"],
                {"type":"object","required":["nation","current","proposed"],"additionalProperties":True},
                {"nation":"England","current":{"maximum_quantity":"10 tonnes"},"proposed":{"maximum_quantity":"20 tonnes"}},
                impact,
            ),
        }
        for name, (description, schema, example, executor) in specs.items():
            def make_exec(fn, tool):
                return lambda args: _record(tool, lambda: fn(args), paid=True)
            paid_handlers[name] = gate.build(
                PaidToolSpec(name=name,price=prices[name],description=description,input_schema=schema,example=example),
                make_exec(executor,name),
            )

    def discovery(request, route: str) -> None:
        marker = str(request.headers.get("x-mcp-commercial-actor","")).strip().lower()
        record_discovery(route, request.url.query, owned_probe=marker in {"owned","owned_ci","owner","test","smoke"})

    @server.custom_route("/", methods=["GET"], include_in_schema=False)
    async def landing(request):
        discovery(request, "/")
        return HTMLResponse(
            f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RegEvidenceHub Waste</title></head><body><main style="font-family:system-ui;max-width:900px;margin:48px auto;padding:0 22px;line-height:1.55">
<h1>RegEvidenceHub Waste</h1><p>Agent-native, evidence-linked England waste regulatory preflight.</p>
<h2>Primary workflows</h2><ul>
<li><code>waste_rule_preflight</code> — $0.02 USDC</li>
<li><code>carrier_broker_dealer_registration_preflight</code> — $0.02 USDC</li>
<li><code>digital_waste_tracking_receipt_readiness</code> — $0.03 USDC</li>
<li><code>permit_change_impact</code> — $0.03 USDC</li></ul>
<p>MCP: <code>{MCP_URL}</code></p><p>Public AI MCP: <code>{PUBLIC_ORIGIN}/ai/mcp</code></p>
<p><a href="/pricing">pricing</a> · <a href="/llms.txt">llms.txt</a> · <a href="/.well-known/agent-card.json">agent card</a> · <a href="/metrics">metrics</a></p>
<p>Informational preflight only; not Environment Agency approval or legal advice.</p></main></body></html>"""
        )

    @server.custom_route("/health", methods=["GET"], include_in_schema=False)
    async def health(_request):
        h=source_health()
        payment_state="ready" if enforced else "disabled"
        return JSONResponse({
            "contract":"regevidencehub-ops-v1","status":"ok" if h["decision_usable"] else "review_required",
            "serving":True,"service":"RegEvidenceHub Waste","version":__version__,
            "commit":(os.getenv("RAILWAY_GIT_COMMIT_SHA") or "unknown")[:12],
            "source_state":"ready" if h["decision_usable"] else "review_required","payment_state":payment_state,
        },headers={"Cache-Control":"no-store"})

    @server.custom_route("/status", methods=["GET"], include_in_schema=False)
    async def status(_request):
        return JSONResponse(service_info(gate) | {"metrics_24h": public_usage_summary()["windows"]["24h"]},headers={"Cache-Control":"no-store"})

    @server.custom_route("/version", methods=["GET"], include_in_schema=False)
    async def version(_request):
        return JSONResponse({"contract":"regevidencehub-ops-v1","service":"RegEvidenceHub Waste","version":__version__,"commit":(os.getenv("RAILWAY_GIT_COMMIT_SHA") or "unknown")[:12],"public_origin":PUBLIC_ORIGIN})

    @server.custom_route("/metrics", methods=["GET"], include_in_schema=False)
    async def metrics(request):
        discovery(request, "/metrics")
        return JSONResponse(public_usage_summary(),headers={"Cache-Control":"no-store"})

    @server.custom_route("/source-audit", methods=["GET"], include_in_schema=False)
    async def source_audit(_request):
        checked=check_all_sources()
        return JSONResponse({"health":source_health(checked),"checked_sources":checked},headers={"Cache-Control":"no-store"})

    @server.custom_route("/pricing", methods=["GET"], include_in_schema=False)
    async def pricing(_request):
        rows="".join(f"<li><code>{name}</code> — {price} USDC</li>" for name,price in prices.items())
        return HTMLResponse(f"<html><body><h1>RegEvidenceHub Waste pricing</h1><ul>{rows}</ul><p>x402 v2 on Base mainnet when payment is enabled.</p></body></html>")

    for _path, _target in (("/privacy","/plugin/privacy"),("/terms","/plugin/terms"),("/support","/plugin/support")):
        async def redirect_policy(_request, target=_target):
            return RedirectResponse(target)
        server.custom_route(_path,methods=["GET"],include_in_schema=False)(redirect_policy)

    @server.custom_route("/robots.txt", methods=["GET"], include_in_schema=False)
    async def robots(_request):
        return PlainTextResponse(f"User-agent: *\nAllow: /\nSitemap: {PUBLIC_ORIGIN}/sitemap.xml\n")

    @server.custom_route("/sitemap.xml", methods=["GET"], include_in_schema=False)
    async def sitemap(_request):
        urls=["/","/pricing","/privacy","/terms","/support","/llms.txt","/.well-known/agent-card.json"]
        body='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(f"<url><loc>{PUBLIC_ORIGIN}{p}</loc></url>" for p in urls) + "</urlset>"
        return PlainTextResponse(body,media_type="application/xml")

    @server.custom_route("/llms.txt", methods=["GET"], include_in_schema=False)
    async def llms(request):
        discovery(request, "/llms.txt")
        return PlainTextResponse(
            f"# RegEvidenceHub Waste\nJurisdiction: England\nMCP: {MCP_URL}\nPublic AI MCP: {PUBLIC_ORIGIN}/ai/mcp\n"
            "Use for waste carrier/broker/dealer registration, Digital Waste Tracking receiving-site readiness, waste permit/exemption routing and permit-change impact.\n"
            "Free: waste_rule_info, list_waste_rules, waste_source_status. Paid commercial decisions use x402 v2.\n"
            "Fail closed on stale, changed, unavailable, unreviewed or incomplete official evidence. Not regulator approval or legal advice.\n"
        )

    @server.custom_route("/.well-known/mcp.json", methods=["GET"], include_in_schema=False)
    async def mcp_discovery(request):
        discovery(request, "/.well-known/mcp.json")
        return JSONResponse({
            "name":REGISTRY_NAME,"title":"RegEvidenceHub Waste","version":__version__,
            "transport":"streamable-http","url":MCP_URL,"publicAiUrl":f"{PUBLIC_ORIGIN}/ai/mcp",
            "keywords":_agent_card()["keywords"],
            "links":{"pricing":f"{PUBLIC_ORIGIN}/pricing","privacy":f"{PUBLIC_ORIGIN}/privacy","terms":f"{PUBLIC_ORIGIN}/terms","support":f"{PUBLIC_ORIGIN}/support"},
        })

    @server.custom_route("/.well-known/mcp/server-card.json", methods=["GET"], include_in_schema=False)
    async def server_card(request):
        discovery(request, "/.well-known/mcp/server-card.json")
        return JSONResponse(_agent_card())

    @server.custom_route("/.well-known/agent-card.json", methods=["GET"], include_in_schema=False)
    async def agent_card(request):
        discovery(request, "/.well-known/agent-card.json")
        return JSONResponse(_agent_card())

    @server.custom_route("/.well-known/agent.json", methods=["GET"], include_in_schema=False)
    async def agent_json(request):
        discovery(request, "/.well-known/agent.json")
        return JSONResponse(_agent_card())

    @server.custom_route("/agents.json", methods=["GET"], include_in_schema=False)
    async def agents_json(request):
        discovery(request, "/agents.json")
        return JSONResponse({"agents":[_agent_card()]})

    @server.custom_route("/.well-known/x402", methods=["GET"], include_in_schema=False)
    async def x402_discovery(request):
        discovery(request, "/.well-known/x402")
        return JSONResponse(_public_x402_document(gate))

    @server.custom_route("/openapi.json", methods=["GET"], include_in_schema=False)
    async def openapi(request):
        discovery(request, "/openapi.json")
        return JSONResponse(_openapi_document())

    @server.tool(description=TOOL_DESCRIPTIONS["waste_rule_info"], annotations=annotations("waste_rule_info"))
    def waste_rule_info(ctx: Context) -> dict[str, Any]:
        return _record("waste_rule_info", lambda: service_info(gate), meta=_meta(ctx))

    @server.tool(description=TOOL_DESCRIPTIONS["list_waste_rules"], annotations=annotations("list_waste_rules"))
    def list_waste_rules(ctx: Context) -> dict[str, Any]:
        return _record("list_waste_rules", catalogue, meta=_meta(ctx))

    @server.tool(description=TOOL_DESCRIPTIONS["waste_source_status"], annotations=annotations("waste_source_status"))
    def waste_source_status(ctx: Context) -> dict[str, Any]:
        return _record("waste_source_status", source_health, meta=_meta(ctx))

    @server.tool(description=TOOL_DESCRIPTIONS["check_waste_sources"], annotations=annotations("check_waste_sources"))
    def check_waste_sources(ctx: Context) -> dict[str, Any]:
        return _record("check_waste_sources", lambda: (lambda checked: source_health(checked) | {"checked_sources":checked})(check_all_sources()), meta=_meta(ctx))

    @server.tool(description=TOOL_DESCRIPTIONS["get_source_registry"], annotations=annotations("get_source_registry"))
    def get_source_registry(ctx: Context) -> list[dict[str, Any]]:
        return _record("get_source_registry", source_registry, meta=_meta(ctx))

    executors = {
        "waste_rule_preflight": waste_preflight,
        "carrier_broker_dealer_registration_preflight": carrier_broker_dealer_registration_preflight,
        "digital_waste_tracking_receipt_readiness": digital_waste_tracking_receipt_readiness,
        "permit_change_impact": impact,
    }
    if not enforced:
        @server.tool(name="waste_rule_preflight",description=TOOL_DESCRIPTIONS["waste_rule_preflight"],annotations=annotations("waste_rule_preflight",paid=True))
        def waste_rule_preflight_tool(scenario: dict[str, Any]) -> dict[str, Any]:
            return _record("waste_rule_preflight",lambda:waste_preflight(scenario),paid=True)

        @server.tool(name="carrier_broker_dealer_registration_preflight",description=TOOL_DESCRIPTIONS["carrier_broker_dealer_registration_preflight"],annotations=annotations("carrier_broker_dealer_registration_preflight",paid=True))
        def cbd_tool(scenario: dict[str, Any]) -> dict[str, Any]:
            return _record("carrier_broker_dealer_registration_preflight",lambda:carrier_broker_dealer_registration_preflight(scenario),paid=True)

        @server.tool(name="digital_waste_tracking_receipt_readiness",description=TOOL_DESCRIPTIONS["digital_waste_tracking_receipt_readiness"],annotations=annotations("digital_waste_tracking_receipt_readiness",paid=True))
        def dwt_tool(scenario: dict[str, Any]) -> dict[str, Any]:
            return _record("digital_waste_tracking_receipt_readiness",lambda:digital_waste_tracking_receipt_readiness(scenario),paid=True)

        @server.tool(name="permit_change_impact",description=TOOL_DESCRIPTIONS["permit_change_impact"],annotations=annotations("permit_change_impact",paid=True))
        def permit_tool(scenario: dict[str, Any]) -> dict[str, Any]:
            return _record("permit_change_impact",lambda:impact(scenario),paid=True)
    else:
        from .x402_mcp2 import invoke_mcp2_paid_handler
        @server.tool(name="waste_rule_preflight",description=TOOL_DESCRIPTIONS["waste_rule_preflight"],annotations=annotations("waste_rule_preflight",paid=True))
        def waste_rule_preflight_paid(scenario: dict[str, Any], ctx: Context) -> CallToolResult:
            return invoke_mcp2_paid_handler(paid_handlers["waste_rule_preflight"],tool_name="waste_rule_preflight",arguments=scenario,ctx=ctx)
        @server.tool(name="carrier_broker_dealer_registration_preflight",description=TOOL_DESCRIPTIONS["carrier_broker_dealer_registration_preflight"],annotations=annotations("carrier_broker_dealer_registration_preflight",paid=True))
        def cbd_paid(scenario: dict[str, Any], ctx: Context) -> CallToolResult:
            return invoke_mcp2_paid_handler(paid_handlers["carrier_broker_dealer_registration_preflight"],tool_name="carrier_broker_dealer_registration_preflight",arguments=scenario,ctx=ctx)
        @server.tool(name="digital_waste_tracking_receipt_readiness",description=TOOL_DESCRIPTIONS["digital_waste_tracking_receipt_readiness"],annotations=annotations("digital_waste_tracking_receipt_readiness",paid=True))
        def dwt_paid(scenario: dict[str, Any], ctx: Context) -> CallToolResult:
            return invoke_mcp2_paid_handler(paid_handlers["digital_waste_tracking_receipt_readiness"],tool_name="digital_waste_tracking_receipt_readiness",arguments=scenario,ctx=ctx)
        @server.tool(name="permit_change_impact",description=TOOL_DESCRIPTIONS["permit_change_impact"],annotations=annotations("permit_change_impact",paid=True))
        def permit_paid(scenario: dict[str, Any], ctx: Context) -> CallToolResult:
            return invoke_mcp2_paid_handler(paid_handlers["permit_change_impact"],tool_name="permit_change_impact",arguments=scenario,ctx=ctx)

    return server

def safe_mcp_surface_mounts(public_ai_app: object) -> list[object]:
    from starlette.routing import Mount
    return [Mount("/openai",app=public_ai_app),Mount("/ai",app=public_ai_app)]

def main() -> None:
    from contextlib import AsyncExitStack, asynccontextmanager
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route
    from .discovery_observability import DiscoveryObservabilityASGI
    from .public_ai_server import build_public_ai_server
    from .submission_pages import glama_claim_challenge, openai_apps_challenge, plugin_product_page, privacy_page, support_page, terms_page

    host=os.getenv("HOST","0.0.0.0")
    port=int(os.getenv("PORT","8000"))
    commercial_server=build_server()
    commercial_app=commercial_server.streamable_http_app(host=host,json_response=True,stateless_http=True)
    public_ai_server=build_public_ai_server()
    public_ai_app=public_ai_server.streamable_http_app(host=host,json_response=True,stateless_http=True)

    @asynccontextmanager
    async def lifespan(_app):
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(commercial_server.session_manager.run())
            await stack.enter_async_context(public_ai_server.session_manager.run())
            yield

    app=Starlette(routes=[
        Route("/waste-rule-preflight",endpoint=plugin_product_page,methods=["GET"]),
        Route("/plugin/privacy",endpoint=privacy_page,methods=["GET"]),
        Route("/plugin/terms",endpoint=terms_page,methods=["GET"]),
        Route("/plugin/support",endpoint=support_page,methods=["GET"]),
        Route("/.well-known/openai-apps-challenge",endpoint=openai_apps_challenge,methods=["GET"]),
        Route("/.well-known/glama.json",endpoint=glama_claim_challenge,methods=["GET"]),
        *safe_mcp_surface_mounts(public_ai_app),
        Mount("/",app=commercial_app),
    ],lifespan=lifespan)
    app=DiscoveryObservabilityASGI(app)
    uvicorn.run(app,host=host,port=port)

if __name__=="__main__":
    main()
