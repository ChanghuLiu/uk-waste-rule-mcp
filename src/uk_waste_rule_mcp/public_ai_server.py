"""Permanent payment-free MCP surface for public AI ecosystems."""
from __future__ import annotations

from typing import Any, Literal

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

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
    "Read-only, evidence-linked England waste regulatory preflight for businesses, carriers, brokers, dealers, "
    "receiving sites and waste operators. It routes current waste operations, checks carrier/broker/dealer registration "
    "lifecycle questions, Digital Waste Tracking receiving-site readiness, permit-change impact and official-source health. "
    "It intentionally does not submit registrations, permits, exemptions or DWT records, manage regulator records, "
    "classify hazardous waste, assign waste codes, approve operations, or provide legal advice."
)
PUBLIC_AI_TOOL_NAMES = (
    "waste_service_info",
    "waste_rule_catalog",
    "waste_source_status",
    "waste_rule_preflight",
    "waste_carrier_broker_dealer_preflight",
    "waste_digital_tracking_readiness",
    "waste_permit_change_preflight",
)

class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WasteRuleScenario(_StrictModel):
    nation: Literal["England"] | None = Field(
        default=None,
        description="UK nation for the operation. This public preflight currently supports England only and never infers jurisdiction.",
    )
    role: Literal["producer","carrier","broker","dealer","receiver","operator"] | None = Field(
        default=None,
        description="Primary waste role. Use receiver/operator for sites taking or operating on waste; carrier/broker/dealer for movement or arranging roles.",
    )
    activities: list[Literal[
        "produce_controlled_waste","transport_waste","arrange_waste","receive_waste","store_waste","treat_recover_dispose_waste"
    ]] = Field(
        default_factory=list,
        description="One or more modelled activities. Do not invent waste codes or hazardous status from an activity label.",
    )
    site_location: str | None = Field(
        default=None,
        description="Site or sufficiently precise operating location in England when location matters to the route.",
    )
    waste_types: list[str] | str | None = Field(
        default=None,
        description="User-supplied waste types or codes. Do not infer EWC codes from free text.",
    )
    hazardous_status: bool | None = Field(
        default=None,
        description="Whether hazardous waste is involved, only when explicitly known from the user's facts; otherwise leave null.",
    )
    authorisation_status: Literal["permit","exemption","licence","none","other"] | None = Field(
        default=None,
        description="Current receiving/operator authorisation when known. Do not infer permit or exemption status.",
    )


class CarrierRegistrationScenario(_StrictModel):
    nation: Literal["England"] | None = Field(
        default=None,
        description="UK nation. This workflow currently supports England only.",
    )
    role: Literal["carrier","broker","dealer"] | None = Field(
        default=None,
        description="Registration role being checked: carrier, broker, or dealer.",
    )
    action: Literal[
        "new_registration","renew","change_details","change_activity","change_legal_type","lower_to_upper"
    ] = Field(
        default="new_registration",
        description="Registration lifecycle action. Use renew only for an existing registration; use change_* only for an existing registration change.",
    )
    own_waste_only: bool | None = Field(
        default=None,
        description="For carriers, whether the business transports only waste it produces itself. Leave null if not established.",
    )
    construction_demolition_waste: bool | None = Field(
        default=None,
        description="For an own-waste carrier, whether construction or demolition waste is carried; this affects the current route.",
    )
    existing_registration_tier: Literal["upper","lower"] | None = Field(
        default=None,
        description="Existing registration tier for renewal checks. Do not infer the tier from the user's business type.",
    )


class DigitalTrackingScenario(_StrictModel):
    nation: Literal["England"] | None = Field(
        default=None,
        description="UK nation. This workflow models England phase-1 receiving-site timing only.",
    )
    receiving_authorisation: Literal["permit","permitted","licence","licensed","exemption","registered_exemption","other"] | None = Field(
        default=None,
        description="Receiving-site authorisation. Do not infer authorisation from the fact that a site receives waste.",
    )
    receives_controlled_waste: bool | None = Field(
        default=None,
        description="Whether the site receives controlled waste; required to determine phase-1 receiving-site scope.",
    )
    reporting_method_ready: bool | None = Field(
        default=None,
        description="Whether an operational receipt-reporting route is ready. Leave null if readiness has not been confirmed.",
    )
    as_of_date: str | None = Field(
        default=None,
        description="Optional assessment date in YYYY-MM-DD. Omit to use the service's current date.",
    )


