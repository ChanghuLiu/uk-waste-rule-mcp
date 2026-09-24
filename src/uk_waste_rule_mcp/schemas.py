"""Shared strict input schemas for public-AI and commercial Waste MCP tools."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WasteRuleScenario(StrictModel):
    nation: Literal["England"] | None = Field(
        default=None,
        description="UK nation for the operation. This service currently supports England only and never infers jurisdiction.",
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


class CarrierRegistrationScenario(StrictModel):
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


class DigitalTrackingScenario(StrictModel):
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


class PermitOperationFacts(StrictModel):
    site_location: str | None = Field(default=None, description="Current or proposed site location.")
    activities: list[str] | None = Field(default=None, description="Current or proposed waste activities.")
    waste_types: list[str] | str | None = Field(default=None, description="Current or proposed user-supplied waste types/codes.")
    hazardous_status: bool | None = Field(default=None, description="Known hazardous-waste status; never infer it.")
    maximum_quantity: str | int | float | None = Field(default=None, description="Current or proposed maximum quantity, preserving the user's unit/context.")
    storage_method: str | None = Field(default=None, description="Current or proposed storage method.")
    treatment_method: str | None = Field(default=None, description="Current or proposed treatment method.")
    operating_hours: str | None = Field(default=None, description="Current or proposed operating hours.")


class PermitChangeScenario(StrictModel):
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
