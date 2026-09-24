"""Permanent payment-free MCP surface for public AI ecosystems."""
from __future__ import annotations

from typing import Any
from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from . import __version__
from .engine import (
    PRODUCT,
    carrier_broker_dealer_registration_preflight as cbd_preflight,
    digital_waste_tracking_receipt_readiness as dwt_readiness,
    list_waste_rules as catalogue,
    permit_change_impact as impact,
    waste_preflight,
)
from .monitor import source_health

PUBLIC_AI_SERVER_NAME = "RegEvidenceHub Waste"
PUBLIC_AI_SERVER_DESCRIPTION = (
    "Evidence-linked England waste regulatory preflight for businesses, carriers, brokers, dealers, "
    "receiving sites and waste operators. It covers general route selection, carrier/broker/dealer "
    "registration lifecycle, Digital Waste Tracking receiving-site readiness and permit-change impact. "
    "Results are conservative preflight information, not Environment Agency approval or legal advice."
)
PUBLIC_AI_TOOL_NAMES = (
    "waste_rule_info",
    "list_waste_rules",
    "waste_source_status",
    "waste_rule_preflight",
    "carrier_broker_dealer_registration_preflight",
    "digital_waste_tracking_receipt_readiness",
    "permit_change_impact",
)

def _annotations(title: str) -> ToolAnnotations:
    return ToolAnnotations(
        title=title, readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
    )

def build_public_ai_server() -> MCPServer:
    server=MCPServer(
        PUBLIC_AI_SERVER_NAME,
        title=PUBLIC_AI_SERVER_NAME,
        description=PUBLIC_AI_SERVER_DESCRIPTION,
        version=__version__,
        instructions=(
            PUBLIC_AI_SERVER_DESCRIPTION
            + " All tools on this endpoint are free and payment-free. "
            + "Use list_waste_rules for scope discovery; waste_rule_preflight for general routing; "
            + "carrier_broker_dealer_registration_preflight for registration lifecycle questions; "
            + "digital_waste_tracking_receipt_readiness for phase-1 receiving-site readiness; "
            + "permit_change_impact for proposed operating changes; and waste_source_status for evidence freshness. "
            + "Never infer hazardous status, waste codes, permit conditions, exemption eligibility or regulator approval."
        ),
    )

    @server.tool(annotations=_annotations("Waste preflight service information"), structured_output=True)
    def waste_rule_info() -> dict[str,Any]:
        return {
            "product":PRODUCT,"version":__version__,"jurisdiction":"England",
            "surface":"public_ai_payment_free","tools":list(PUBLIC_AI_TOOL_NAMES),
            "payment":"none_on_public_ai_surface","fail_closed":True,"source_health":source_health(),
            "disclaimer":"Preflight information only; not an Environment Agency decision, permit, exemption, registration or legal advice.",
        }

    @server.tool(annotations=_annotations("List supported waste roles and activities"), structured_output=True)
    def list_waste_rules() -> dict[str,Any]:
        return catalogue()

    @server.tool(annotations=_annotations("Check persisted waste source health"), structured_output=True)
    def waste_source_status() -> dict[str,Any]:
        return source_health()

    @server.tool(name="waste_rule_preflight", annotations=_annotations("Run an England waste-rule preflight"), structured_output=True)
    def waste_rule_preflight_tool(scenario: dict[str,Any]) -> dict[str,Any]:
        return waste_preflight(scenario)

    @server.tool(name="carrier_broker_dealer_registration_preflight", annotations=_annotations("Check waste carrier broker dealer registration"), structured_output=True)
    def carrier_broker_dealer_registration_preflight_tool(scenario: dict[str,Any]) -> dict[str,Any]:
        return cbd_preflight(scenario)

    @server.tool(name="digital_waste_tracking_receipt_readiness", annotations=_annotations("Check Digital Waste Tracking receipt readiness"), structured_output=True)
    def digital_waste_tracking_receipt_readiness_tool(scenario: dict[str,Any]) -> dict[str,Any]:
        return dwt_readiness(scenario)

    @server.tool(annotations=_annotations("Screen waste permit change impact"), structured_output=True)
    def permit_change_impact(scenario: dict[str,Any]) -> dict[str,Any]:
        return impact(scenario)

    return server
