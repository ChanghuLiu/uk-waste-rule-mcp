"""Human questions mapped to the existing Waste scenario schemas."""
from __future__ import annotations

from datetime import date
from html import escape
import re

from .form_feedback import bind_form_values


RULE = "waste_rule_preflight"
CARRIER = "waste_carrier_broker_dealer_preflight"
TRACKING = "waste_digital_tracking_readiness"
CHANGE = "waste_permit_change_preflight"
WORKFLOWS = (RULE, CARRIER, TRACKING, CHANGE)
ROLES = (
    ("producer", "We produce waste"), ("carrier", "We transport waste"),
    ("broker", "We arrange waste transport or disposal"), ("dealer", "We buy or sell waste"),
    ("receiver", "Our site receives waste"), ("operator", "We operate a waste site"),
)
ACTIVITIES = (
    ("produce_controlled_waste", "Produce waste"), ("transport_waste", "Transport waste"),
    ("arrange_waste", "Arrange waste transport or disposal"), ("receive_waste", "Receive waste at a site"),
    ("store_waste", "Store waste"), ("treat_recover_dispose_waste", "Treat, recover or dispose of waste"),
)
AUTHORISATIONS = (
    ("permit", "Environmental permit"), ("exemption", "Registered waste exemption"),
    ("licence", "Waste licence"), ("none", "No current authorisation"), ("other", "Other authorisation"),
)
ACTIONS = (
    ("new_registration", "Apply for a new registration"), ("renew", "Renew an existing registration"),
    ("change_details", "Update registration details"), ("change_activity", "Change registered activities"),
    ("change_legal_type", "Change the legal type of the business"), ("lower_to_upper", "Move from lower tier to upper tier"),
)
YES_NO = (("true", "Yes"), ("false", "No"), ("unknown", "Not sure"))
LABELS = {
    "scenario__nation": "Where does the operation take place?",
    "rule__role": "What is your main waste role?",
    "rule__site_location": "Where do you operate?",
    "rule__waste_types": "What waste do you handle?",
    "rule__hazardous_status": "Is hazardous waste involved?",
    "rule__authorisation_status": "What authorisation does the site currently have?",
    "carrier__role": "Which registration role are you checking?",
    "carrier__action": "What do you want to do?",
    "carrier__own_waste_only": "Do you transport only waste produced by your own business?",
    "carrier__construction_demolition_waste": "Does that waste include construction or demolition waste?",
    "carrier__existing_registration_tier": "What is your existing registration tier?",
    "tracking__receiving_authorisation": "What authorisation does the receiving site have?",
    "tracking__receives_controlled_waste": "Does the site receive controlled waste?",
    "tracking__reporting_method_ready": "Is your receipt-reporting method operational?",
    "tracking__as_of_date": "Assessment date",
}
OPERATION_FIELDS = (
    ("site_location", "Site location", "e.g. Leeds"),
    ("activities", "Waste activities", "e.g. storing waste\nSorting recyclable material"),
    ("waste_types", "Waste types or known waste codes", "e.g. cardboard packaging\nUsed wooden pallets"),
    ("hazardous_status", "Is hazardous waste involved?", ""),
    ("maximum_quantity", "Maximum quantity, including units", "e.g. 50 tonnes per week"),
    ("storage_method", "Storage method", "e.g. covered containers"),
    ("treatment_method", "Treatment method", "e.g. sorting by hand"),
    ("operating_hours", "Operating hours", "e.g. Monday–Friday, 08:00–17:00"),
)
for _side in ("current", "proposed"):
    for _field, _label, _ in OPERATION_FIELDS:
        LABELS[f"{_side}__{_field}"] = ("Current operation — " if _side == "current" else "Proposed operation — ") + _label


class QuestionFormError(ValueError):
    def __init__(self, errors, fields):
        self.messages = errors
        self.fields = fields
        super().__init__(" ".join(errors))