class PermitOperationFacts(_StrictModel):
    site_location: str | None = Field(default=None, description="Current or proposed site location.")
    activities: list[str] | None = Field(default=None, description="Current or proposed waste activities.")
    waste_types: list[str] | str | None = Field(default=None, description="Current or proposed user-supplied waste types/codes.")
    hazardous_status: bool | None = Field(default=None, description="Known hazardous-waste status; never infer it.")
    maximum_quantity: str | int | float | None = Field(default=None, description="Current or proposed maximum quantity, preserving the user's unit/context.")
    storage_method: str | None = Field(default=None, description="Current or proposed storage method.")
    treatment_method: str | None = Field(default=None, description="Current or proposed treatment method.")
    operating_hours: str | None = Field(default=None, description="Current or proposed operating hours.")


class PermitChangeScenario(_StrictModel):
    nation: Literal["England"] | None = Field(
        default=None,
        description="UK nation. This workflow currently supports England only.",
    )
    current: PermitOperationFacts = Field(
        description="Current operating facts. Supply only facts actually known from the existing operation/authorisation.",
    )
    proposed: PermitOperationFacts = Field(
        description="Proposed operating facts to compare against current facts. The tool identifies changed modelled fields but does not decide that a permit variation is legally required.",
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
    server = MCPServer(
        PUBLIC_AI_SERVER_NAME,
        title=PUBLIC_AI_SERVER_NAME,
        description=PUBLIC_AI_SERVER_DESCRIPTION,
        version=__version__,
        instructions=(
            PUBLIC_AI_SERVER_DESCRIPTION
            + " All tools on this endpoint are free and payment-free. "
            + "Start with waste_service_info for service scope or waste_rule_catalog for valid role/activity identifiers. "
            + "Use waste_rule_preflight only for general current-operation routing. "
            + "Use waste_carrier_broker_dealer_preflight instead for carrier/broker/dealer registration lifecycle questions. "
            + "Use waste_digital_tracking_readiness instead for phase-1 England receiving-site reporting readiness. "
            + "Use waste_permit_change_preflight instead when comparing known current and proposed operating facts. "
            + "Use waste_source_status only for official-evidence freshness. "
            + "Never infer hazardous status, waste codes, permit conditions, exemption eligibility or regulator approval."
        ),
    )

    @server.tool(
        description=(
            "FREE SERVICE/DISCOVERY metadata tool. Use for questions about this connector's England scope, "
            "available tools, payment-free public-AI surface, fail-closed behavior, and safety boundaries. "
            "Do NOT use for evidence freshness; use waste_source_status. Do NOT use for a case-specific regulatory route; "
            "use waste_rule_preflight or the narrower registration, DWT, or permit-change tool."
        ),
        annotations=_annotations("Waste service and tool information"),
        structured_output=True,
    )
    def waste_service_info() -> dict[str, Any]:
        return {
            "product": PRODUCT,
            "version": __version__,
            "jurisdiction": "England",
            "surface": "public_ai_payment_free",
            "tools": list(PUBLIC_AI_TOOL_NAMES),
            "payment": "none_on_public_ai_surface",
            "fail_closed": True,
            "source_health": source_health(),
            "disclaimer": "Read-only preflight information only; not an Environment Agency decision, filing, permit, exemption, registration or legal advice.",
        }

    @server.tool(
        description=(
            "FREE RULE CATALOG tool. Use before a case-specific preflight when an agent needs the exact supported role IDs, "
            "activity IDs, and bounded route names accepted by this service. Do NOT use it to decide a user's case; "
            "use waste_rule_preflight after collecting the relevant facts."
        ),
        annotations=_annotations("List supported waste roles and activity identifiers"),
        structured_output=True,
    )
    def waste_rule_catalog() -> dict[str, Any]:
        return catalogue()

    @server.tool(
        description=(
            "FREE EVIDENCE-HEALTH tool. Use only to check whether the reviewed official GOV.UK / Environment Agency evidence "
            "is fresh, unchanged, available and decision-usable. It returns source-health status and never makes a waste-route "
            "or permit conclusion. Do NOT use for operational routing; use waste_rule_preflight or a narrower workflow tool."
        ),
        annotations=_annotations("Check official waste evidence freshness"),
        structured_output=True,
    )
    def waste_source_status() -> dict[str, Any]:
        return source_health()

    @server.tool(
        name="waste_rule_preflight",
        description=(
            "FREE GENERAL ENTRY TOOL for a CURRENT England waste operation when the regulatory route is still uncertain. "
            "Provide nation, role, one or more modelled activities, and any known site/waste/authorisation facts. "
            "Returns a deterministic route, missing facts, findings, evidence and next actions; it is read-only and does not submit anything. "
            "Do NOT use when the question is specifically carrier/broker/dealer registration, DWT receiving-site readiness, or a current-vs-proposed permit change; "
            "use the corresponding narrow tool instead."
        ),
        annotations=_annotations("Run a general England waste-rule preflight"),
        structured_output=True,
    )
    def waste_rule_preflight_tool(scenario: WasteRuleScenario) -> dict[str, Any]:
        return waste_preflight(scenario.model_dump(exclude_none=True))

    @server.tool(
        name="waste_carrier_broker_dealer_preflight",
        description=(
            "FREE CARRIER/BROKER/DEALER REGISTRATION LIFECYCLE tool for England. Select when the unresolved question is a new registration, "
            "renewal, detail/activity change, legal-type change, or lower-to-upper change for a carrier, broker or dealer. "
            "Supply role and lifecycle action, plus own-waste/tier facts when relevant. Returns a bounded route, fee route, findings and official evidence. "
            "It is read-only and never submits or renews a registration. Do NOT use for site permit changes or DWT reporting readiness."
        ),
        annotations=_annotations("Check carrier broker dealer registration lifecycle"),
        structured_output=True,
    )
    def carrier_broker_dealer_registration_preflight_tool(scenario: CarrierRegistrationScenario) -> dict[str, Any]:
        return cbd_preflight(scenario.model_dump(exclude_none=True))

    @server.tool(
        name="waste_digital_tracking_readiness",
        description=(
            "FREE DIGITAL WASTE TRACKING RECEIVING-SITE READINESS tool for England phase 1. Select only when the question is whether a waste receiving site "
            "is in the permitted/licensed receiving-site scope and ready for receipt reporting around the 1 October 2026 mandatory start. "
            "Supply receiving authorisation, whether controlled waste is received, reporting-method readiness, and optionally an as-of date. "
            "Returns phase-1 scope/readiness, findings and evidence; it never submits DWT records. Do NOT use for carrier registration or permit-change comparison."
        ),
        annotations=_annotations("Check Digital Waste Tracking receiving-site readiness"),
        structured_output=True,
    )
    def digital_waste_tracking_receipt_readiness_tool(scenario: DigitalTrackingScenario) -> dict[str, Any]:
        return dwt_readiness(scenario.model_dump(exclude_none=True))

    @server.tool(
        name="waste_permit_change_preflight",
        description=(
            "FREE PERMIT-CHANGE IMPACT PREFLIGHT for an EXISTING England waste operation when both current and proposed operating facts are available. "
            "Compare modelled fields such as location, activities, waste types, quantity, storage, treatment or operating hours. "
            "Returns changed fields, findings, official evidence and review actions; it is read-only and does not vary a permit or decide that a variation/new permit is legally required. "
            "Do NOT use for a brand-new operation route, carrier registration, or DWT receipt-reporting readiness."
        ),
        annotations=_annotations("Screen current versus proposed permit-impact facts"),
        structured_output=True,
    )
    def permit_change_impact(scenario: PermitChangeScenario) -> dict[str, Any]:
        return impact(scenario.model_dump(exclude_none=True))

    return server
