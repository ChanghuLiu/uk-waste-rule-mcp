from __future__ import annotations

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

def form_html(action: str, *, src: str = "regevidencehub", run_class: str = "") -> str:
    activity_boxes = "".join(
        f'<label class="check"><input type="checkbox" name="activity_{escape(a)}" value="true"> {escape(a.replace("_", " ").title())}</label>'
        for a in ACTIVITIES
    )
    return f'''<form method="post" action="{escape(action)}">
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

def render_page(*, form: str, payload: Mapping[str, Any] | None = None, errors: list[str] | None = None, src: str = "regevidencehub", run_class: str = "") -> str:
    error_html = ""
    if errors:
        error_html = '<section class="errors"><h2>Correct these inputs</h2><ul>' + "".join(f"<li>{escape(e)}</li>" for e in errors) + "</ul></section>"
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
<style>body{{font-family:system-ui,sans-serif;max-width:960px;margin:0 auto;padding:32px 20px;line-height:1.55;color:#17202a}}h1{{line-height:1.15}}fieldset{{border:1px solid #ccd6dd;border-radius:8px;padding:18px}}legend,.label,label{{font-weight:650}}.field{{display:grid;grid-template-columns:minmax(240px,1fr) minmax(280px,1fr);gap:14px;align-items:start;border-top:1px solid #edf0f2;padding:10px 0}}select,input{{font:inherit;padding:8px;border:1px solid #9aa8b2;border-radius:5px;width:100%;box-sizing:border-box}}input[type=checkbox]{{width:auto}}.check{{display:block;font-weight:400;margin:6px 0}}button{{background:#155eef;color:#fff;border:0;border-radius:5px;padding:10px 16px;font:inherit;font-weight:700;cursor:pointer;margin-top:14px}}.result,.intro{{background:#f5f8fa;border-left:4px solid #155eef;padding:14px 18px;margin:22px 0}}.errors{{background:#fff1f0;border-left:4px solid #c00;padding:10px 18px}}.muted{{color:#53636f}}@media(max-width:700px){{.field{{grid-template-columns:1fr}}}}</style></head><body><main>
<p class="muted">RegEvidenceHub Waste · England</p><h1>England Waste Compliance Preflight Report</h1>
<section class="intro"><p><strong>Free readiness:</strong> confirm the supported role and waste activities before payment.</p><p><strong>Paid report — {HUMAN_REPORT_PRICE}:</strong> the full deterministic evidence-linked waste-rule preflight for the supplied case, including route, missing facts, official-source evidence and fail-closed review status. Access lasts 24 hours.</p><p>Stripe handles payment. RegEvidenceHub Waste does not collect card details.</p></section>
{error_html}{readiness}<h2>Start with structured facts</h2>{form}
<p class="muted">Preflight information only; not Environment Agency approval, a permit/registration decision, or legal advice.</p></main></body></html>'''

def render_paid_report(decision: Mapping[str, Any], *, entitlement_code: str | None) -> str:
    detail = escape(json.dumps(dict(decision), indent=2, sort_keys=True, default=str))
    code = escape(entitlement_code or "waste_compliance_report")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>England Waste Compliance Preflight Report</title><style>body{{font-family:system-ui,sans-serif;max-width:960px;margin:0 auto;padding:32px 20px;line-height:1.55;color:#17202a}}pre{{white-space:pre-wrap;overflow:auto;background:#f5f5f5;padding:16px;border-radius:8px}}.ok{{background:#f5f8fa;border-left:4px solid #155eef;padding:14px 18px}}</style></head><body><main><h1>England Waste Compliance Preflight Report</h1><section class="ok"><p><strong>Entitlement verified:</strong> {code}</p><p>This report preserves deterministic missing-information, evidence-freshness and review-required states.</p></section><h2>Decision</h2><pre>{detail}</pre><p>Preflight information only; not regulator approval or legal advice.</p></main></body></html>'''

def render_checkout_error(message: str = "Checkout is temporarily unavailable.") -> str:
    return f'<!doctype html><html><body><main><h1>Checkout unavailable</h1><p>{escape(message)}</p><p>No payment was taken.</p></main></body></html>'

def render_cancelled() -> str:
    return '<!doctype html><html><body><main><h1>Checkout cancelled</h1><p>No payment was taken and no paid report was generated.</p></main></body></html>'

def render_entitlement_pending() -> str:
    return '<!doctype html><html><body><main><h1>Payment confirmation pending</h1><p>Stripe has returned you to RegEvidenceHub, but the paid entitlement is not active yet. Refresh this page in a few seconds.</p></main></body></html>'