def _select(name, options, *, required=False, unknown=True, hint=""):
    title = LABELS[name]
    body = '<option value="">Choose an option</option>' if required else '<option value="">Not sure</option>'
    body += ''.join('<option value="' + escape(value, quote=True) + '">' + escape(label) + '</option>' for value, label in options if required or value != "unknown")
    if required and unknown:
        body += '<option value="unknown">Not sure</option>'
    help_id = name + '-help'
    return ('<div class="field"><label for="' + name + '">' + escape(title) + '</label><select id="' + name + '" name="' + name + '"' +
            (' required' if required else '') + (' aria-describedby="' + help_id + '"' if hint else '') + '>' + body + '</select>' +
            ('<p class="helper" id="' + help_id + '">' + escape(hint) + '</p>' if hint else '') + '</div>')


def _text(name, *, label=None, placeholder="", multiline=False, hint="", kind="text", maxlength=1000):
    title = label or LABELS[name]
    attrs = ' id="' + name + '" name="' + name + '" maxlength="' + str(maxlength) + '"'
    if placeholder:
        attrs += ' placeholder="' + escape(placeholder, quote=True) + '"'
    if hint:
        attrs += ' aria-describedby="' + name + '-help"'
    control = '<textarea class="question-text" rows="3"' + attrs + '></textarea>' if multiline else '<input type="' + kind + '"' + attrs + '>'
    return ('<div class="field"><label for="' + name + '">' + escape(title) + '</label>' + control +
            ('<p class="helper" id="' + name + '-help">' + escape(hint) + '</p>' if hint else '') + '</div>')


def questions_html(workflow, values=None):
    country = _select("scenario__nation", (("England", "England"),), required=True, unknown=False,
                      hint="This service currently covers operations in England.")
    boxes = ''.join('<label class="activity-choice"><input type="checkbox" name="activity_' + value + '" value="true"> <span>' + escape(label) + '</span></label>' for value, label in ACTIVITIES)
    activities = ('<fieldset class="activity-list"><legend>What waste activities do you carry out?</legend>' + boxes +
                  '<label class="activity-choice"><input type="checkbox" name="activity_unknown" value="true"> <span>Not sure yet</span></label>' +
                  '<p class="helper">Select all that apply, or choose “Not sure yet”.</p></fieldset>')
    rule = (_select("rule__role", ROLES, required=True) + activities +
            _text("rule__site_location", placeholder="e.g. Leeds", hint="Give the town or site location you know. Do not enter personal contact details.") +
            _text("rule__waste_types", multiline=True, placeholder="e.g. cardboard packaging\nUsed wooden pallets", hint="One waste type or known code per line. Leave blank if unknown; do not guess waste codes.", maxlength=2000) +
            _select("rule__hazardous_status", YES_NO) + _select("rule__authorisation_status", AUTHORISATIONS))
    carrier = (_select("carrier__role", tuple(x for x in ROLES if x[0] in {"carrier", "broker", "dealer"}), required=True) +
               _select("carrier__action", ACTIONS, required=True, unknown=False) +
               '<div data-carrier-only>' + _select("carrier__own_waste_only", YES_NO) + _select("carrier__construction_demolition_waste", YES_NO) + '</div>' +
               _select("carrier__existing_registration_tier", (("upper", "Upper tier"), ("lower", "Lower tier")), hint="Answer only if you already have a registration. Otherwise leave this as not supplied."))
    tracking = (_select("tracking__receiving_authorisation", tuple(x for x in AUTHORISATIONS if x[0] != "none")) +
                _select("tracking__receives_controlled_waste", YES_NO, hint="Use the site’s existing records. Choose “Not sure” if you cannot confirm this.") +
                _select("tracking__reporting_method_ready", YES_NO, hint="Is a method ready to report waste receipts? Do not mark Yes unless it is operational.") +
                _text("tracking__as_of_date", kind="date", hint="Optional. Leave blank to use the date the report is generated.", maxlength=10))
    operation_sections = []
    for side in ("current", "proposed"):
        fields = []
        for field, label, placeholder in OPERATION_FIELDS:
            name = side + '__' + field
            if field == "hazardous_status":
                fields.append(_select(name, YES_NO))
            else:
                fields.append(_text(name, label=label, placeholder=placeholder, multiline=field in {"activities", "waste_types"},
                                    hint="One item per line; use only facts you know." if field in {"activities", "waste_types"} else "",
                                    maxlength=2000 if field in {"activities", "waste_types"} else 1000))
        operation_sections.append('<fieldset class="operation-section" data-known-facts="' + side + '"><legend>' +
                                  ('Current operation' if side == 'current' else 'Proposed operation') + '</legend>' + ''.join(fields) + '</fieldset>')
    change = '<p class="helper">Enter at least one known fact for each operation. Leave unknown details blank. Use the same wording for facts that are unchanged.</p><div class="operation-grid">' + ''.join(operation_sections) + '</div>'
    sections = []
    for key, body in ((RULE, rule), (CARRIER, carrier), (TRACKING, tracking), (CHANGE, change)):
        if key != workflow:
            body = re.sub(r'<(input|select|textarea)\b', r'<\1 disabled', body)
        sections.append('<section data-question-workflow="' + key + '"' + (' hidden' if key != workflow else '') + '>' + body + '</section>')
    return bind_form_values('<input type="hidden" name="form_version" value="questions-v1">' + country +
                            '<p class="question-note">Answer the questions you know. “Not sure” answers remain unknown and may mean the report needs further review.</p>' + ''.join(sections), values or {})


