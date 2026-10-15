"""Guided customer answers retain strict Waste facts and reject invalid input."""
from __future__ import annotations

import asyncio
from html.parser import HTMLParser

import httpx
import pytest

from uk_waste_rule_mcp.report_questions import (
    RULE, CARRIER, TRACKING, CHANGE, QuestionFormError, questions_html,
    scenario_from_questions,
)
from uk_waste_rule_mcp.schemas import (
    WasteRuleScenario, CarrierRegistrationScenario, DigitalTrackingScenario, PermitChangeScenario,
)


CASES = [
    (RULE, {"rule__role": "receiver", "activity_receive_waste": "true",
            "rule__waste_types": "cardboard\nwooden pallets", "rule__hazardous_status": "false"},
     WasteRuleScenario),
    (CARRIER, {"carrier__role": "carrier", "carrier__action": "renew",
               "carrier__own_waste_only": "true", "carrier__construction_demolition_waste": "false",
               "carrier__existing_registration_tier": "upper"}, CarrierRegistrationScenario),
    (TRACKING, {"tracking__receiving_authorisation": "permit", "tracking__receives_controlled_waste": "true",
                "tracking__reporting_method_ready": "false", "tracking__as_of_date": "2026-10-04"}, DigitalTrackingScenario),
    (CHANGE, {"current__site_location": "Leeds", "proposed__site_location": "Leeds",
              "proposed__waste_types": "cardboard, wooden pallets"}, PermitChangeScenario),
]


def form_for(workflow, answers):
    return {"workflow": workflow, "form_version": "questions-v1", "scenario__nation": "England",
            "contact_email": "buyer@example.test", **answers}


@pytest.mark.parametrize("workflow,answers,model", CASES)
def test_every_question_workflow_maps_to_existing_strict_schema(workflow, answers, model):
    scenario = scenario_from_questions(form_for(workflow, answers), workflow)
    validated = model.model_validate(scenario).model_dump(exclude_none=True)
    assert validated["nation"] == "England"
    if workflow == RULE:
        assert validated["waste_types"] == ["cardboard", "wooden pallets"]
        assert validated["hazardous_status"] is False
        assert "authorisation_status" not in validated
    elif workflow == CARRIER:
        assert validated["own_waste_only"] is True
        assert validated["construction_demolition_waste"] is False
    elif workflow == TRACKING:
        assert validated["reporting_method_ready"] is False
    else:
        assert "hazardous_status" not in validated["proposed"]
        assert validated["proposed"]["waste_types"] == ["cardboard", "wooden pallets"]


def test_unknown_answers_remain_unknown_without_invented_codes_or_authorisation():
    scenario = scenario_from_questions(form_for(RULE, {"rule__role": "unknown", "activity_unknown": "true"}), RULE)
    assert WasteRuleScenario.model_validate(scenario).model_dump(exclude_none=True) == {"nation": "England", "activities": []}


@pytest.mark.parametrize("role", ["broker", "dealer", "unknown"])
def test_carrier_only_answers_are_ignored_for_other_roles(role):
    scenario = scenario_from_questions(form_for(CARRIER, {"carrier__role": role, "carrier__action": "new_registration",
        "carrier__own_waste_only": "true", "carrier__construction_demolition_waste": "nonsense"}), CARRIER)
    assert "own_waste_only" not in scenario and "construction_demolition_waste" not in scenario


def test_explicit_no_hazardous_waste_counts_as_a_known_permit_fact():
    scenario = scenario_from_questions(form_for(CHANGE, {"current__hazardous_status": "false", "proposed__hazardous_status": "false"}), CHANGE)
    assert scenario["current"] == scenario["proposed"] == {"hazardous_status": False}


@pytest.mark.parametrize("workflow,answers,error_field", [
    (RULE, {"scenario__nation": "Scotland", "rule__role": "receiver", "activity_receive_waste": "true"}, "scenario__nation"),
    (RULE, {"rule__role": "asfadsf", "activity_unknown": "true"}, "rule__role"),
    (RULE, {"rule__role": "receiver"}, "activity_produce_controlled_waste"),
    (RULE, {"rule__role": "receiver", "activity_receive_waste": "true", "activity_unknown": "true"}, "activity_unknown"),
    (RULE, {"rule__role": "receiver", "activity_unknown": "true", "rule__site_location": "x" * 1001}, "rule__site_location"),
    (RULE, {"rule__role": "receiver", "activity_unknown": "true", "rule__waste_types": "x" * 2001}, "rule__waste_types"),
    (CARRIER, {"carrier__role": "producer", "carrier__action": "renew"}, "carrier__role"),
    (CARRIER, {"carrier__role": "carrier", "carrier__action": "unknown"}, "carrier__action"),
    (TRACKING, {"tracking__as_of_date": "2026-02-30"}, "tracking__as_of_date"),
    (TRACKING, {"tracking__as_of_date": "20261004"}, "tracking__as_of_date"),
    (CHANGE, {"proposed__site_location": "Leeds"}, "current__site_location"),
    (CHANGE, {"current__site_location": "Leeds"}, "proposed__site_location"),
])
def test_bad_answers_have_a_specific_field_and_correction(workflow, answers, error_field):
    with pytest.raises(QuestionFormError) as caught:
        scenario_from_questions(form_for(workflow, answers), workflow)
    assert error_field in caught.value.fields.values()
    assert caught.value.messages


