from __future__ import annotations

import os
import time
from typing import Any, Callable

from .analytics import record_call
from .engine import (
    carrier_broker_dealer_registration_preflight,
    digital_waste_tracking_receipt_readiness,
    permit_change_impact,
    waste_preflight,
)
from .schemas import (
    CarrierRegistrationScenario,
    DigitalTrackingScenario,
    PermitChangeScenario,
    WasteRuleScenario,
)

PUBLIC_ORIGIN = os.getenv("WASTE_PUBLIC_ORIGIN", "https://waste.regevidencehub.com").strip().rstrip("/")
DEFAULT_NETWORK = "eip155:8453"

RULE_PATH = "/api/v1/waste-rule-preflight"
CARRIER_PATH = "/api/v1/waste-carrier-broker-dealer-preflight"
DWT_PATH = "/api/v1/waste-digital-tracking-readiness"
PERMIT_PATH = "/api/v1/waste-permit-change-preflight"

SPECS: dict[str, dict[str, Any]] = {
    "waste_rule_preflight": {
        "path": RULE_PATH,
        "price": "$0.02",
        "schema": WasteRuleScenario.model_json_schema(),
        "example": {
            "nation": "England",
            "role": "receiver",
            "activities": ["receive_waste"],
            "site_location": "Leeds",
            "waste_types": ["mixed controlled waste"],
            "hazardous_status": False,
            "authorisation_status": "permit",
        },
        "output": {
            "product": "UK Waste Rule & Permit Change-Impact MCP",
            "schema_version": "0.1",
            "decision": {
                "route": "PERMIT_OR_EXEMPTION_AND_DIGITAL_TRACKING_REVIEW",
                "status": "SCREENING_COMPLETE_REVIEW_REQUIRED",
                "deterministic": True,
            },
        },
        "summary": "Paid England waste-rule preflight",
        "description": (
            "General current-operation routing for permit/exemption/duty-of-care and "
            "Digital Waste Tracking review using the same deterministic engine as the MCP tool."
        ),
    },
    "waste_carrier_broker_dealer_preflight": {
        "path": CARRIER_PATH,
        "price": "$0.02",
        "schema": CarrierRegistrationScenario.model_json_schema(),
        "example": {
            "nation": "England",
            "role": "carrier",
            "action": "new_registration",
            "own_waste_only": False,
        },
        "output": {
            "product": "UK Waste Rule & Permit Change-Impact MCP",
            "schema_version": "0.2",
            "decision": {
                "route": "CARRIER_BROKER_DEALER_REGISTRATION",
                "status": "SCREENING_COMPLETE",
                "deterministic": True,
                "registration_required": True,
            },
        },
        "summary": "Paid waste carrier/broker/dealer registration preflight",
        "description": (
            "England carrier/broker/dealer registration lifecycle preflight using the "
            "same deterministic engine as the MCP tool."
        ),
    },
    "waste_digital_tracking_readiness": {
        "path": DWT_PATH,
        "price": "$0.03",
        "schema": DigitalTrackingScenario.model_json_schema(),
        "example": {
            "nation": "England",
            "receiving_authorisation": "permit",
            "receives_controlled_waste": True,
            "reporting_method_ready": True,
        },
        "output": {
            "product": "UK Waste Rule & Permit Change-Impact MCP",
            "schema_version": "0.2",
            "decision": {
                "route": "DIGITAL_WASTE_TRACKING_RECEIPT_READINESS",
                "status": "SCREENING_COMPLETE",
                "deterministic": True,
                "phase1_in_scope": True,
            },
        },
        "summary": "Paid Digital Waste Tracking readiness preflight",
        "description": (
            "England receiving-site Digital Waste Tracking readiness preflight using "
            "the same deterministic engine as the MCP tool."
        ),
    },
    "waste_permit_change_preflight": {
        "path": PERMIT_PATH,
        "price": "$0.03",
        "schema": PermitChangeScenario.model_json_schema(),
        "example": {
            "nation": "England",
            "current": {"maximum_quantity": "10 tonnes"},
            "proposed": {"maximum_quantity": "20 tonnes"},
        },
        "output": {
            "product": "UK Waste Rule & Permit Change-Impact MCP",
            "schema_version": "0.1",
            "decision": {
                "route": "PERMIT_CHANGE_IMPACT",
                "status": "REVIEW_REQUIRED",
                "deterministic": True,
                "changed_fields": ["maximum_quantity"],
            },
        },
        "summary": "Paid waste permit change-impact preflight",
        "description": (
            "England current-versus-proposed waste permit/exemption change-impact "
            "preflight using the same deterministic engine as the MCP tool."
        ),
    },
}

EXECUTORS: dict[str, tuple[type, Callable[[dict[str, Any]], dict[str, Any]]]] = {
    "waste_rule_preflight": (WasteRuleScenario, waste_preflight),
    "waste_carrier_broker_dealer_preflight": (
        CarrierRegistrationScenario,
        carrier_broker_dealer_registration_preflight,
    ),
    "waste_digital_tracking_readiness": (
        DigitalTrackingScenario,
        digital_waste_tracking_receipt_readiness,
    ),
    "waste_permit_change_preflight": (PermitChangeScenario, permit_change_impact),
}


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _price(name: str) -> str:
    default = str(SPECS[name]["price"])
    return (
        os.getenv("WASTE_X402_PRICE_" + name.upper(), default).strip()
        or default
    )


def settings() -> dict[str, str | bool]:
    return {
        "enabled": _truthy(os.getenv("WASTE_PAYMENT_ENFORCED", "0")),
        "network": os.getenv("WASTE_X402_NETWORK", DEFAULT_NETWORK).strip() or DEFAULT_NETWORK,
        "pay_to": os.getenv("WASTE_X402_PAY_TO", "").strip(),
        "facilitator_url": os.getenv(
            "WASTE_X402_FACILITATOR_URL", "https://facilitator.payai.network"
        ).strip(),
    }


