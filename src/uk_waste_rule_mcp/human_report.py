from __future__ import annotations
from .form_feedback import feedback_page, with_form_feedback, bind_form_values, error_summary

from html import escape
from typing import Any, Mapping
from urllib.parse import parse_qs
import json
import os

ROUTE = "/compliance-report"
READINESS_ROUTE = f"{ROUTE}/readiness"
CHECKOUT_ROUTE = f"{ROUTE}/checkout"
SUCCESS_ROUTE = f"{ROUTE}/checkout-success"
CANCEL_ROUTE = f"{ROUTE}/checkout-cancelled"
HUMAN_REPORT_PRICE = os.getenv("WASTE_HUMAN_REPORT_PRICE_DISPLAY", "£19.00").strip() or "£19.00"

ACTIVITIES = (
    "produce_controlled_waste",
    "transport_waste",
    "arrange_waste",
    "receive_waste",
    "store_waste",
    "treat_recover_dispose_waste",
)
ROLES = ("producer", "carrier", "broker", "dealer", "receiver", "operator")
AUTHORISATIONS = ("permit", "exemption", "licence", "none", "other")

def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}

def query_value(request: Any, name: str) -> str:
    query = str(getattr(getattr(request, "url", None), "query", "") or "")
    return (parse_qs(query, keep_blank_values=True).get(name) or [""])[0]

def source_bucket(request: Any, form: Mapping[str, str] | None = None) -> str:
    raw = str((form or {}).get("src") or query_value(request, "src") or "regevidencehub").strip().lower()
    return raw[:64] or "regevidencehub"

def classification(request: Any, form: Mapping[str, str] | None = None, *, posted: bool) -> tuple[str, bool]:
    raw = str((form or {}).get("run_class") or query_value(request, "run") or "").strip().lower()
    if raw in {"owner", "owner_test", "test", "smoke", "ci"}:
        return "owner_test", True
    if raw in {"synthetic", "fixture"}:
        return "synthetic", False
    return ("confirmed_external", False) if posted else ("unknown", False)

def validate_form(form: Mapping[str, str]) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    role = str(form.get("role", "")).strip()
    if role not in ROLES:
        errors.append("Choose a supported waste role.")
    activities = [name for name in ACTIVITIES if _truthy(form.get(f"activity_{name}"))]
    if not activities:
        errors.append("Choose at least one waste activity.")
    if not _truthy(form.get("facts_complete")):
        errors.append("Confirm that you supplied the material facts you currently know.")
    payload: dict[str, Any] = {"nation": "England", "role": role, "activities": activities}
    site_location = str(form.get("site_location", "")).strip()
    if site_location:
        payload["site_location"] = site_location
    waste_types = [item.strip() for item in str(form.get("waste_types", "")).split(",") if item.strip()]
    if waste_types:
        payload["waste_types"] = waste_types
    hazardous = str(form.get("hazardous_status", "")).strip().lower()
    if hazardous in {"yes", "true", "1"}:
        payload["hazardous_status"] = True
    elif hazardous in {"no", "false", "0"}:
        payload["hazardous_status"] = False
    elif hazardous:
        errors.append("Hazardous status must be Yes, No, or Unknown.")
    authorisation = str(form.get("authorisation_status", "")).strip().lower()
    if authorisation:
        if authorisation not in AUTHORISATIONS:
            errors.append("Choose a supported authorisation status.")
        else:
            payload["authorisation_status"] = authorisation
    return (None, errors) if errors else (payload, [])

def hidden_fields(payload: Mapping[str, Any], *, src: str, run_class: str) -> str:
    values: list[tuple[str, str]] = [
        ("role", str(payload.get("role", ""))),
        ("site_location", str(payload.get("site_location", ""))),
        ("waste_types", ", ".join(payload.get("waste_types", []) if isinstance(payload.get("waste_types"), list) else [])),
        ("hazardous_status", "" if "hazardous_status" not in payload else ("yes" if payload.get("hazardous_status") else "no")),
        ("authorisation_status", str(payload.get("authorisation_status", ""))),
        ("facts_complete", "true"),
        ("src", src),
        ("run_class", run_class),
    ]
    for activity in payload.get("activities", []):
        values.append((f"activity_{activity}", "true"))
    return "".join(f'<input type="hidden" name="{escape(k)}" value="{escape(v)}">' for k, v in values)

