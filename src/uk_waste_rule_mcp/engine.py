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
        "source_ids": ["govuk-waste-duty-of-care"],
    },
    "arrange_waste": {
        "label": "Arrange transport or disposal of waste",
        "route": "BROKER_OR_DEALER_AND_DUTY_OF_CARE_REVIEW",
        "source_ids": ["govuk-waste-duty-of-care"],
    },
    "receive_waste": {
        "label": "Receive waste at a site",
        "route": "PERMIT_OR_EXEMPTION_AND_DIGITAL_TRACKING_REVIEW",
        "source_ids": ["govuk-environmental-permits", "govuk-waste-exemptions", "govuk-digital-waste-tracking-service"],
    },
    "store_waste": {
        "label": "Store waste",
        "route": "PERMIT_OR_EXEMPTION_REVIEW",
        "source_ids": ["govuk-environmental-permits", "govuk-waste-exemptions"],
    },
    "treat_recover_dispose_waste": {
        "label": "Treat, recover or dispose of waste",
        "route": "PERMIT_OR_EXEMPTION_REVIEW",
        "source_ids": ["govuk-environmental-permits", "govuk-waste-exemptions"],
    },
}


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
    source_ids = {"govuk-environmental-permits", "govuk-waste-exemptions"}
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
        source_ids.update({"govuk-environmental-permits", "govuk-waste-duty-of-care"})
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
            findings.append(_finding("AUTH-001", "blocking", "missing", "State whether the site currently relies on a permit, exemption, licence or no authorisation; the route is not inferred.", ["govuk-environmental-permits", "govuk-waste-exemptions"]))
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