def _amount(value: str) -> str:
    return value[1:] if value.startswith("$") else value


def paid_openapi_paths() -> dict[str, Any]:
    paths: dict[str, Any] = {}
    error_402 = {
        "description": (
            "Payment Required. Inspect the runtime x402 v2 PAYMENT-REQUIRED header "
            "for authoritative chain, asset, amount and payment requirements."
        )
    }
    for name, spec in SPECS.items():
        paths[str(spec["path"])] = {
            "post": {
                "operationId": name.replace("_", "-"),
                "summary": spec["summary"],
                "description": (
                    str(spec["description"])
                    + " Payment verification precedes deterministic business execution. "
                      "Official evidence freshness still gates the result. "
                      "Informational preflight only; not Environment Agency approval or legal advice."
                ),
                "tags": ["waste", "england", "regulatory", "x402"],
                "x-payment-info": {
                    "price": {
                        "mode": "fixed",
                        "currency": "USD",
                        "amount": _amount(_price(name)),
                    },
                    "protocols": [{"x402": {}}],
                },
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": spec["schema"],
                            "example": spec["example"],
                        }
                    },
                },
                "responses": {
                    "200": {"description": "Evidence-linked deterministic waste preflight result."},
                    "402": error_402,
                    "422": {"description": "Invalid request."},
                },
            }
        }
    return paths


def _execute(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    model_cls, executor = EXECUTORS[name]
    started = time.perf_counter()
    status = "OK"
    try:
        model = model_cls.model_validate(payload)
        return executor(model.model_dump(exclude_none=True))
    except Exception:
        status = "ERROR"
        raise
    finally:
        record_call(
            name + "_http",
            status,
            (time.perf_counter() - started) * 1000,
            paid=True,
        )


def install_http_routes(server: Any) -> None:
    from starlette.responses import JSONResponse

    for name, spec in SPECS.items():
        path = str(spec["path"])

        def make_handler(tool_name: str):
            async def handler(request):
                if not _truthy(os.getenv("WASTE_PAYMENT_ENFORCED", "0")):
                    return JSONResponse(
                        {"error": "HTTP x402 compatibility surface is disabled in this environment."},
                        status_code=503,
                    )
                try:
                    payload = await request.json()
                except Exception:
                    return JSONResponse({"error": "Expected a JSON object body."}, status_code=422)
                if not isinstance(payload, dict):
                    return JSONResponse({"error": "Expected a JSON object body."}, status_code=422)
                try:
                    result = _execute(tool_name, payload)
                except Exception as exc:
                    return JSONResponse(
                        {"error": "Invalid request.", "detail": str(exc)},
                        status_code=422,
                    )
                return JSONResponse(result)
            return handler

        server.custom_route(path, methods=["POST"], include_in_schema=False)(
            make_handler(name)
        )


def wrap_http_x402(app: Any) -> Any:
    cfg = settings()
    if not cfg["enabled"]:
        return app
    if not cfg["pay_to"]:
        raise RuntimeError("WASTE_X402_PAY_TO is required when HTTP x402 is enabled")

    try:
        from x402.extensions.bazaar import (
            OutputConfig,
            bazaar_resource_server_extension,
            declare_discovery_extension,
        )
        from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
        from x402.http.middleware.fastapi import PaymentMiddlewareASGI
        from x402.http.types import RouteConfig
        from x402.mechanisms.evm.exact import ExactEvmServerScheme
        from x402.server import x402ResourceServer
    except ImportError as exc:
        raise RuntimeError("HTTP x402 support requires x402[fastapi,evm]") from exc

    network = str(cfg["network"])
    if not network.startswith("eip155:"):
        raise RuntimeError("Waste HTTP x402 compatibility supports eip155:* exact payment only")

    facilitator = HTTPFacilitatorClient(
        FacilitatorConfig(url=str(cfg["facilitator_url"]))
    )
    resource_server = x402ResourceServer(facilitator)
    resource_server.register(network, ExactEvmServerScheme())
    resource_server.register_extension(bazaar_resource_server_extension)

    def discovery_extension(spec: dict[str, Any]) -> dict[str, Any]:
        extensions = declare_discovery_extension(
            input=spec["example"],
            input_schema=spec["schema"],
            body_type="json",
            output=OutputConfig(
                example=spec["output"],
                schema={"type": "object", "additionalProperties": True},
            ),
        )
        bazaar = extensions.get("bazaar", {})
        info = bazaar.get("info", {}) if isinstance(bazaar, dict) else {}
        input_info = info.get("input", {}) if isinstance(info, dict) else {}
        if not isinstance(input_info, dict):
            raise RuntimeError("Bazaar HTTP discovery declaration missing input metadata")
        input_info["method"] = "POST"
        return extensions

    routes: dict[str, Any] = {}
    for name, spec in SPECS.items():
        path = str(spec["path"])
        routes[f"POST {path}"] = RouteConfig(
            accepts=[
                PaymentOption(
                    scheme="exact",
                    pay_to=str(cfg["pay_to"]),
                    price=_price(name),
                    network=network,
                )
            ],
            resource=f"{PUBLIC_ORIGIN}{path}",
            mime_type="application/json",
            description=(
                str(spec["description"])
                + " Payment verification precedes deterministic execution. "
                  "Not Environment Agency approval or legal advice."
            ),
            extensions=discovery_extension(spec),
        )

    return PaymentMiddlewareASGI(app, routes=routes, server=resource_server)
