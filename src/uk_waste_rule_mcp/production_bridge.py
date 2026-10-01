"""Production HTTP/MCP surface for RegEvidenceHub Waste."""
from __future__ import annotations

import json
import os
import secrets
import time
from urllib.parse import parse_qs
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
from .case_state import DurableCaseStore
from .commercial import CommercialPlatformClient, CommercialPlatformError, PendingWasteReportStore
from .entitlement_token import verify_entitlement_token
from .sources import source_registry
from .schemas import CarrierRegistrationScenario, DigitalTrackingScenario, PermitChangeScenario, WasteRuleScenario

PUBLIC_ORIGIN = os.getenv("WASTE_PUBLIC_ORIGIN", "https://waste.regevidencehub.com").strip().rstrip("/")
MCP_URL = os.getenv("WASTE_PUBLIC_MCP_URL", f"{PUBLIC_ORIGIN}/mcp").strip()
REGISTRY_NAME = "io.github.ChanghuLiu/uk-waste-rule-mcp"
BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

SHARED_EXECUTION_ACTION = "waste_case_preflight"
SHARED_EXECUTION_WORKFLOWS = {
    "waste_rule_preflight": (WasteRuleScenario, waste_preflight),
    "waste_carrier_broker_dealer_preflight": (CarrierRegistrationScenario, carrier_broker_dealer_registration_preflight),
    "waste_digital_tracking_readiness": (DigitalTrackingScenario, digital_waste_tracking_receipt_readiness),
    "waste_permit_change_preflight": (PermitChangeScenario, impact),
}
COMMERCIAL_CLIENT = CommercialPlatformClient()
CASE_RUNTIME_DIR = os.getenv("WASTE_RUNTIME_DIR") or ("/data/waste-rule-mcp" if os.getenv("RAILWAY_ENVIRONMENT") else "/tmp/waste-rule-mcp")
DURABLE_CASES = DurableCaseStore(CASE_RUNTIME_DIR, ttl_seconds=int(os.getenv("WASTE_CASE_TTL_SECONDS", "86400")))
REPORT_CHECKOUTS = PendingWasteReportStore(
    os.getenv("WASTE_REPORT_CHECKOUT_STORE_PATH", "").strip() or os.path.join(CASE_RUNTIME_DIR, "report-checkouts.json"),
    ttl_seconds=int(os.getenv("WASTE_REPORT_CHECKOUT_TTL_SECONDS", "604800")),
)

def shared_execution_enabled() -> bool:
    return os.getenv("WASTE_SHARED_EXECUTION_ENABLED", "0").strip() == "1"

