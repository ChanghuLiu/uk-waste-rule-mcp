"""Readable purchase report pages; decision payloads remain unchanged."""
from __future__ import annotations
from .form_feedback import feedback_page, with_form_feedback, bind_form_values, error_summary

import json
from html import escape
from urllib.parse import urlencode, urlsplit

STYLE = """
*{box-sizing:border-box}body{margin:0;background:#f2f6fb;color:#18324b;font:16px/1.65 system-ui,-apple-system,sans-serif}
a{color:#175acb;text-underline-offset:3px}a:hover{color:#103a85}a:focus-visible,summary:focus-visible{outline:3px solid #83b4ff;outline-offset:4px}
.wrap{max-width:1120px;margin:auto;padding:40px 24px 64px}.brand{font-size:13px;font-weight:800;letter-spacing:.1em;color:#225ac7;margin-bottom:28px}
h1{font-size:clamp(28px,4vw,40px);line-height:1.18;margin:12px 0 18px;letter-spacing:-.025em}h2{font-size:21px;margin:0 0 18px}h3{font-size:17px;margin:0 0 8px}
p{margin:0 0 16px}.muted{color:#536b82}.hero{background:#173453;color:white;border-radius:20px;padding:32px;margin-bottom:24px}.hero .muted{color:#d2e0ee}
.badge{display:inline-block;background:#e7f5ed;color:#145636;border:1px solid #c4e2d1;border-radius:24px;padding:5px 12px;font-size:13px;font-weight:750}
.grid{display:grid;grid-template-columns:minmax(0,1.65fr) minmax(0,1fr);gap:24px;align-items:start}.stack{display:grid;gap:24px}
.card{background:white;border:1px solid #dce5ef;border-radius:16px;padding:28px;box-shadow:0 6px 20px #193a5810;min-width:0}
.notice{background:#fff4de;border:1px solid #ecd5a4;color:#704713;border-radius:12px;padding:16px 20px;margin-bottom:24px}
dl{margin:0}dl>div{display:grid;grid-template-columns:42% minmax(0,1fr);gap:14px;padding:12px 0;border-bottom:1px solid #e7edf4}
dl>div:last-child{border:0}dt{color:#536b82}dd{margin:0;font-weight:650;overflow-wrap:anywhere}
ul,ol{margin:0;padding-left:23px}li{padding-left:4px;margin:0 0 14px}li:last-child{margin-bottom:0}
.finding{border-left:3px solid #729acc;padding:4px 0 4px 16px;margin:0 0 20px}.finding:last-child{margin-bottom:0}
.meta{font-size:13px;color:#596f84}.source{padding:16px 0;border-top:1px solid #e4ebf3}.source:first-of-type{border:0;padding-top:0}
.source a{font-weight:650;overflow-wrap:anywhere}.source p{margin:6px 0 0}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:12px 0;border-bottom:1px solid #e5edf5}th:last-child,td:last-child{text-align:right;white-space:nowrap}
code{overflow-wrap:anywhere;font-size:14px;background:#edf3fa;padding:3px 6px;border-radius:5px}
details{margin-top:24px}summary{cursor:pointer;font-weight:700;padding:8px 0}details p{margin-top:12px}
pre{font:13px/1.6 ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f5fa;padding:20px;border-radius:12px;max-height:650px;overflow:auto}
.btn{display:inline-flex;justify-content:center;align-items:center;min-height:48px;padding:10px 20px;border-radius:9px;background:#2160df;color:white;text-decoration:none;font-weight:700;margin-top:10px}.btn:hover{background:#174bb6;color:white}
.footer{font-size:14px;color:#5a7087;margin-top:28px}.message{max-width:700px;margin:6vh auto}.message .card{padding:36px}
@media(max-width:760px){.wrap{padding:24px 16px 40px}.grid{grid-template-columns:1fr}.hero,.card{padding:22px}.brand{margin-bottom:20px}dl>div{grid-template-columns:1fr;gap:3px}.message{margin:3vh auto}}
@media print{body{background:white}.wrap{max-width:none;padding:0}.grid{display:block}.card{box-shadow:none;margin-bottom:20px;break-inside:avoid}.hero{background:white;color:#18324b;border:1px solid #dce5ef}.hero .muted{color:#536b82}}
"""

def _text(value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    elif value is True:
        value = "Yes"
    elif value is False:
        value = "No"
    elif value is None:
        value = "Not specified"
    return escape(str(value))


def _label(value):
    return str(value).replace("_", " ").capitalize()


@feedback_page
def document(title, body, script=""):
    script_tag = "<script>" + script + "</script>" if script else ""
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="referrer" content="no-referrer"><title>' + _text(title) +
        '</title><style>' + STYLE + '</style></head><body><main class="wrap">'
        '<header class="brand">REG EVIDENCE HUB · WASTE</header>' + body +
        '<footer class="footer">Informational preflight only; not Environment Agency approval or legal advice.</footer>'
        '</main>' + script_tag + '</body></html>'
    )