class Controls(HTMLParser):
    def __init__(self):
        super().__init__()
        self.controls = []

    def handle_starttag(self, tag, attrs):
        if tag in {"input", "select", "textarea"}:
            self.controls.append(dict(attrs))


@pytest.mark.parametrize("workflow,answers,model", CASES)
def test_inactive_question_controls_are_disabled_and_json_is_not_required(workflow, answers, model):
    markup = questions_html(workflow, form_for(workflow, answers))
    controls = Controls()
    controls.feed(markup)
    prefixes = {RULE: "rule__", CARRIER: "carrier__", TRACKING: "tracking__", CHANGE: "current__"}
    for control in controls.controls:
        name = control.get("name", "")
        inactive = any(name.startswith(prefix) for key, prefix in prefixes.items() if key != workflow)
        if name.startswith("proposed__") and workflow != CHANGE:
            inactive = True
        if name.startswith("activity_") and workflow != RULE:
            inactive = True
        if inactive:
            assert "disabled" in control
    assert not any(control.get("name") == "payload" for control in controls.controls)


@pytest.fixture
def customer_checkout(monkeypatch, tmp_path):
    from starlette.applications import Starlette
    from uk_waste_rule_mcp import production_bridge as bridge
    from uk_waste_rule_mcp.commercial import PendingWasteReportStore

    class FakeCommercial:
        def __init__(self):
            self.calls = []

        async def create_report_checkout(self, **kwargs):
            self.calls.append(kwargs)
            return {"checkout_id": "co_guided", "stripe_session_id": "cs_test_guided",
                    "checkout_url": "https://checkout.stripe.test/guided", "report_claim_token": "local-claim"}

    fake = FakeCommercial()
    store = PendingWasteReportStore(tmp_path / "guided-reports.json")
    monkeypatch.setattr(bridge, "COMMERCIAL_CLIENT", fake)
    monkeypatch.setattr(bridge, "REPORT_CHECKOUTS", store)
    monkeypatch.setattr(bridge, "PUBLIC_ORIGIN", "https://waste.example.test")
    app = Starlette(routes=bridge.build_server()._custom_starlette_routes)

    def post(answers):
        async def run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://waste.example.test") as client:
                return await client.post("/waste-report/checkout", data=answers, follow_redirects=False)
        return asyncio.run(run())

    return post, fake, store


@pytest.mark.parametrize("workflow,answers,model", CASES)
def test_every_guided_form_starts_checkout_with_validated_facts(customer_checkout, workflow, answers, model):
    post, fake, store = customer_checkout
    response = post(form_for(workflow, answers))
    assert response.status_code == 303
    assert response.headers["location"] == "https://checkout.stripe.test/guided"
    assert len(fake.calls) == 1
    row = store.get_by_checkout_id("co_guided")
    assert row["workflow"] == workflow
    assert row["payload"] == model.model_validate(scenario_from_questions(form_for(workflow, answers), workflow)).model_dump(exclude_none=True)


def test_invalid_guided_form_preserves_answers_and_does_not_start_checkout(customer_checkout):
    post, fake, _ = customer_checkout
    answers = {"rule__role": "receiver", "activity_receive_waste": "true", "activity_unknown": "true",
               "rule__site_location": '<script>alert("x")</script>', "rule__waste_types": "cardboard\nwooden pallets"}
    response = post(form_for(RULE, answers))
    assert response.status_code == 422
    assert not fake.calls
    assert "Please correct" in response.text
    assert 'data-field="activity_unknown"' in response.text
    assert "cardboard\nwooden pallets" in response.text
    assert '<script>alert("x")</script>' not in response.text
    assert "&lt;script&gt;" in response.text
    assert 'value="buyer@example.test"' in response.text


@pytest.mark.parametrize("email", ["@example.test", "buyer@", "buyer", "a b@example.test", "a@@example.test"])
def test_invalid_email_is_explained_before_creating_a_checkout(customer_checkout, email):
    post, fake, _ = customer_checkout
    response = post(form_for(RULE, {"rule__role": "receiver", "activity_receive_waste": "true", "contact_email": email}))
    assert response.status_code == 422
    assert not fake.calls
    assert "Checkout email: enter a valid email address" in response.text