def scenario_from_questions(form, workflow):
    errors, fields = [], {}

    def reject(name, advice):
        message = LABELS.get(name, "Waste activities") + ': ' + advice
        errors.append(message)
        fields[message] = name

    def choice(name, options, *, required=False, unknown=True):
        raw = str(form.get(name, "")).strip()
        allowed = {value for value, _ in options}
        if not raw and required:
            reject(name, "choose an option from the list.")
        elif raw in {"", "unknown"} and unknown:
            return None
        elif raw not in allowed:
            reject(name, "choose a supported option from the list.")
        return raw if raw in allowed else None

    def boolean(name):
        value = choice(name, YES_NO)
        return True if value == "true" else False if value == "false" else None

    def text(name, maximum=1000):
        value = str(form.get(name, "")).strip()
        if len(value) > maximum:
            reject(name, f"use no more than {maximum} characters.")
        return value or None

    def items(name):
        value = text(name, 2000)
        return [part.strip() for part in re.split(r'[\n,]+', value) if part.strip()] if value else None

    nation = choice("scenario__nation", (("England", "England"),), required=True, unknown=False)
    scenario = {"nation": nation}
    if workflow == RULE:
        scenario.update(role=choice("rule__role", ROLES, required=True), site_location=text("rule__site_location"),
                        waste_types=items("rule__waste_types"), hazardous_status=boolean("rule__hazardous_status"),
                        authorisation_status=choice("rule__authorisation_status", AUTHORISATIONS))
        activities = [value for value, _ in ACTIVITIES if str(form.get('activity_' + value, '')).lower() in {'true', 'on', '1'}]
        unknown = str(form.get('activity_unknown', '')).lower() in {'true', 'on', '1'}
        if not activities and not unknown:
            reject("activity_produce_controlled_waste", "select at least one activity, or choose “Not sure yet”.")
        if activities and unknown:
            reject("activity_unknown", "choose known activities or “Not sure yet”, rather than both.")
        scenario['activities'] = activities
    elif workflow == CARRIER:
        role = choice("carrier__role", tuple(x for x in ROLES if x[0] in {'carrier', 'broker', 'dealer'}), required=True)
        scenario.update(role=role, action=choice("carrier__action", ACTIONS, required=True, unknown=False),
                        existing_registration_tier=choice("carrier__existing_registration_tier", (("upper", "Upper tier"), ("lower", "Lower tier"))))
        if role == 'carrier':
            scenario.update(own_waste_only=boolean("carrier__own_waste_only"), construction_demolition_waste=boolean("carrier__construction_demolition_waste"))
    elif workflow == TRACKING:
        scenario.update(receiving_authorisation=choice("tracking__receiving_authorisation", tuple(x for x in AUTHORISATIONS if x[0] != 'none')),
                        receives_controlled_waste=boolean("tracking__receives_controlled_waste"), reporting_method_ready=boolean("tracking__reporting_method_ready"))
        assessment_date = text("tracking__as_of_date", 10)
        if assessment_date:
            try:
                if date.fromisoformat(assessment_date).isoformat() != assessment_date:
                    raise ValueError
                scenario['as_of_date'] = assessment_date
            except ValueError:
                reject("tracking__as_of_date", "choose a valid calendar date.")
    elif workflow == CHANGE:
        for side in ('current', 'proposed'):
            facts = {}
            for field, _, _ in OPERATION_FIELDS:
                name = side + '__' + field
                value = boolean(name) if field == 'hazardous_status' else items(name) if field in {'activities', 'waste_types'} else text(name)
                if value is not None:
                    facts[field] = value
            if not facts:
                reject(side + '__site_location', 'enter at least one known fact for this operation before continuing.')
            scenario[side] = facts
    else:
        message = 'Preflight type: choose an option from the supported list.'
        errors.append(message)
        fields[message] = 'workflow'
    if errors:
        raise QuestionFormError(errors, fields)
    return scenario