def message_response(title, message, status_code=200, script="", status_id=False):
    from starlette.responses import HTMLResponse
    status = ' id="status" role="status" aria-live="polite"' if status_id else ""
    body = (
        '<section class="message"><div class="card"><h1>' + _text(title) +
        '</h1><p class="muted"' + status + '>' + _text(message) +
        '</p><a class="btn" href="/waste-report/recover">Recover by email</a>'
        '<p style="margin-top:20px"><a href="/waste-report">Return to the report form</a></p></div></section>'
    )
    return HTMLResponse(document(title, body, script), status_code=status_code, headers={
        "Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
    })


def _list(items):
    return "<ul>" + "".join("<li>" + _text(x) + "</li>" for x in items) + "</ul>"


def paid_report_html(report, checkout_id):
    decision = report.get("decision") or {}
    health = report.get("source_health") or {}
    if not decision:
        decision = {"status": report.get("status", "Not specified")}
    notice = (
        '<div class="notice">Review the cited official sources and resolve any review-required or missing-information findings before acting. '
        'Paid access confirms your purchase; this report does not grant regulatory approval.</div>'
    )
    body = (
        '<section class="hero"><span class="badge">Verified paid access</span>'
        '<h1>Your England Waste Compliance Report</h1><p class="muted">Generated ' +
        _text(report.get("generated_on", "Not specified")) + ' · England</p></section>' + notice
    )
    decision_rows = "".join(
        "<div><dt>" + _text(_label(key)) + "</dt><dd>" + _text(_label(value) if isinstance(value, str) else value) + "</dd></div>"
        for key, value in decision.items()
    )
    findings = "".join(
        '<article class="finding"><h3>' + _text(_label(item.get("status", item.get("severity", "Finding")))) +
        '</h3><p>' + _text(item.get("message", "")) + '</p><p class="meta">' +
        _text(item.get("code", "")) + " · " + _text(item.get("severity", "")) +
        ' · Sources: ' + _text(", ".join(item.get("source_ids") or [])) + '</p></article>'
        for item in report.get("findings", [])
    ) or '<p class="muted">No findings were returned.</p>'
    left = '<section class="card"><h2>Decision summary</h2><dl>' + decision_rows + '</dl></section>'
    left += '<section class="card"><h2>Findings</h2>' + findings + '</section>'
    if report.get("next_actions"):
        left += '<section class="card"><h2>Next steps</h2>' + _list(report["next_actions"]) + '</section>'
    if report.get("limitations"):
        left += '<section class="card"><h2>Scope and limitations</h2>' + _list(report["limitations"]) + '</section>'
    right = '<section class="card"><h2>Official source checks</h2><dl><div><dt>Source status</dt><dd>' + _text(health.get("status", "Not specified")) + '</dd></div><div><dt>Decision usable</dt><dd>' + _text(health.get("decision_usable")) + '</dd></div></dl>'
    if health.get("decision_usable") is False:
        right += '<p class="notice" style="margin-top:18px">Official-source checks require review. Resolve this before relying on the decision.</p>'
    if health.get("blocking_sources"):
        right += _list(health["blocking_sources"])
    for item in report.get("evidence", []):
        url = str(item.get("url") or "")
        parsed = urlsplit(url)
        title = _text(item.get("title", item.get("id", "Source")))
        link = '<a href="' + escape(url, quote=True) + '" target="_blank" rel="noopener noreferrer">' + title + '</a>' if parsed.scheme in ("http", "https") and parsed.netloc else title
        right += '<article class="source">' + link + '<p class="meta">Checked: ' + _text(item.get("last_checked_at", item.get("last_checked", "Not specified"))) + '</p><p class="meta">Status: ' + _text(item.get("last_status", "Not specified")) + '</p></article>'
    right += '</section>'
    fees = report.get("current_published_fees_gbp") or {}
    rows = "".join(
        '<tr><td>' + _text(_label(key)) + '</td><td>£' + format(value, ".2f") + '</td></tr>'
        for key, value in fees.items() if isinstance(value, (int, float)) and not isinstance(value, bool)
    )
    if rows:
        right += '<section class="card"><h2>Published registration fees</h2><p class="muted">Fees charged by the official registration service, separate from your report purchase.</p><table><thead><tr><th scope="col">Action</th><th scope="col">GBP</th></tr></thead><tbody>' + rows + '</tbody></table><p class="meta" style="margin-top:16px">' + _text(fees.get("note", "Confirm current fees with the official service.")) + '</p></section>'
    body += '<div class="grid"><div class="stack">' + left + '</div><aside class="stack">' + right + '</aside></div>'
    recovery_url = "/waste-report/recover?" + urlencode({"checkout_id": checkout_id})
    body += (
        '<section class="card" style="margin-top:24px"><h2>Your order</h2><p class="muted">Save this reference for later access.</p><p><code>' +
        _text(checkout_id) + '</code></p><p class="meta">Access lasts 24 hours from purchase. Email recovery does not extend the access period.</p>'
        '<details><summary>Recover this report later</summary><p>Use the same email address you entered at checkout.</p><a class="btn" href="' +
        escape(recovery_url, quote=True) + '">Send a recovery link</a></details></section>'
        '<details class="card"><summary>View complete report data (JSON)</summary><pre>' +
        _text(json.dumps(report, indent=2, ensure_ascii=False)) + '</pre></details>'
    )
    return document("Your Waste compliance report", body)