def _select(name: str, label: str, values: tuple[str, ...], *, required: bool = False) -> str:
    req = " required" if required else ""
    options = ['<option value="">Unknown / not supplied</option>']
    options += [f'<option value="{escape(v)}">{escape(v.replace("_", " ").title())}</option>' for v in values]
    return f'<label for="{escape(name)}">{escape(label)}</label><select id="{escape(name)}" name="{escape(name)}"{req}>' + "".join(options) + "</select>"

def form_html(action: str, *, src: str = "regevidencehub", run_class: str = "", values=None) -> str:
    activity_boxes = "".join(
        f'<label class="check"><input type="checkbox" name="activity_{escape(a)}" value="true"> {escape(a.replace("_", " ").title())}</label>'
        for a in ACTIVITIES
    )
    markup = f'''<form method="post" action="{escape(action)}" data-require-activity="true">
<input type="hidden" name="src" value="{escape(src)}"><input type="hidden" name="run_class" value="{escape(run_class)}">
<fieldset><legend>Waste operation facts</legend>
<div class="field">{_select("role","Primary waste role",ROLES,required=True)}</div>
<div class="field"><span class="label">Waste activities</span><div>{activity_boxes}</div></div>
<div class="field"><label for="site_location">Site / operating location</label><input id="site_location" name="site_location" type="text" placeholder="e.g. Leeds"></div>
<div class="field"><label for="waste_types">Waste types or codes</label><input id="waste_types" name="waste_types" type="text" placeholder="Comma-separated; do not guess codes"></div>
<div class="field">{_select("hazardous_status","Hazardous waste status",("yes","no"))}</div>
<div class="field">{_select("authorisation_status","Current authorisation",AUTHORISATIONS)}</div>
<label class="check"><input type="checkbox" name="facts_complete" value="true" required> I have supplied the material facts I currently know.</label>
<button type="submit">Check readiness</button>
</fieldset></form>'''
    return bind_form_values(markup, values or {})