STYLE = """
[data-question-workflow][hidden],[data-carrier-only][hidden]{display:none!important}
.question-note{margin:22px 0 0;padding:14px 16px;background:#eef4ff;color:#294a72;border-radius:10px;font-size:.9rem}
.question-text{min-height:90px;font:inherit;line-height:1.5}.activity-list{margin:24px 0 0;padding:18px;border:1px solid #dce5f0;border-radius:12px;min-width:0}.activity-list legend,.operation-section legend{padding:0 8px;font-weight:700;font-size:.95rem}
.activity-choice{display:flex;align-items:flex-start;gap:12px;margin:12px 0;font-weight:450}.activity-choice input{flex:0 0 18px;width:18px;min-height:18px;height:18px;padding:0;margin-top:4px;accent-color:#1d4ed8}.activity-choice span{min-width:0;line-height:1.5}
.operation-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:18px;margin-top:18px}.operation-section{min-width:0;margin:0;padding:16px;border:1px solid #dce5f0;border-radius:12px;background:#f9fbfe}.operation-section .field{margin-top:18px}.operation-section label{font-size:.92rem}
@media(max-width:1000px){.operation-grid{grid-template-columns:1fr}}
"""

SCRIPT = r"""
(()=>{
const select=document.getElementById('workflow'),form=select.form;
const clearValidity=()=>form.querySelectorAll('input,select,textarea').forEach(f=>{if(f.validity.customError){f.removeAttribute('aria-invalid');const message=document.getElementById(f.id+'-error');if(message)message.hidden=true;}f.setCustomValidity('');});
function activate(){
 form.querySelectorAll('[data-question-workflow]').forEach(section=>{
  const active=section.dataset.questionWorkflow===select.value;section.hidden=!active;
  section.querySelectorAll('input,select,textarea').forEach(f=>f.disabled=!active);
 });
 const carrier=form.querySelector('[data-carrier-only]');
 const show=select.value==='waste_carrier_broker_dealer_preflight'&&form.elements.carrier__role.value==='carrier';
 carrier.hidden=!show;carrier.querySelectorAll('select').forEach(f=>f.disabled=!show);
 clearValidity();
}
select.addEventListener('change',activate);form.elements.carrier__role.addEventListener('change',activate);
form.querySelectorAll('.activity-list input').forEach(box=>box.addEventListener('change',()=>{
 if(box.checked){form.querySelectorAll('.activity-list input').forEach(other=>{if(other!==box&&(box.name==='activity_unknown'||other.name==='activity_unknown'))other.checked=false;});}
 clearValidity();
}));
form.addEventListener('input',clearValidity,true);
form.addEventListener('submit',()=>{
 clearValidity();
 if(select.value==='waste_rule_preflight'&&!form.querySelector('.activity-list input:checked')){
  form.querySelector('.activity-list input').setCustomValidity('Waste activities: select at least one activity, or choose “Not sure yet”.');
 }
 if(select.value==='waste_permit_change_preflight')form.querySelectorAll('[data-known-facts]').forEach(section=>{
  const known=Array.from(section.querySelectorAll('input,select,textarea')).some(f=>f.value.trim()&&f.value!=='unknown');
  if(!known)section.querySelector('input').setCustomValidity((section.dataset.knownFacts==='current'?'Current operation':'Proposed operation')+': enter at least one known fact before continuing.');
 });
},true);
activate();
})();
"""
