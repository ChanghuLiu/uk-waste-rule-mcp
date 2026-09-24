"""Conservative, evidence-linked waste-rule screening for England.

This MVP deliberately routes ambiguous or incomplete fact patterns to review.
It does not determine permit eligibility, approve operations, or submit data.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .monitor import source_health
from .sources import source_registry

PRODUCT = "UK Waste Rule & Permit Change-Impact MCP"
SUPPORTED_NATIONS = {"england"}

ROLES: dict[str, str] = {
    "producer": "A business producing controlled waste",
    "carrier": "A business transporting waste",
    "broker": "A business arranging waste transport or disposal",
    "dealer": "A business buying or selling waste",
    "receiver": "A site receiving waste under a permit, licence or other authorisation",
    "operator": "A site operating a waste storage, treatment, disposal or recovery activity",
}

ACTIVITIES: dict[str, dict[str, Any]] = {
    "produce_controlled_waste": {
        "label": "Produce controlled waste",
        "route": "DUTY_OF_CARE_REVIEW",
        "source_ids": ["govuk-waste-duty-of-care"],
    },
    "transport_waste": {
        "label": "Transport waste",
        "route": "CARRIER_REGISTRATION_AND_DUTY_OF_CARE_REVIEW",
        "source_ids": ["govuk-cbd-registration", "govuk-waste-duty-of-care"],
    },
    "arrange_waste": {
        "label": "Arrange transport or disposal of waste",
        "route": "BROKER_OR_DEALER_AND_DUTY_OF_CARE_REVIEW",
        "source_ids": ["govuk-cbd-registration", "govuk-waste-duty-of-care"],
    },
    "receive_waste": {
        "label": "Receive waste at a site",
        "route": "PERMIT_OR_EXEMPTION_AND_DIGITAL_TRACKING_REVIEW",
        "source_ids": ["govuk-environmental-permits", "govuk-waste-environmental-permits", "govuk-waste-exemptions", "govuk-digital-waste-tracking-service"],
    },
    "store_waste": {
        "label": "Store waste",
        "route": "PERMIT_OR_EXEMPTION_REVIEW",
        "source_ids": ["govuk-environmental-permits", "govuk-waste-environmental-permits", "govuk-waste-exemptions"],
    },
    "treat_recover_dispose_waste": {
        "label": "Treat, recover or dispose of waste",
        "route": "PERMIT_OR_EXEMPTION_REVIEW",
        "source_ids": ["govuk-environmental-permits", "govuk-waste-environmental-permits", "govuk-waste-exemptions"],
    },
}

CBD_ROLES = {"carrier", "broker", "dealer"}
DWT_MANDATORY_ENGLAND = date(2026, 10, 1)


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _finding(code: str, severity: str, status: str, message: str, source_ids: list[str] | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "status": status,
        "message": message,
        "source_ids": source_ids or [],
    }


def _source_subset(ids: set[str]) -> list[dict[str, Any]]:
    return [source for source in source_registry() if source["id"] in ids]


def _source_gate(ids: set[str]) -> dict[str, Any]:
    selected = [source for source in source_registry() if source["id"] in ids]
    health = source_health(selected)
    return health


def list_waste_rules() -> dict[str, Any]:
    return {
        "product": PRODUCT,
        "scope": "England only",
        "roles": [{"id": key, "label": value} for key, value in ROLES.items()],
        "activities": [
            {"id": key, "label": value["label"], "route": value["route"], "source_ids": value["source_ids"]}
            for key, value in ACTIVITIES.items()
        ],
        "note": "This catalogue routes fact patterns for review; it does not decide permit eligibility or statutory exemptions.",
    }


def classify_waste_route(scenario: dict[str, Any]) -> dict[str, Any]:
    nation = _norm(scenario.get("nation", ""))
    role = _norm(scenario.get("role", ""))
    activities = [_norm(item) for item in scenario.get("activities", []) if _norm(item)]
    unknown = [item for item in activities if item not in ACTIVITIES]

    if not nation:
        return {"route": "MISSING_NATION", "status": "REVIEW_REQUIRED", "reason": "The UK nation is required; the engine does not infer jurisdiction."}
    if nation not in SUPPORTED_NATIONS:
        return {"route": "OUT_OF_SCOPE", "status": "REVIEW_REQUIRED", "reason": "This MVP covers England only."}
    if not role:
        return {"route": "MISSING_ROLE", "status": "REVIEW_REQUIRED", "reason": "The operator role is required; the engine does not infer producer, carrier, broker, dealer, receiver or operator status."}
    if role not in ROLES:
        return {"route": "UNKNOWN_ROLE", "status": "REVIEW_REQUIRED", "reason": "The supplied role is not modelled; no registration or permit conclusion is inferred."}
    if unknown:
        return {"route": "UNKNOWN_ACTIVITY", "status": "REVIEW_REQUIRED", "reason": "One or more activity identifiers are not modelled; no regulatory conclusion is inferred."}
    if not activities:
        return {"route": "NO_ACTIVITY_IDENTIFIED", "status": "REVIEW_REQUIRED", "reason": "At least one waste activity is required for routing."}
    routes = {ACTIVITIES[item]["route"] for item in activities}
    if "PERMIT_OR_EXEMPTION_AND_DIGITAL_TRACKING_REVIEW" in routes:
        route = "PERMIT_OR_EXEMPTION_AND_DIGITAL_TRACKING_REVIEW"
    elif "PERMIT_OR_EXEMPTION_REVIEW" in routes:
        route = "PERMIT_OR_EXEMPTION_REVIEW"
    elif len(routes) == 1:
        route = next(iter(routes))
    else:
        route = "COMBINED_WASTE_OBLIGATIONS_REVIEW"
    return {"route": route, "status": "REVIEW_REQUIRED", "reason": "The activity is routed to a bounded regulatory preflight; this result is not a permit, exemption or registration decision."}


def _changed_fields(current: dict[str, Any], proposed: dict[str, Any]) -> list[str]:
    fields = ("site_location", "activities", "waste_types", "hazardous_status", "maximum_quantity", "storage_method", "treatment_method", "operating_hours")
    return [field for field in fields if current.get(field) != proposed.get(field)]


def permit_change_impact(scenario: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(scenario, dict):
        raise TypeError("scenario must be an object")
    nation = _norm(scenario.get("nation", ""))
    source_ids = {"govuk-environmental-permits", "govuk-waste-environmental-permits", "govuk-waste-exemptions"}
    findings: list[dict[str, Any]] = []
    source_gate = _source_gate(source_ids)
    if not source_gate["decision_usable"]:
        findings.append(_finding("SOURCE-001", "blocking", "review_required", "One or more official sources are missing a current unchanged fingerprint or are stale; no permit-change conclusion is returned.", sorted(source_ids)))
    if not nation:
        findings.append(_finding("SCOPE-001", "blocking", "missing", "The UK nation is required; the engine does not infer jurisdiction.", ["govuk-environmental-permits"]))
    elif nation not in SUPPORTED_NATIONS:
        findings.append(_finding("SCOPE-001", "blocking", "review_required", "This MVP covers England only.", ["govuk-environmental-permits"]))
    current = scenario.get("current")
    proposed = scenario.get("proposed")
    if not isinstance(current, dict) or not isinstance(proposed, dict):
        findings.append(_finding("CHANGE-001", "blocking", "missing", "Provide both current and proposed operation facts; the engine does not infer a change from a description alone.", list(source_ids)))
        status = "INCOMPLETE"
        changed: list[str] = []
    else:
        changed = _changed_fields(current, proposed)
        if not changed:
            findings.append(_finding("CHANGE-002", "info", "no_change_identified", "No modelled operational field changed between the current and proposed facts.", list(source_ids)))
            status = "REVIEW_REQUIRED"
        else:
            findings.append(_finding("CHANGE-003", "blocking", "review_required", "A modelled operational change may affect permit, exemption or management-system obligations; obtain a route-specific review.", list(source_ids)))
            status = "REVIEW_REQUIRED"
    if any(item["status"] == "missing" for item in findings):
        status = "INCOMPLETE"
    elif not source_gate["decision_usable"]:
        status = "REVIEW_REQUIRED"
    return {
        "product": PRODUCT,
        "schema_version": "0.1",
        "generated_on": date.today().isoformat(),
        "decision": {
            "route": "PERMIT_CHANGE_IMPACT",
            "status": status,
            "deterministic": True,
            "changed_fields": changed,
        },
        "findings": findings,
        "source_health": source_gate,
        "evidence": _source_subset(source_ids),
        "next_actions": [
            "Compare the proposed activity against the current permit, exemption and management-system conditions.",
            "Confirm the route with the relevant regulator or qualified environmental adviser before operating the change.",
        ],
        "limitations": [
            "This MVP does not decide whether a variation, new permit, exemption or registration is legally required.",
            "Hazardous waste classification, POPs, waste codes, quantity thresholds and permit conditions require fact-specific review.",
        ],
    }


def waste_preflight(scenario: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(scenario, dict):
        raise TypeError("scenario must be an object")
    nation = _norm(scenario.get("nation", ""))
    role = _norm(scenario.get("role", ""))
    activities = [_norm(item) for item in scenario.get("activities", []) if _norm(item)]
    route = classify_waste_route(scenario)
    findings: list[dict[str, Any]] = []
    source_ids: set[str] = set()
    for activity in activities:
        if activity in ACTIVITIES:
            source_ids.update(ACTIVITIES[activity]["source_ids"])
    if not source_ids:
        source_ids.update({"govuk-environmental-permits", "govuk-waste-environmental-permits", "govuk-waste-duty-of-care"})
    source_gate = _source_gate(source_ids)
    if not source_gate["decision_usable"]:
        findings.append(_finding("SOURCE-001", "blocking", "review_required", "One or more official sources are missing a current unchanged fingerprint or are stale; no regulatory conclusion is returned.", sorted(source_ids)))

    if route["route"] == "MISSING_NATION":
        findings.append(_finding("SCOPE-001", "blocking", "missing", route["reason"], ["govuk-environmental-permits"]))
    elif route["route"] == "OUT_OF_SCOPE":
        findings.append(_finding("SCOPE-001", "blocking", "review_required", route["reason"], ["govuk-environmental-permits"]))
    elif route["route"] == "MISSING_ROLE":
        findings.append(_finding("ROLE-002", "blocking", "missing", route["reason"], ["govuk-waste-duty-of-care", "govuk-environmental-permits"]))
    elif route["route"] == "UNKNOWN_ROLE":
        findings.append(_finding("ROLE-001", "blocking", "unknown", route["reason"]))
    elif route["route"] == "UNKNOWN_ACTIVITY":
        findings.append(_finding("ACTIVITY-001", "blocking", "unknown", route["reason"]))
    elif route["route"] == "NO_ACTIVITY_IDENTIFIED":
        findings.append(_finding("ACTIVITY-002", "blocking", "missing", route["reason"], ["govuk-environmental-permits"]))
    else:
        findings.append(_finding("ROUTE-001", "info", "identified", route["reason"], sorted(source_ids)))

    if route["route"] not in {"MISSING_NATION", "OUT_OF_SCOPE", "MISSING_ROLE", "UNKNOWN_ROLE", "UNKNOWN_ACTIVITY", "NO_ACTIVITY_IDENTIFIED"}:
        required = (("site_location", "Provide the site location or a sufficiently precise operating location."), ("waste_types", "Provide the waste types or codes being handled."), ("hazardous_status", "State whether hazardous waste may be involved; do not infer this from the activity name."))
        for field, message in required:
            if scenario.get(field) in (None, "", []):
                findings.append(_finding(f"FACT-{field.upper()}", "blocking", "missing", message, sorted(source_ids)))
        if role in {"receiver", "operator"} and scenario.get("authorisation_status") in (None, ""):
            findings.append(_finding("AUTH-001", "blocking", "missing", "State whether the site currently relies on a permit, exemption, licence or no authorisation; the route is not inferred.", ["govuk-environmental-permits", "govuk-waste-environmental-permits", "govuk-waste-exemptions"]))
        if "receive_waste" in activities:
            source_ids.add("govuk-digital-waste-tracking-service")
            findings.append(_finding("DWT-001", "warning", "review_required", "Receiving-site digital tracking scope and reporting readiness require a separate fact and timeline check.", ["govuk-digital-waste-tracking-service", "govuk-report-receipt-of-waste"]))
        if role in {"carrier", "broker", "dealer"} or any(item in {"transport_waste", "arrange_waste"} for item in activities):
            findings.append(_finding("DUTY-001", "warning", "review_required", "Confirm the applicable carrier/broker/dealer registration and duty-of-care controls for the supplied role.", ["govuk-waste-duty-of-care"]))

    blocking = [item for item in findings if item["severity"] == "blocking" and item["status"] in {"missing", "unknown", "failed", "not_confirmed"}]
    status = "INCOMPLETE" if blocking else "SCREENING_COMPLETE_REVIEW_REQUIRED"
    if route["route"] in {"OUT_OF_SCOPE", "UNKNOWN_ROLE", "UNKNOWN_ACTIVITY", "NO_ACTIVITY_IDENTIFIED"}:
        status = "REVIEW_REQUIRED"
    elif not source_gate["decision_usable"] and status != "INCOMPLETE":
        status = "REVIEW_REQUIRED"
    return {
        "product": PRODUCT,
        "schema_version": "0.1",
        "generated_on": date.today().isoformat(),
        "scope": "England only; official-source-linked regulatory routing, not legal advice or an operating approval.",
        "decision": {"route": route["route"], "status": status, "conclusion": route["reason"], "deterministic": True},
        "normalised_input": {"nation": nation or None, "role": role or None, "activities": activities},
        "findings": findings,
        "source_health": source_gate,
        "evidence": _source_subset(source_ids),
        "next_actions": [
            "Confirm the exact regulator route and current source conditions before operating or changing the activity.",
            "Do not treat this preflight as a permit, exemption, registration, approval or legal advice.",
        ],
        "limitations": [
            "This MVP does not submit Digital Waste Tracking data or replace operational waste-management software.",
            "No hazardous-waste, POPs, EWC-code, quantity-threshold or permit-condition conclusion is inferred from incomplete facts.",
        ],
    }


def carrier_broker_dealer_registration_preflight(scenario: dict[str, Any]) -> dict[str, Any]:
    """Preflight England waste carrier/broker/dealer registration and lifecycle actions.

    This deliberately does not infer registration tier from an incomplete fact pattern.
    """
    if not isinstance(scenario, dict):
        raise TypeError("scenario must be an object")

    source_ids = {"govuk-cbd-registration", "govuk-waste-duty-of-care"}
    gate = _source_gate(source_ids)
    findings: list[dict[str, Any]] = []
    nation = _norm(scenario.get("nation"))
    role = _norm(scenario.get("role"))
    action = _norm(scenario.get("action") or "new_registration")
    own_waste_only = scenario.get("own_waste_only")
    construction_demolition = scenario.get("construction_demolition_waste")
    existing_tier = _norm(scenario.get("existing_registration_tier"))

    if not gate["decision_usable"]:
        findings.append(_finding(
            "SOURCE-001", "blocking", "review_required",
            "One or more official carrier/broker/dealer sources are stale, changed, unavailable or unreviewed; the decision is withheld.",
            sorted(source_ids),
        ))

    if not nation:
        findings.append(_finding("SCOPE-001", "blocking", "missing", "The UK nation is required.", ["govuk-cbd-registration"]))
    elif nation != "england":
        findings.append(_finding("SCOPE-001", "blocking", "review_required", "This workflow currently covers England only.", ["govuk-cbd-registration"]))

    if not role:
        findings.append(_finding("CBD-ROLE-001", "blocking", "missing", "Specify carrier, broker or dealer.", ["govuk-cbd-registration"]))
    elif role not in CBD_ROLES:
        findings.append(_finding("CBD-ROLE-002", "blocking", "unknown", "This workflow is only for carrier, broker or dealer registration.", ["govuk-cbd-registration"]))

    registration_required: bool | None = None
    price_route = "REVIEW_REQUIRED"
    if role in CBD_ROLES and nation == "england":
        registration_required = True
        findings.append(_finding(
            "CBD-REG-001", "info", "required",
            "Businesses that transport waste, deal in waste, or broker waste movements must use the carrier/broker/dealer registration route in England.",
            ["govuk-cbd-registration"],
        ))
        if role == "carrier":
            if own_waste_only is None:
                findings.append(_finding(
                    "CBD-FACT-001", "blocking", "missing",
                    "State whether the carrier transports only waste it produces itself; this affects the current fee/tier route.",
                    ["govuk-cbd-registration"],
                ))
            elif bool(own_waste_only):
                if construction_demolition is None:
                    findings.append(_finding(
                        "CBD-FACT-002", "blocking", "missing",
                        "For an own-waste carrier, state whether construction or demolition waste is carried.",
                        ["govuk-cbd-registration"],
                    ))
                elif bool(construction_demolition):
                    price_route = "STANDARD_REGISTRATION_FEE_ROUTE"
                else:
                    price_route = "OWN_WASTE_USUALLY_FREE_ROUTE"
            else:
                price_route = "STANDARD_REGISTRATION_FEE_ROUTE"
        else:
            price_route = "STANDARD_REGISTRATION_FEE_ROUTE"

    lifecycle = {
        "new_registration": "NEW_REGISTRATION",
        "renew": "RENEWAL",
        "change_details": "UPDATE_WITHIN_28_DAYS",
        "change_activity": "ACTIVITY_CHANGE",
        "change_legal_type": "NEW_REGISTRATION_REQUIRED",
        "lower_to_upper": "NEW_REGISTRATION_REQUIRED",
    }.get(action, "UNKNOWN_ACTION")

    if lifecycle == "UNKNOWN_ACTION":
        findings.append(_finding(
            "CBD-ACTION-001", "blocking", "unknown",
            "Supported actions are new_registration, renew, change_details, change_activity, change_legal_type and lower_to_upper.",
            ["govuk-cbd-registration"],
        ))
    elif action == "renew" and existing_tier:
        if existing_tier == "upper":
            findings.append(_finding(
                "CBD-RENEW-001", "info", "required",
                "Upper-tier registrations are renewed every 3 years.",
                ["govuk-cbd-registration"],
            ))
        elif existing_tier == "lower":
            findings.append(_finding(
                "CBD-RENEW-002", "info", "not_required",
                "The current GOV.UK registration page says lower-tier registration does not require renewal.",
                ["govuk-cbd-registration"],
            ))
        else:
            findings.append(_finding("CBD-TIER-001", "blocking", "unknown", "Unknown registration tier.", ["govuk-cbd-registration"]))
    elif action == "renew" and not existing_tier:
        findings.append(_finding("CBD-TIER-002", "blocking", "missing", "Provide existing_registration_tier for a renewal decision.", ["govuk-cbd-registration"]))

    blocking = [
        item for item in findings
        if item["severity"] == "blocking" and item["status"] in {"missing", "unknown"}
    ]
    if blocking:
        status = "INCOMPLETE"
    elif not gate["decision_usable"] or nation != "england":
        status = "REVIEW_REQUIRED"
    else:
        status = "SCREENING_COMPLETE"

    return {
        "product": PRODUCT,
        "schema_version": "0.2",
        "generated_on": date.today().isoformat(),
        "decision": {
            "route": "CARRIER_BROKER_DEALER_REGISTRATION",
            "status": status,
            "deterministic": True,
            "registration_required": registration_required,
            "role": role or None,
            "action": lifecycle,
            "fee_route": price_route,
        },
        "current_published_fees_gbp": {
            "standard_registration": 191.02,
            "upper_tier_renewal": 130.25,
            "change_activity": 49.62,
            "note": "Fee values are returned only with the current reviewed official source and must not be cached as permanent statutory amounts.",
        } if gate["decision_usable"] else None,
        "findings": findings,
        "source_health": gate,
        "evidence": _source_subset(source_ids),
        "next_actions": [
            "Use the Environment Agency registration service for the applicable carrier, broker or dealer lifecycle action.",
            "Confirm the registration tier shown by the official service; this preflight does not independently assign legal tier status.",
        ],
        "limitations": [
            "This service does not submit or renew a registration.",
            "It does not determine environmental-offence eligibility or replace an Environment Agency decision.",
        ],
    }


def digital_waste_tracking_receipt_readiness(scenario: dict[str, Any]) -> dict[str, Any]:
    """Check phase-1 Digital Waste Tracking readiness for England receiving sites."""
    if not isinstance(scenario, dict):
        raise TypeError("scenario must be an object")

    source_ids = {"govuk-digital-waste-tracking-service", "govuk-report-receipt-of-waste"}
    gate = _source_gate(source_ids)
    findings: list[dict[str, Any]] = []
    nation = _norm(scenario.get("nation"))
    authorisation = _norm(scenario.get("receiving_authorisation"))
    receives_controlled = scenario.get("receives_controlled_waste")
    reporting_ready = scenario.get("reporting_method_ready")

    raw_as_of = scenario.get("as_of_date")
    if raw_as_of:
        try:
            as_of = date.fromisoformat(str(raw_as_of))
        except ValueError:
            as_of = date.today()
            findings.append(_finding("DWT-DATE-001", "blocking", "unknown", "as_of_date must use YYYY-MM-DD.", sorted(source_ids)))
    else:
        as_of = date.today()

    if not gate["decision_usable"]:
        findings.append(_finding(
            "SOURCE-001", "blocking", "review_required",
            "Digital Waste Tracking evidence is stale, changed, unavailable or unreviewed; the readiness decision is withheld.",
            sorted(source_ids),
        ))
    if not nation:
        findings.append(_finding("SCOPE-001", "blocking", "missing", "The UK nation is required.", sorted(source_ids)))
    elif nation != "england":
        findings.append(_finding("SCOPE-001", "blocking", "review_required", "This workflow currently models England phase-1 timing only.", sorted(source_ids)))

    phase1_in_scope: bool | None = None
    requirement = "REVIEW_REQUIRED"
    if nation == "england":
        if receives_controlled is None:
            findings.append(_finding("DWT-FACT-001", "blocking", "missing", "State whether the site receives controlled waste.", sorted(source_ids)))
        elif not bool(receives_controlled):
            phase1_in_scope = False
            requirement = "NO_CONTROLLED_WASTE_RECEIPT_IDENTIFIED"
        elif not authorisation:
            findings.append(_finding("DWT-FACT-002", "blocking", "missing", "State the receiving-site authorisation: permit, licence, exemption or other.", sorted(source_ids)))
        elif authorisation in {"permit", "permitted", "licence", "licensed"}:
            phase1_in_scope = True
            requirement = "MANDATORY" if as_of >= DWT_MANDATORY_ENGLAND else "PREPARE_FOR_MANDATORY_START"
            findings.append(_finding(
                "DWT-SCOPE-001", "info", "required" if as_of >= DWT_MANDATORY_ENGLAND else "upcoming",
                "England permitted or licensed waste receiving sites are in phase 1 of mandatory Digital Waste Tracking from 1 October 2026.",
                sorted(source_ids),
            ))
            if reporting_ready is not True:
                findings.append(_finding(
                    "DWT-READY-001", "blocking", "missing" if reporting_ready is None else "not_confirmed",
                    "Confirm a reporting route is operational before the mandatory start or before relying on this readiness result.",
                    sorted(source_ids),
                ))
        elif authorisation in {"exemption", "registered_exemption"}:
            phase1_in_scope = False
            requirement = "NOT_INCLUDED_IN_PHASE_1_CURRENT_MODEL"
            findings.append(_finding(
                "DWT-SCOPE-002", "warning", "review_required",
                "Current GOV.UK phase-1 guidance distinguishes permitted/licensed receiving sites from registered exemptions; keep later-phase changes under review.",
                ["govuk-digital-waste-tracking-service"],
            ))
        else:
            findings.append(_finding("DWT-AUTH-001", "blocking", "unknown", "Unsupported receiving authorisation value.", sorted(source_ids)))

    blocking = [
        item for item in findings
        if item["severity"] == "blocking" and item["status"] in {"missing", "unknown", "not_confirmed"}
    ]
    if blocking:
        status = "INCOMPLETE"
    elif not gate["decision_usable"] or nation != "england":
        status = "REVIEW_REQUIRED"
    else:
        status = "SCREENING_COMPLETE"

    return {
        "product": PRODUCT,
        "schema_version": "0.2",
        "generated_on": date.today().isoformat(),
        "decision": {
            "route": "DIGITAL_WASTE_TRACKING_RECEIPT_READINESS",
            "status": status,
            "deterministic": True,
            "phase1_in_scope": phase1_in_scope,
            "requirement": requirement,
            "mandatory_from": DWT_MANDATORY_ENGLAND.isoformat(),
            "as_of_date": as_of.isoformat(),
            "reporting_timing": "Report each received load within 2 working days, starting the day after receipt, when the mandatory receiving-site rule applies.",
        },
        "findings": findings,
        "source_health": gate,
        "evidence": _source_subset(source_ids),
        "next_actions": [
            "Confirm the receiving-site authorisation and whether controlled waste is received.",
            "Prepare either the receipt-of-waste API or the supported spreadsheet route before the mandatory date if the site is in scope.",
            "Continue monitoring later Digital Waste Tracking phases for exemptions and collectors.",
        ],
        "limitations": [
            "This workflow does not submit Digital Waste Tracking records.",
            "It does not classify waste, generate waste codes or calculate permit conditions.",
        ],
    }