@feedback_page
def render_page(*, form: str, payload: Mapping[str, Any] | None = None, errors: list[str] | None = None, src: str = "regevidencehub", run_class: str = "") -> str:
    error_html = ""
    if errors:
        error_html = '<section class="errors"><h2>Correct these inputs</h2><ul>' + "".join('<li data-field="' + ("activity_produce_controlled_waste" if "waste activity" in e else "facts_complete" if "Confirm" in e else "") + '">' + escape(e) + '</li>' for e in errors) + "</ul></section>"
    readiness = ""
    if payload is not None:
        readiness = f'''<section class="result"><h2>Free readiness result</h2>
<p><strong>Supported route:</strong> England waste-rule preflight.</p>
<p><strong>Role:</strong> {escape(str(payload.get("role","")))}</p>
<p><strong>Activities supplied:</strong> {escape(", ".join(payload.get("activities", [])))}</p>
<p>Your case has the minimum structured facts for the paid evidence-linked report. Missing or uncertain regulatory facts remain explicit; the service does not infer waste codes or hazardous status.</p>
<form method="post" action="{CHECKOUT_ROUTE}">{hidden_fields(payload,src=src,run_class=run_class)}<button type="submit">Get England Waste Compliance Preflight Report — {HUMAN_REPORT_PRICE}</button></form>
</section>'''
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>England Waste Compliance Preflight Report</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#f3f6fb;color:#18324b;font:16px/1.65 system-ui,-apple-system,sans-serif}}main{{max-width:960px;margin:0 auto;padding:clamp(24px,5vw,48px) 24px}}h1{{font-size:clamp(1.8rem,5vw,2.6rem);line-height:1.2;letter-spacing:-.035em}}h2{{line-height:1.3}}fieldset{{background:#fff;border:1px solid #dce5ef;border-radius:14px;padding:22px 24px;margin:22px 0;box-shadow:0 6px 22px #193a580c}}legend,.label,label{{font-weight:650}}.field{{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:18px;align-items:center;border-top:1px solid #edf1f5;padding:14px 0;min-width:0}}.field>*{{min-width:0}}select,input{{font:inherit;color:inherit;padding:11px 13px;border:1px solid #aabacf;border-radius:8px;width:100%;min-height:48px;background:#fff}}input[type=checkbox]{{width:18px;height:18px;min-height:18px;vertical-align:middle;accent-color:#155eef}}.check{{display:block;font-weight:400;line-height:1.5;margin:10px 0}}button{{background:#155eef;color:#fff;border:0;border-radius:9px;padding:12px 18px;min-height:48px;font:inherit;font-weight:700;cursor:pointer;margin-top:14px}}button:hover{{background:#124ac0}}:focus-visible{{outline:3px solid #94b9ff;outline-offset:3px}}.result,.intro{{background:#fff;border:1px solid #dce5ef;border-left:4px solid #155eef;border-radius:12px;padding:18px 22px;margin:22px 0;box-shadow:0 4px 18px #193a5808}}.errors{{background:#fff5f4;border:1px solid #f0d2d0;border-left:4px solid #bc3030;border-radius:12px;padding:14px 18px}}.muted{{color:#536b82}}@media(max-width:700px){{main{{padding:24px 16px 36px}}.field{{grid-template-columns:1fr;gap:8px;align-items:start}}fieldset{{padding:18px}}button{{width:100%}}.result,.intro,.errors{{padding:16px}}}}</style></head><body><main>
<p class="muted">RegEvidenceHub Waste · England</p><h1>England Waste Compliance Preflight Report</h1>
<section class="intro"><p><strong>Free readiness:</strong> confirm the supported role and waste activities before payment.</p><p><strong>Paid report — {HUMAN_REPORT_PRICE}:</strong> the full deterministic evidence-linked waste-rule preflight for the supplied case, including route, missing facts, official-source evidence and fail-closed review status. Access lasts 24 hours.</p><p>Stripe handles payment. RegEvidenceHub Waste does not collect card details.</p></section>
{error_html}{readiness}<h2>Start with structured facts</h2>{form}
<p class="muted">Preflight information only; not Environment Agency approval, a permit/registration decision, or legal advice.</p></main></body></html>'''

@feedback_page
def render_paid_report(decision: Mapping[str, Any], *, entitlement_code: str | None) -> str:
    detail = escape(json.dumps(dict(decision), indent=2, sort_keys=True, default=str))
    code = escape(entitlement_code or "waste_compliance_report")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>England Waste Compliance Preflight Report</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f3f6fb;color:#18324b;font:16px/1.65 system-ui,-apple-system,sans-serif}}
main{{max-width:960px;margin:0 auto;padding:clamp(24px,6vw,56px) 24px}}
.brand{{margin:0 0 20px;color:#215cdb;font-size:.8rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase}}
h1{{margin:0 0 22px;font-size:clamp(1.8rem,5vw,2.6rem);line-height:1.2;letter-spacing:-.035em}}
h2{{margin:0 0 14px;font-size:1.25rem}}
.card{{margin:20px 0;padding:clamp(20px,4vw,30px);background:#fff;border:1px solid #dce5ef;border-radius:16px;box-shadow:0 6px 22px #193a580c;min-width:0}}
.ok{{border-top:4px solid #16804a;background:#f0faf4}}.ok p:last-child{{margin-bottom:0}}
pre{{margin:0;max-width:100%;white-space:pre-wrap;overflow-wrap:anywhere;overflow:auto;background:#f5f8fc;border:1px solid #e3eaf2;border-radius:10px;padding:18px;font:13px/1.6 ui-monospace,SFMono-Regular,Consolas,monospace}}
.muted{{color:#536b82}}a{{color:#175acb;text-underline-offset:3px}}:focus-visible{{outline:3px solid #83b4ff;outline-offset:3px}}
footer{{margin-top:26px;color:#536b82;font-size:.9rem}}
@media(max-width:600px){{main{{padding:24px 16px 36px}}.card{{padding:20px}}pre{{padding:14px;font-size:12px}}}}
</style></head><body><main><p class="brand">RegEvidenceHub Waste · England</p><h1>England Waste Compliance Preflight Report</h1>
<section class="card ok"><p><strong>Paid access verified</strong></p><p>Order reference: <code>{code}</code></p><p>This report preserves deterministic missing-information, evidence-freshness and review-required states.</p></section>
<section class="card"><h2>Decision details</h2><pre>{detail}</pre></section>
<footer>Preflight information only; not Environment Agency approval, a permit or registration decision, or legal advice.</footer></main></body></html>'''

