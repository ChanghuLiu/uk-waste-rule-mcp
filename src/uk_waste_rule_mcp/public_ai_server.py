"""Permanent payment-free MCP surface for public AI ecosystems."""

from __future__ import annotations

from typing import Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from . import __version__
from .engine import PRODUCT, list_waste_rules as catalogue, permit_change_impact as impact, waste_preflight
from .monitor import source_health


PUBLIC_AI_SERVER_NAME = "RegEvidenceHub Waste"
PUBLIC_AI_SERVER_DESCRIPTION = (
    "Evidence-linked England waste-rule and permit-change preflight for businesses, "
    "waste carriers, brokers, dealers, receivers and operators. Use it to identify "
    "the relevant regulatory route, inspect persisted official-source health, check "
    "which facts are missing, and screen whether a proposed operational change needs "
    "permit or exemption review. Results are conservative preflight information, "
    "not an Environment Agency decision, permit, exemption, registration or legal advice."
)
PUBLIC_AI_TOOL_NAMES = (
    "waste_rule_info",
    "list_waste_rules",
    "waste_source_status",
    "waste_rule_preflight",
    "permit_change_impact",
)


def _annotations(title: str) -> ToolAnnotations:
    return ToolAnnotations(
        title=title,
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )


def build_public_ai_server() -> MCPServer:
    """Build the isolated payment-free server used by ChatGPT, Claude and Grok."""

    server = MCPServer(
        PUBLIC_AI_SERVER_NAME,
        title=PUBLIC_AI_SERVER_NAME,
        description=PUBLIC_AI_SERVER_DESCRIPTION,
        version=__version__,
        instructions=(
            PUBLIC_AI_SERVER_DESCRIPTION
            + " All tools on this endpoint are free and payment-free. "
            + "Use list_waste_rules for supported roles and activities, then use "
            + "waste_rule_preflight for a current operation or permit_change_impact "
            + "for a proposed change. Check waste_source_status when evidence freshness "
            + "matters. Never infer hazardous status, permit conditions, exemption "
            + "eligibility, waste codes, quantity thresholds or regulator approval."
        ),
    )

    @server.tool(
        annotations=_annotations("Waste preflight service information"),
        structured_output=True,
    )
    def waste_rule_info() -> dict[str, Any]:
        """Explain the payment-free public AI surface and its safety boundary."""
        health = source_health()
        return {
            "product": PRODUCT,
            "version": __version__,
            "jurisdiction": "England",
            "surface": "public_ai_payment_free",
            "tools": list(PUBLIC_AI_TOOL_NAMES),
            "payment": "none_on_public_ai_surface",
            "fail_closed": True,
            "source_health": health,
            "disclaimer": (
                "Preflight information only; not an Environment Agency decision, "
                "permit, exemption, registration or legal advice."
            ),
        }

    @server.tool(
        annotations=_annotations("List supported waste roles and activities"),
        structured_output=True,
    )
    def list_waste_rules() -> dict[str, Any]:
        """List the bounded England waste roles, activities and modelled routes."""
        return catalogue()

    @server.tool(
        annotations=_annotations("Check persisted waste source health"),
        structured_output=True,
    )
    def waste_source_status() -> dict[str, Any]:
        """Return reviewed official-source freshness and fail-closed status."""
        return source_health()

    @server.tool(
        annotations=_annotations("Run an England waste-rule preflight"),
        structured_output=True,
    )
    def waste_rule_preflight(scenario: dict[str, Any]) -> dict[str, Any]:
        """Run a payment-free conservative preflight for a current waste activity."""
        return waste_preflight(scenario)

    @server.tool(
        annotations=_annotations("Screen waste permit change impact"),
        structured_output=True,
    )
    def permit_change_impact(scenario: dict[str, Any]) -> dict[str, Any]:
        """Compare current and proposed facts and identify changes requiring review."""
        return impact(scenario)

    return server