PRICES = {
    "waste_rule_preflight": "$0.02",
    "waste_carrier_broker_dealer_preflight": "$0.02",
    "waste_digital_tracking_readiness": "$0.03",
    "waste_permit_change_preflight": "$0.03",
}
TOOL_TITLES = {
    "waste_service_info": "Waste regulatory service information",
    "waste_rule_catalog": "Supported waste regulatory routes",
    "waste_rule_info": "Waste regulatory service information (legacy alias)",
    "list_waste_rules": "Supported waste regulatory routes (legacy alias)",
    "waste_source_status": "Waste official-source status",
    "waste_source_audit": "Live waste source audit",
    "waste_source_registry": "Waste official-source registry",
    "waste_rule_preflight": "England waste-rule preflight",
    "waste_carrier_broker_dealer_preflight": "Waste carrier/broker/dealer registration preflight",
    "waste_digital_tracking_readiness": "Digital Waste Tracking receipt readiness",
    "waste_permit_change_preflight": "Waste permit change-impact preflight",
}
TOOL_DESCRIPTIONS = {
    "waste_service_info": (
        "FREE SERVICE/DISCOVERY metadata tool. Select this for questions about RegEvidenceHub Waste scope, "
        "available tools, which tools are FREE versus PAID, x402 payment mode, exact prices, jurisdiction, "
        "or service capabilities. Do NOT use for source freshness or a case-specific regulatory decision."
    ),
    "waste_rule_info": (
        "LEGACY COMPATIBILITY alias for waste_service_info. Use waste_service_info for new integrations. "
        "Returns the same free service/discovery metadata so previously installed connectors do not fail with Unknown tool."
    ),
    "list_waste_rules": (
        "LEGACY COMPATIBILITY alias for waste_rule_catalog. Use waste_rule_catalog for new integrations. "
        "Returns the same free supported-role/activity catalogue so previously installed connectors do not fail with Unknown tool."
    ),
    "waste_rule_catalog": (
        "FREE RULE-CATALOG tool. Select this when an agent needs the exact supported England waste roles, "
        "activity identifiers, and bounded regulatory routes before preparing a case-specific preflight. "
        "Do NOT use it to decide a user's case; use waste_rule_preflight or the matching narrow workflow."
    ),
    "waste_source_status": (
        "FREE OFFICIAL-EVIDENCE HEALTH tool. Select only for freshness, availability, changed-source, "
        "or decision-usable status for monitored GOV.UK / Environment Agency evidence. "
        "Do NOT use for tool pricing, service capabilities, or operational routing."
    ),
    "waste_source_audit": (
        "FREE LIVE SOURCE-AUDIT tool. Select only when a fresh network check of monitored official sources "
        "and fingerprint comparison is required. It does not accept new baselines or change reviewed evidence. "
        "Do NOT use for a waste-route decision; use waste_rule_preflight after source health is established."
    ),
    "waste_source_registry": (
        "FREE SOURCE-REGISTRY catalogue tool. Select when an agent needs the monitored official-source metadata, "
        "source identifiers, reviewed baseline state, or coverage inventory. Do NOT use it as a regulatory decision tool."
    ),
    "waste_rule_preflight": (
        "PAID $0.02 DEFAULT ENTRY TOOL for a CURRENT England waste operation when the unresolved question is which "
        "waste regulatory route applies. Returns missing facts, permit/exemption/duty-of-care routing and official evidence. "
        "Do NOT use for a specific carrier/broker/dealer registration lifecycle, Digital Waste Tracking receiving-site readiness, "
        "or a current-versus-proposed permit change; use the corresponding narrow tool."
    ),
    "waste_carrier_broker_dealer_preflight": (
        "PAID $0.02 CARRIER/BROKER/DEALER REGISTRATION LIFECYCLE tool for England. Select for new registration, renewal, "
        "detail/activity changes, legal-type changes, or lower-to-upper changes. Returns the bounded registration route, "
        "current reviewed fee route and missing facts. It does not submit or renew a registration. "
        "Do NOT use for site permit changes or Digital Waste Tracking readiness."
    ),
    "waste_digital_tracking_readiness": (
        "PAID $0.03 DIGITAL WASTE TRACKING RECEIVING-SITE READINESS tool for England phase 1. Select when the unresolved "
        "question is whether a permitted/licensed receiving site is in scope and operationally ready for receipt reporting "
        "around the 1 October 2026 mandatory start. It never submits DWT records. "
        "Do NOT use for carrier registration or permit-change comparison."
    ),
    "waste_permit_change_preflight": (
        "PAID $0.03 PERMIT-CHANGE IMPACT PREFLIGHT for an EXISTING England waste operation when both current and proposed "
        "operating facts are available. Identifies changed modelled fields requiring permit/exemption review and returns evidence. "
        "It does not decide that a variation or new permit is legally required. "
        "Do NOT use for a brand-new operation route, carrier registration, or DWT readiness."
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
            "waste_service_info","waste_rule_catalog","waste_source_status","waste_source_audit","waste_source_registry"
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
    doc = {
        "version": 1,
        "x402Version": 2,
        "service": REGISTRY_NAME,
        "serviceName": "RegEvidenceHub Waste",
        "title": "RegEvidenceHub Waste",
        "description": "Evidence-linked deterministic England waste-regulatory preflight for agents and workflow automation.",
        "type": "mcp",
        "resource": MCP_URL,
        "mcp": MCP_URL,
        "paymentEnforced": payment_enforced(),
        "network": network,
        "scheme": "exact",
        "asset": BASE_USDC,
        "assetSymbol": "USDC",
        "facilitator": os.getenv("WASTE_X402_FACILITATOR_URL", "https://facilitator.payai.network"),
        "tags": ["waste","england","permit","carrier","compliance"],
        "freeTools": ["waste_service_info","waste_rule_catalog","waste_source_status","waste_source_audit","waste_source_registry"],
        "paidTools": [{"name": name, "priceUSDC": price.lstrip("$")} for name, price in PRICES.items()],
    }
    pay_to = getattr(gate, "pay_to", "") if gate is not None else ""
    if pay_to:
        doc["payTo"] = pay_to
    return doc

def _agent_card() -> dict[str, Any]:
    return {
        "name": "RegEvidenceHub Waste",
        "description": "Evidence-linked deterministic England waste-regulatory preflight for agents and workflow automation.",
        "version": __version__,
        "url": MCP_URL,
        "transport": "streamable-http",
        "registryName": REGISTRY_NAME,
        "repository": "https://github.com/ChanghuLiu/uk-waste-rule-mcp",
        "homepage": f"{PUBLIC_ORIGIN}/waste-rule-preflight",
        "support": f"{PUBLIC_ORIGIN}/support",
        "keywords": [
            "England waste regulation","waste carrier registration","waste broker dealer registration",
            "Digital Waste Tracking","waste environmental permit","waste exemption","waste permit change",
            "Environment Agency compliance","waste duty of care",
        ],
        "recommendedWorkflow": [
            {"step":1,"tool":"waste_service_info","billing":"free","purpose":"Inspect exact scope and pricing."},
            {"step":2,"tool":"waste_source_status","billing":"free","purpose":"Check official evidence health."},
            {"step":3,"tool":"waste_rule_preflight","billing":"x402","purpose":"Route a current waste operation."},
            {"step":4,"tool":"waste_carrier_broker_dealer_preflight OR waste_digital_tracking_readiness OR waste_permit_change_preflight","billing":"x402","purpose":"Use the narrow workflow matching the regulatory question."},
        ],
        "capabilities": {"freeDiscovery":["waste_service_info","waste_rule_catalog","waste_source_status"],"paidDecisionTools":list(PRICES)},
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
    from .http_x402 import paid_openapi_paths
    paths.update(paid_openapi_paths())
    return {
        "openapi":"3.1.0",
        "info":{
            "title":"RegEvidenceHub Waste",
            "version":__version__,
            "description":"Evidence-linked England waste regulatory decision service.",
            "contact":{"email":"launchcircle.server@gmail.com"},
            "x-guidance":(
                "Use the narrowest paid route for the regulatory question: waste-rule routing, carrier/broker/dealer registration, Digital Waste Tracking readiness, or permit-change impact. "
                "Provide the business role, waste activity, site/transport facts, permit or registration context, and change details requested by the schema. "
                "The service returns deterministic evidence-linked preflight output and fails closed when official evidence is stale, changed, unreviewed, or incomplete."
            ),
        },
        "servers":[{"url":PUBLIC_ORIGIN}],
        "externalDocs":{"description":"Agent-readable usage and capability guide","url":f"{PUBLIC_ORIGIN}/llms.txt"},
        "paths":paths,
    }

def build_server():
    try:
        from mcp.server import MCPServer
        from mcp.server.mcpserver.context import Context
        from mcp.types import CallToolResult, ToolAnnotations
        from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
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
            "Use waste_carrier_broker_dealer_preflight for carrier/broker/dealer registration lifecycle questions; "
            "waste_digital_tracking_readiness for receiving-site DWT phase-1 readiness; "
            "waste_permit_change_preflight for proposed operating changes; and waste_rule_preflight for general route selection. "
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
                WasteRuleScenario.model_json_schema(),
                {"nation":"England","role":"receiver","activities":["receive_waste"],"site_location":"Leeds","waste_types":["mixed controlled waste"],"hazardous_status":False,"authorisation_status":"permit"},
                {"product":"UK Waste Rule & Permit Change-Impact MCP","schema_version":"0.1","decision":{"route":"PERMIT_OR_EXEMPTION_AND_DIGITAL_TRACKING_REVIEW","status":"SCREENING_COMPLETE_REVIEW_REQUIRED","deterministic":True}},
                waste_preflight,
            ),
            "waste_carrier_broker_dealer_preflight": (
                TOOL_DESCRIPTIONS["waste_carrier_broker_dealer_preflight"],
                CarrierRegistrationScenario.model_json_schema(),
                {"nation":"England","role":"carrier","action":"new_registration","own_waste_only":False},
                {"product":"UK Waste Rule & Permit Change-Impact MCP","schema_version":"0.2","decision":{"route":"CARRIER_BROKER_DEALER_REGISTRATION","status":"SCREENING_COMPLETE","deterministic":True,"registration_required":True,"role":"carrier","action":"NEW_REGISTRATION","fee_route":"STANDARD_REGISTRATION_FEE_ROUTE"}},
                carrier_broker_dealer_registration_preflight,
            ),
            "waste_digital_tracking_readiness": (
                TOOL_DESCRIPTIONS["waste_digital_tracking_readiness"],
                DigitalTrackingScenario.model_json_schema(),
                {"nation":"England","receiving_authorisation":"permit","receives_controlled_waste":True,"reporting_method_ready":True},
                {"product":"UK Waste Rule & Permit Change-Impact MCP","schema_version":"0.2","decision":{"route":"DIGITAL_WASTE_TRACKING_RECEIPT_READINESS","status":"SCREENING_COMPLETE","deterministic":True,"phase1_in_scope":True}},
                digital_waste_tracking_receipt_readiness,
            ),
            "waste_permit_change_preflight": (
                TOOL_DESCRIPTIONS["waste_permit_change_preflight"],
                PermitChangeScenario.model_json_schema(),
                {"nation":"England","current":{"maximum_quantity":"10 tonnes"},"proposed":{"maximum_quantity":"20 tonnes"}},
                {"product":"UK Waste Rule & Permit Change-Impact MCP","schema_version":"0.1","decision":{"route":"PERMIT_CHANGE_IMPACT","status":"REVIEW_REQUIRED","deterministic":True,"changed_fields":["maximum_quantity"]}},
                impact,
            ),
        }
        for name, (description, schema, example, output_example, executor) in specs.items():
            def make_exec(fn, tool):
                return lambda args: _record(tool, lambda: fn(args), paid=True)
            paid_handlers[name] = gate.build(
                PaidToolSpec(name=name,price=prices[name],description=description,input_schema=schema,example=example,output_example=output_example),
                make_exec(executor,name),
            )

    def discovery(request, route: str) -> None:
        marker = str(request.headers.get("x-mcp-commercial-actor","")).strip().lower()
        record_discovery(route, request.url.query, owned_probe=marker in {"owned","owned_ci","owner","test","smoke"})

    @server.custom_route("/waste-report", methods=["GET"], include_in_schema=False)
    async def waste_report_page(_request):
        return HTMLResponse("""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="referrer" content="no-referrer"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Waste compliance report — RegEvidenceHub</title><main style="font-family:system-ui;max-width:820px;margin:40px auto;padding:0 20px;line-height:1.55"><h1>England Waste Compliance Preflight Report</h1><p>Run one evidence-linked regulatory preflight. Your case details stay with the Waste service; only checkout email and bounded purchase metadata go to the shared payment service. No product account is required.</p><form method="post" action="/waste-report/checkout"><label>Preflight type <select name="workflow"><option value="waste_rule_preflight">Waste rules and permit route — £19</option><option value="waste_carrier_broker_dealer_preflight">Carrier, broker or dealer registration — £19</option><option value="waste_digital_tracking_readiness">Digital Waste Tracking readiness — £19</option><option value="waste_permit_change_preflight">Permit change impact — £19</option></select></label><p><label>Scenario JSON<br><textarea name="payload" required rows="12" style="width:100%" placeholder='{"nation":"England","role":"receiver","activities":["receive_waste"]}'></textarea></label></p><p><label>Email for checkout and verified recovery<br><input name="contact_email" type="email" autocomplete="email" required maxlength="254"></label></p><button type="submit">Continue to secure Stripe Checkout</button></form><p><a href="/waste-report/recover">Recover a paid report</a> · <a href="/pricing">API pricing</a></p><p>Informational preflight only; not Environment Agency approval or legal advice.</p></main></html>""")

    @server.custom_route("/waste-report/checkout", methods=["POST"], include_in_schema=False)
    async def waste_report_checkout(request):
        from html import escape
        try:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                form = await request.json()
            else:
                parsed = parse_qs((await request.body()).decode("utf-8", "replace"), keep_blank_values=True)
                form = {key: values[-1] for key, values in parsed.items()}
            workflow = str(form.get("workflow") or "")
            payload_value = form.get("payload")
            payload = json.loads(payload_value) if isinstance(payload_value, str) else payload_value
            contact_email = str(form.get("contact_email") or "").strip()
            if workflow not in SHARED_EXECUTION_WORKFLOWS or not isinstance(payload, dict):
                raise ValueError("Choose a supported preflight and provide scenario JSON.")
            if not contact_email or len(contact_email) > 254 or contact_email.count("@") != 1 or any(ch.isspace() for ch in contact_email):
                raise ValueError("Enter a valid email address for payment and recovery.")
            model, _executor = SHARED_EXECUTION_WORKFLOWS[workflow]
            validated_payload = model.model_validate(payload).model_dump(exclude_none=True)
        except Exception as exc:
            return HTMLResponse(f"<main><h1>Checkout could not start</h1><p>{escape(str(exc))}</p><p><a href='/waste-report'>Review the report form</a></p></main>", status_code=422)

        pending_token = REPORT_CHECKOUTS.create(workflow=workflow, payload=validated_payload)
        source_channel = "direct"
        try:
            checkout = await COMMERCIAL_CLIENT.create_report_checkout(
                contact_email=contact_email,
                source_channel=source_channel,
                success_url=f"{PUBLIC_ORIGIN}/waste-report/checkout-success",
                cancel_url=f"{PUBLIC_ORIGIN}/waste-report/checkout-cancelled",
            )
            REPORT_CHECKOUTS.attach_checkout(pending_token, checkout["checkout_id"])
        except Exception:
            REPORT_CHECKOUTS.discard(pending_token)
            return HTMLResponse("<main><h1>Checkout is temporarily unavailable</h1><p>Your case has not been charged. Try again later.</p><a href='/waste-report'>Return to the report form</a></main>", status_code=503)
        response = RedirectResponse(checkout["checkout_url"], status_code=303)
        response.set_cookie(key=f"report_claim_{checkout['checkout_id']}", value=checkout["report_claim_token"], max_age=1800, httponly=True,
                            secure=PUBLIC_ORIGIN.startswith("https://"), samesite="lax", path="/waste-report/checkout-success")
        return response

    @server.custom_route("/waste-report/checkout-success", methods=["GET"], include_in_schema=False)
    async def waste_report_success(request):
        from html import escape
        checkout_id = next((key.removeprefix("report_session_") for key in request.cookies if key.startswith("report_session_")), "")
        if not checkout_id:
            checkout_id = next((key.removeprefix("report_claim_") for key in request.cookies if key.startswith("report_claim_")), "")
        if not checkout_id:
            return HTMLResponse("""<!doctype html><html><meta charset=utf-8><meta name=referrer content=no-referrer><title>Recover report</title><main><h1>Opening recovered report…</h1><p id=status>Verifying access</p></main><script>(()=>{const p=new URLSearchParams(location.hash.slice(1));history.replaceState(null,'',location.pathname);const checkout_id=p.get('checkout_id'),report_session=p.get('report_session');if(!checkout_id||!report_session){document.getElementById('status').textContent='Recovery link is missing or expired.';return;}fetch('/api/v1/report-access/redeem',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({checkout_id,report_session})}).then(r=>{if(!r.ok)throw Error();location.replace('/waste-report/checkout-success');}).catch(()=>{document.getElementById('status').textContent='Payment may still be processing, or this recovery link is invalid, expired, or already used.';});})();</script></html>""", headers={"Cache-Control":"no-store", "Referrer-Policy":"no-referrer", "Content-Security-Policy":"default-src 'none'; script-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'"})
        row = REPORT_CHECKOUTS.get_by_checkout_id(checkout_id)
        if row is None:
            return HTMLResponse("<main><h1>Report unavailable</h1><p>Use verified-email recovery or restart checkout.</p></main>", status_code=403)
        report_session = request.cookies.get(f"report_session_{checkout_id}")
        if not report_session:
            claim = request.cookies.get(f"report_claim_{checkout_id}")
            if not claim:
                return HTMLResponse("<main><h1>Report unavailable</h1><p>Use verified-email recovery.</p></main>", status_code=403)
            try:
                claimed = await COMMERCIAL_CLIENT.claim_report_access(checkout_id=checkout_id, report_claim_token=claim)
                report_session = str(claimed["report_session"])
            except Exception:
                return HTMLResponse("<main><h1>Payment pending</h1><p>We could not verify paid access yet. Refresh this page or recover by email.</p></main>", status_code=403)
        try:
            verified = await COMMERCIAL_CLIENT.verify_report_access(checkout_id=checkout_id, report_session=report_session)
        except Exception:
            verified = False
        if not verified:
            return HTMLResponse("<main><h1>Report unavailable</h1><p>Access could not be verified.</p></main>", status_code=403)
        model, executor = SHARED_EXECUTION_WORKFLOWS[row["workflow"]]
        report = executor(model.model_validate(row["payload"]).model_dump(exclude_none=True))
        response = HTMLResponse(f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="referrer" content="no-referrer"><title>Your waste compliance report</title><main style="font-family:system-ui;max-width:900px;margin:40px auto;padding:0 20px;line-height:1.55"><h1>Your England Waste Compliance Report</h1><p>Verified paid access. Review the cited official sources and resolve any REVIEW_REQUIRED or missing-information findings before acting.</p><pre style="white-space:pre-wrap;overflow-wrap:anywhere">{escape(json.dumps(report, indent=2, ensure_ascii=False))}</pre><p>Order reference: <code>{escape(checkout_id)}</code></p><a href="/waste-report/recover">Recover access by verified email</a></main></html>""", headers={"Cache-Control":"private, no-store", "Referrer-Policy":"no-referrer"})
        response.set_cookie(key=f"report_session_{checkout_id}", value=report_session, max_age=86400, httponly=True, secure=PUBLIC_ORIGIN.startswith("https://"), samesite="lax", path="/waste-report/checkout-success")
        response.delete_cookie(key=f"report_claim_{checkout_id}", path="/waste-report/checkout-success")
        return response

    @server.custom_route("/waste-report/checkout-cancelled", methods=["GET"], include_in_schema=False)
    async def waste_report_cancelled(_request):
        return HTMLResponse("<main><h1>Checkout cancelled</h1><p>No paid report was created.</p><a href='/waste-report'>Return to Waste report</a></main>")

    @server.custom_route("/api/v1/report-access/redeem", methods=["POST"], include_in_schema=False)
    async def redeem_waste_report(request):
        try:
            body = await request.json()
            checkout_id, report_session = str(body.get("checkout_id") or ""), str(body.get("report_session") or "")
        except Exception:
            return JSONResponse({"status":"invalid_request"}, status_code=422)
        row = REPORT_CHECKOUTS.get_by_checkout_id(checkout_id)
        try:
            verified = bool(row is not None and await COMMERCIAL_CLIENT.verify_report_access(checkout_id=checkout_id, report_session=report_session))
        except Exception:
            verified = False
        if not verified:
            return JSONResponse({"status":"report_access_unavailable"}, status_code=403)
        response = Response(status_code=204, headers={"Cache-Control":"no-store", "Referrer-Policy":"no-referrer"})
        response.set_cookie(key=f"report_session_{checkout_id}", value=report_session, max_age=86400, httponly=True, secure=PUBLIC_ORIGIN.startswith("https://"), samesite="lax", path="/waste-report/checkout-success")
        return response

    @server.custom_route("/api/v1/report-access/recovery", methods=["POST"], include_in_schema=False)
    async def waste_report_recovery(request):
        from html import escape
        try:
            body = await request.json()
            checkout_id, contact_email = str(body.get("checkout_id") or ""), str(body.get("contact_email") or "").strip()
        except Exception:
            return JSONResponse({"status":"invalid_request"}, status_code=422)
        if len(contact_email) > 254 or contact_email.count("@") != 1 or any(ch.isspace() for ch in contact_email):
            return JSONResponse({"status":"invalid_request"}, status_code=422)
        try:
            await COMMERCIAL_CLIENT.start_report_recovery(checkout_id=checkout_id, contact_email=contact_email)
        except Exception:
            pass
        return JSONResponse({"status":"If a paid report matches those details, a recovery link will be sent."}, headers={"Cache-Control":"no-store"})

    @server.custom_route("/waste-report/recover", methods=["GET"], include_in_schema=False)
    async def waste_report_recover(_request):
        return HTMLResponse("""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="referrer" content="no-referrer"><title>Recover Waste report</title><main><h1>Recover report access</h1><form id="form"><label>Order reference <input name="checkout_id" required></label><label>Checkout email <input name="contact_email" type="email" autocomplete="email" required></label><button>Send recovery link</button></form><p id="status" aria-live="polite"></p></main><script>document.getElementById('form').addEventListener('submit',async e=>{e.preventDefault();const f=e.currentTarget,r=await fetch('/api/v1/report-access/recovery',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({checkout_id:f.elements.checkout_id.value,contact_email:f.elements.contact_email.value})});document.getElementById('status').textContent=r.ok?'If a paid report matches those details, a recovery link will be sent.':'Recovery is temporarily unavailable. Try again later.';});</script></html>""", headers={"Cache-Control":"no-store", "Referrer-Policy":"no-referrer", "Content-Security-Policy":"default-src 'none'; script-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'"})

    @server.custom_route("/api/v1/continuation-case", methods=["POST"], include_in_schema=False)
    async def continuation_case(request):
        if not shared_execution_enabled():
            return JSONResponse({"status":"shared_execution_disabled"}, status_code=503)
        try:
            body = await request.json()
            action = str(body.get("action") or SHARED_EXECUTION_ACTION)
            workflow = str(body.get("workflow") or "waste_rule_preflight")
            if action != SHARED_EXECUTION_ACTION or workflow not in SHARED_EXECUTION_WORKFLOWS:
                return JSONResponse({"status":"invalid_request","error_code":"unsupported_action"}, status_code=422)
            model, _ = SHARED_EXECUTION_WORKFLOWS[workflow]
            payload = model.model_validate(body.get("payload") or {}).model_dump(exclude_none=True)
            source_bucket = str(body.get("source_bucket") or "direct")
            classification = str(body.get("classification") or "unknown")
            owner_test = bool(body.get("owner_test") or False)
            if classification not in {"unknown","confirmed_external","owner_test","synthetic"}:
                return JSONResponse({"status":"invalid_request","error_code":"invalid_classification"}, status_code=422)
        except Exception as exc:
            return JSONResponse({"status":"invalid_request","reason":str(exc)}, status_code=422)
        row = DURABLE_CASES.create(
            action=action, workflow=workflow, payload=payload, source_bucket=source_bucket,
            classification=classification, owner_test=owner_test,
        )
        try:
            continuation = await COMMERCIAL_CLIENT.issue_continuation(case_ref=row.case_ref, state_ref=row.state_ref)
        except Exception:
            return JSONResponse({"status":"commercial_unavailable"}, status_code=503)
        return JSONResponse({
            "product_id": COMMERCIAL_CLIENT.product_id,
            "case_ref": row.case_ref,
            "state_ref": row.state_ref,
            "workflow": row.workflow,
            "continuation_token": continuation["continuation_token"],
            "expires_in_seconds": continuation.get("expires_in_seconds"),
        })

    @server.custom_route("/api/v1/execute-restored-case", methods=["POST"], include_in_schema=False)
    async def execute_restored_case(request):
        if not shared_execution_enabled():
            return JSONResponse({"status":"shared_execution_disabled"}, status_code=503)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"status":"invalid_request"}, status_code=422)
        if body.get("contract_version") not in {None, "reh-execution-v1"}:
            return JSONResponse({"status":"invalid_request","error_code":"unsupported_contract_version"}, status_code=422)
        if body.get("product_id") not in {None, COMMERCIAL_CLIENT.product_id}:
            return JSONResponse({"status":"invalid_request","error_code":"wrong_product"}, status_code=422)
        if body.get("action") not in {None, SHARED_EXECUTION_ACTION}:
            return JSONResponse({"status":"invalid_request","error_code":"unsupported_action"}, status_code=422)
        try:
            claims = await verify_entitlement_token(
                str(body.get("entitlement_token") or ""),
                platform_url=COMMERCIAL_CLIENT.platform_url,
                expected_product_id=COMMERCIAL_CLIENT.product_id,
            )
        except ValueError:
            return JSONResponse({"status":"forbidden"}, status_code=403)
        row = DURABLE_CASES.get(str(body.get("state_ref") or ""))
        if row is None:
            return JSONResponse({"status":"case_unavailable","error_code":"state_not_found"}, status_code=404)
        if row.action != SHARED_EXECUTION_ACTION or row.workflow not in SHARED_EXECUTION_WORKFLOWS:
            return JSONResponse({"status":"invalid_request","error_code":"stored_action_mismatch"}, status_code=422)
        _, executor = SHARED_EXECUTION_WORKFLOWS[row.workflow]
        try:
            decision = executor(dict(row.payload))
        except Exception:
            return JSONResponse({
                "contract_version":"reh-execution-v1","product_id":COMMERCIAL_CLIENT.product_id,
                "status":"failed","execution_id":f"waste_{secrets.token_hex(12)}",
                "result":None,"error_code":"execution_unavailable",
            }, status_code=503)
        return JSONResponse({
            "contract_version":"reh-execution-v1",
            "product_id":COMMERCIAL_CLIENT.product_id,
            "status":"executed",
            "execution_id":f"waste_{secrets.token_hex(12)}",
            "result":{
                "gateway_status":"OK",
                "workflow":row.workflow,
                "decision":decision,
                "entitlement_code":str(claims.get("entitlement_code") or ""),
            },
            "error_code":None,
        })

    @server.custom_route("/", methods=["GET"], include_in_schema=False)
    async def landing(request):
        discovery(request, "/")
        return HTMLResponse(
            f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Agent-native, evidence-linked England waste regulatory preflight with x402-paid MCP decision tools for waste routing, carrier registration, Digital Waste Tracking readiness and permit-change checks.">
<meta name="robots" content="index,follow"><link rel="canonical" href="{PUBLIC_ORIGIN}/">
<meta property="og:title" content="RegEvidenceHub Waste"><meta property="og:description" content="England waste regulatory preflight for agents, with evidence health and x402-paid decision tools."><meta property="og:url" content="{PUBLIC_ORIGIN}/">
<title>RegEvidenceHub Waste</title></head><body><main style="font-family:system-ui;max-width:900px;margin:48px auto;padding:0 22px;line-height:1.55">
<h1>RegEvidenceHub Waste</h1><p>Agent-native, evidence-linked England waste regulatory preflight.</p>
<h2>Primary workflows</h2><ul>
<li><code>waste_rule_preflight</code> — $0.02 USDC</li>
<li><code>waste_carrier_broker_dealer_preflight</code> — $0.02 USDC</li>
<li><code>waste_digital_tracking_readiness</code> — $0.03 USDC</li>
<li><code>waste_permit_change_preflight</code> — $0.03 USDC</li></ul>
<p>MCP: <code>{MCP_URL}</code></p><p>Public AI MCP: <code>{PUBLIC_ORIGIN}/ai/mcp</code></p>
<p><a href="/waste-report">Buy a one-off verified report — £19</a> · <a href="/pricing">API pricing</a> · <a href="/llms.txt">llms.txt</a> · <a href="/.well-known/agent-card.json">agent card</a> · <a href="/metrics">metrics</a></p>
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
        return HTMLResponse(f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="RegEvidenceHub Waste x402 pricing for England waste regulatory MCP decision tools."><meta name="robots" content="index,follow">
<link rel="canonical" href="{PUBLIC_ORIGIN}/pricing"><title>Pricing — RegEvidenceHub Waste</title></head>
<body><main style="font-family:system-ui;max-width:900px;margin:48px auto;padding:0 22px;line-height:1.55">
<h1>RegEvidenceHub Waste pricing</h1><p>Machine-to-machine pricing for the commercial MCP endpoint <code>{MCP_URL}</code>.</p>
<ul>{rows}</ul><p>Protocol: x402 v2 · Network: Base mainnet · Asset: USDC.</p>
<p><a href="/.well-known/x402">x402 discovery metadata</a> · <a href="/.well-known/agent-card.json">agent card</a> · <a href="/llms.txt">llms.txt</a></p>
</main></body></html>""")

    for _path, _target in (("/privacy","/plugin/privacy"),("/terms","/plugin/terms"),("/support","/plugin/support")):
        async def redirect_policy(_request, target=_target):
            return RedirectResponse(target)
        server.custom_route(_path,methods=["GET"],include_in_schema=False)(redirect_policy)

    @server.custom_route("/robots.txt", methods=["GET"], include_in_schema=False)
    async def robots(_request):
        return PlainTextResponse(f"User-agent: *\nAllow: /\nSitemap: {PUBLIC_ORIGIN}/sitemap.xml\n")

    @server.custom_route("/sitemap.xml", methods=["GET"], include_in_schema=False)
    async def sitemap(_request):
        urls=["/","/waste-report","/pricing","/privacy","/terms","/support","/llms.txt","/.well-known/agent-card.json"]
        body='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(f"<url><loc>{PUBLIC_ORIGIN}{p}</loc></url>" for p in urls) + "</urlset>"
        return PlainTextResponse(body,media_type="application/xml")

    @server.custom_route("/llms.txt", methods=["GET"], include_in_schema=False)
    async def llms(request):
        discovery(request, "/llms.txt")
        return PlainTextResponse(
            f"# RegEvidenceHub Waste\nJurisdiction: England\nMCP: {MCP_URL}\nPublic AI MCP: {PUBLIC_ORIGIN}/ai/mcp\n"
            "Use for waste carrier/broker/dealer registration, Digital Waste Tracking receiving-site readiness, waste permit/exemption routing and permit-change impact.\n"
            "Free: waste_service_info, waste_rule_catalog, waste_source_status, waste_source_audit, waste_source_registry.\n"
            "Paid: waste_rule_preflight $0.02 USDC; waste_carrier_broker_dealer_preflight $0.02 USDC; waste_digital_tracking_readiness $0.03 USDC; waste_permit_change_preflight $0.03 USDC.\n"
            f"x402 discovery: {PUBLIC_ORIGIN}/.well-known/x402\nAgent card: {PUBLIC_ORIGIN}/.well-known/agent-card.json\n"
            "Paid commercial decisions use x402 v2 on Base mainnet. Fail closed on stale, changed, unavailable, unreviewed or incomplete official evidence. Not regulator approval or legal advice.\n"
        )

    @server.custom_route("/.well-known/mcp.json", methods=["GET"], include_in_schema=False)
    async def mcp_discovery(request):
        discovery(request, "/.well-known/mcp.json")
        return JSONResponse({
            "name":REGISTRY_NAME,"title":"RegEvidenceHub Waste","version":__version__,
            "transport":"streamable-http","url":MCP_URL,"publicAiUrl":f"{PUBLIC_ORIGIN}/ai/mcp",
            "keywords":_agent_card()["keywords"],
            "links":{"homepage":f"{PUBLIC_ORIGIN}/waste-rule-preflight","repository":"https://github.com/ChanghuLiu/uk-waste-rule-mcp","pricing":f"{PUBLIC_ORIGIN}/pricing","privacy":f"{PUBLIC_ORIGIN}/privacy","terms":f"{PUBLIC_ORIGIN}/terms","support":f"{PUBLIC_ORIGIN}/support"},
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

    @server.tool(description=TOOL_DESCRIPTIONS["waste_service_info"], annotations=annotations("waste_service_info"))
    def waste_service_info(ctx: Context) -> dict[str, Any]:
        return _record("waste_service_info", lambda: service_info(gate), meta=_meta(ctx))

    @server.tool(description=TOOL_DESCRIPTIONS["waste_rule_catalog"], annotations=annotations("waste_rule_catalog"))
    def waste_rule_catalog(ctx: Context) -> dict[str, Any]:
        return _record("waste_rule_catalog", catalogue, meta=_meta(ctx))

    @server.tool(name="waste_rule_info", description=TOOL_DESCRIPTIONS["waste_rule_info"], annotations=annotations("waste_rule_info"))
    def waste_rule_info_legacy(ctx: Context) -> dict[str, Any]:
        return _record("waste_rule_info", lambda: service_info(gate), meta=_meta(ctx))

    @server.tool(name="list_waste_rules", description=TOOL_DESCRIPTIONS["list_waste_rules"], annotations=annotations("list_waste_rules"))
    def list_waste_rules_legacy(ctx: Context) -> dict[str, Any]:
        return _record("list_waste_rules", catalogue, meta=_meta(ctx))

    @server.tool(description=TOOL_DESCRIPTIONS["waste_source_status"], annotations=annotations("waste_source_status"))
    def waste_source_status(ctx: Context) -> dict[str, Any]:
        return _record("waste_source_status", source_health, meta=_meta(ctx))

    @server.tool(description=TOOL_DESCRIPTIONS["waste_source_audit"], annotations=annotations("waste_source_audit"))
    def waste_source_audit(ctx: Context) -> dict[str, Any]:
        return _record("waste_source_audit", lambda: (lambda checked: source_health(checked) | {"checked_sources":checked})(check_all_sources()), meta=_meta(ctx))

    @server.tool(description=TOOL_DESCRIPTIONS["waste_source_registry"], annotations=annotations("waste_source_registry"))
    def waste_source_registry(ctx: Context) -> list[dict[str, Any]]:
        return _record("waste_source_registry", source_registry, meta=_meta(ctx))

    executors = {
        "waste_rule_preflight": waste_preflight,
        "waste_carrier_broker_dealer_preflight": carrier_broker_dealer_registration_preflight,
        "waste_digital_tracking_readiness": digital_waste_tracking_receipt_readiness,
        "waste_permit_change_preflight": impact,
    }
    if not enforced:
        @server.tool(name="waste_rule_preflight",description=TOOL_DESCRIPTIONS["waste_rule_preflight"],annotations=annotations("waste_rule_preflight",paid=True))
        def waste_rule_preflight_tool(scenario: WasteRuleScenario) -> dict[str, Any]:
            return _record("waste_rule_preflight",lambda:waste_preflight(scenario.model_dump(exclude_none=True)),paid=True)

        @server.tool(name="waste_carrier_broker_dealer_preflight",description=TOOL_DESCRIPTIONS["waste_carrier_broker_dealer_preflight"],annotations=annotations("waste_carrier_broker_dealer_preflight",paid=True))
        def cbd_tool(scenario: CarrierRegistrationScenario) -> dict[str, Any]:
            return _record("waste_carrier_broker_dealer_preflight",lambda:carrier_broker_dealer_registration_preflight(scenario.model_dump(exclude_none=True)),paid=True)

        @server.tool(name="waste_digital_tracking_readiness",description=TOOL_DESCRIPTIONS["waste_digital_tracking_readiness"],annotations=annotations("waste_digital_tracking_readiness",paid=True))
        def dwt_tool(scenario: DigitalTrackingScenario) -> dict[str, Any]:
            return _record("waste_digital_tracking_readiness",lambda:digital_waste_tracking_receipt_readiness(scenario.model_dump(exclude_none=True)),paid=True)

        @server.tool(name="waste_permit_change_preflight",description=TOOL_DESCRIPTIONS["waste_permit_change_preflight"],annotations=annotations("waste_permit_change_preflight",paid=True))
        def permit_tool(scenario: PermitChangeScenario) -> dict[str, Any]:
            return _record("waste_permit_change_preflight",lambda:impact(scenario.model_dump(exclude_none=True)),paid=True)
    else:
        from .x402_mcp2 import invoke_mcp2_paid_handler
        @server.tool(name="waste_rule_preflight",description=TOOL_DESCRIPTIONS["waste_rule_preflight"],annotations=annotations("waste_rule_preflight",paid=True))
        def waste_rule_preflight_paid(scenario: WasteRuleScenario, ctx: Context) -> CallToolResult:
            return invoke_mcp2_paid_handler(paid_handlers["waste_rule_preflight"],tool_name="waste_rule_preflight",arguments=scenario.model_dump(exclude_none=True),ctx=ctx)
        @server.tool(name="waste_carrier_broker_dealer_preflight",description=TOOL_DESCRIPTIONS["waste_carrier_broker_dealer_preflight"],annotations=annotations("waste_carrier_broker_dealer_preflight",paid=True))
        def cbd_paid(scenario: CarrierRegistrationScenario, ctx: Context) -> CallToolResult:
            return invoke_mcp2_paid_handler(paid_handlers["waste_carrier_broker_dealer_preflight"],tool_name="waste_carrier_broker_dealer_preflight",arguments=scenario.model_dump(exclude_none=True),ctx=ctx)
        @server.tool(name="waste_digital_tracking_readiness",description=TOOL_DESCRIPTIONS["waste_digital_tracking_readiness"],annotations=annotations("waste_digital_tracking_readiness",paid=True))
        def dwt_paid(scenario: DigitalTrackingScenario, ctx: Context) -> CallToolResult:
            return invoke_mcp2_paid_handler(paid_handlers["waste_digital_tracking_readiness"],tool_name="waste_digital_tracking_readiness",arguments=scenario.model_dump(exclude_none=True),ctx=ctx)
        @server.tool(name="waste_permit_change_preflight",description=TOOL_DESCRIPTIONS["waste_permit_change_preflight"],annotations=annotations("waste_permit_change_preflight",paid=True))
        def permit_paid(scenario: PermitChangeScenario, ctx: Context) -> CallToolResult:
            return invoke_mcp2_paid_handler(paid_handlers["waste_permit_change_preflight"],tool_name="waste_permit_change_preflight",arguments=scenario.model_dump(exclude_none=True),ctx=ctx)

    from .http_x402 import install_http_routes
    install_http_routes(server)
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
    from .http_x402 import wrap_http_x402
    app=wrap_http_x402(app)
    uvicorn.run(app,host=host,port=port)

if __name__=="__main__":
    main()