STATUS_STYLE = """
*{box-sizing:border-box}body{margin:0;background:#f3f6fb;color:#18324b;font:16px/1.65 system-ui,-apple-system,sans-serif}
main{max-width:720px;margin:0 auto;padding:clamp(24px,7vw,64px) 24px}
.brand{margin:0 0 20px;color:#215cdb;font-size:.8rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase}
.card{background:#fff;border:1px solid #dce5ef;border-top:4px solid #215cdb;border-radius:16px;padding:clamp(22px,5vw,38px);box-shadow:0 10px 32px #193a5810}
h1{margin:0 0 14px;font-size:clamp(1.8rem,5vw,2.5rem);line-height:1.2;letter-spacing:-.035em}
p{margin:0 0 16px}.message{color:#536b82}.actions{margin:24px 0 0}
a{color:#175acb;text-underline-offset:3px}.button{display:inline-flex;min-height:48px;align-items:center;justify-content:center;padding:11px 18px;border-radius:9px;background:#2160df;color:#fff;text-decoration:none;font-weight:700}
.button:hover{background:#174bb6}.button:focus-visible{outline:3px solid #83b4ff;outline-offset:3px}
.foot{margin-top:24px;color:#536b82;font-size:.9rem}
@media(max-width:600px){main{padding:24px 16px 36px}.button{width:100%;text-align:center}}
"""

def _render_status_page(title: str, message: str, *, support: bool = False) -> str:
    support_link = ' · <a href="/support">Contact support</a>' if support else ""
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>{escape(title)}</title><style>{STATUS_STYLE}</style></head><body><main>
<p class="brand">RegEvidenceHub Waste · England</p><section class="card"><h1>{escape(title)}</h1><p class="message">{escape(message)}</p><nav class="actions" aria-label="Next steps"><a class="button" href="{ROUTE}">Return to the report form</a></nav></section>
<p class="foot">Preflight information only; not regulator approval or legal advice{support_link}.</p></main></body></html>'''

def render_checkout_error(message: str | None = None) -> str:
    if message:
        return _render_status_page(
            "Report temporarily unavailable",
            "We could not safely generate the report. Your payment may already have completed. Do not purchase again; contact support for help.",
            support=True,
        )
    return _render_status_page(
        "Checkout unavailable",
        "Checkout could not be started. No payment was taken. Please try again later.",
    )

def render_cancelled() -> str:
    return _render_status_page(
        "Checkout cancelled",
        "No payment was taken and no paid report was generated. You can return to the form whenever you are ready.",
    )

def render_entitlement_pending() -> str:
    return _render_status_page(
        "Payment confirmation pending",
        "Your payment has not been confirmed yet, so no paid report is available. Refresh this page in a few seconds. If the issue continues, do not purchase again; contact support.",
        support=True,
    )
