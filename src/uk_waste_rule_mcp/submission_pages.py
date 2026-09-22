"""Public submission pages for the payment-free Waste AI surface."""

from __future__ import annotations

import os
from html import escape

from starlette.responses import HTMLResponse, PlainTextResponse, Response

from .public_ai_server import PUBLIC_AI_SERVER_NAME

SUPPORT_EMAIL = os.getenv("WASTE_SUPPORT_EMAIL", "launchcircle.server@gmail.com").strip()


def _page(title: str, body: str) -> HTMLResponse:
    email = escape(SUPPORT_EMAIL)
    return HTMLResponse(
        f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow"><title>{escape(title)} — {escape(PUBLIC_AI_SERVER_NAME)}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:820px;margin:48px auto;padding:0 20px;line-height:1.6;color:#171717}}h1,h2{{line-height:1.25}}nav a{{margin-right:14px}}.muted{{color:#666}}</style></head>
<body><nav><a href="/waste-rule-preflight">Product</a><a href="/plugin/privacy">Privacy</a><a href="/plugin/terms">Terms</a><a href="/plugin/support">Support</a></nav>
{body}<hr><p class="muted">Support: <a href="mailto:{email}">{email}</a></p></body></html>"""
    )


async def plugin_product_page(_request):
    return _page(
        PUBLIC_AI_SERVER_NAME,
        """
<h1>RegEvidenceHub Waste</h1>
<p>A payment-free public AI connector for conservative England waste-rule and permit-change preflight.</p>
<p>It helps users identify a bounded regulatory route, inspect official-source health, prepare missing facts, and screen whether a proposed operational change requires permit or exemption review.</p>
<h2>Scope</h2>
<p>The current MVP is England-only and covers bounded waste roles and activities including producers, carriers, brokers, dealers, receivers, storage and treatment contexts.</p>
<h2>Boundary</h2>
<p>This public AI surface does not submit registrations, permits, exemptions, waste records or Digital Waste Tracking data. It does not determine hazardous status, waste codes, permit conditions, exemption eligibility, regulator approval, or provide legal advice.</p>
<h2>Payment boundary</h2>
<p>This public AI surface is payment-free. It does not initiate, promote, or link to purchases, paid upgrades, Stripe checkout, or x402 payment flows.</p>
""",
    )


async def privacy_page(_request):
    return _page(
        "Privacy Policy",
        """
<h1>Privacy Policy</h1><p><strong>Effective date:</strong> 22 September 2026</p>
<p>This policy covers the payment-free public AI edition of RegEvidenceHub Waste.</p>
<h2>Information processed</h2>
<p>The service processes only the bounded waste-operation facts supplied to a tool call. It does not require an account and does not request passwords, payment credentials, cryptocurrency keys, contacts, precise location, or full conversation history.</p>
<h2>Operational telemetry</h2>
<p>Hosting infrastructure may retain minimal operational logs for reliability, abuse prevention, security and aggregate measurement. The public AI edition is not designed to persist substantive waste case payloads.</p>
<h2>Payment boundary</h2>
<p>This edition does not initiate purchases, paid upgrades, Stripe checkout, or x402 payment flows and does not process payment credentials.</p>
<h2>Sharing</h2>
<p>Information may be processed by infrastructure providers used to host and operate the service. We do not sell public-AI-tool user data or build advertising profiles from it.</p>
<h2>Contact</h2>
<p>Privacy requests may be sent to the support address below. Do not send passwords, payment credentials, private keys, or unrelated sensitive documents.</p>
""",
    )


async def terms_page(_request):
    return _page(
        "Terms of Use",
        """
<h1>Terms of Use</h1><p><strong>Effective date:</strong> 22 September 2026</p>
<h2>Purpose</h2>
<p>The public AI edition provides read-only regulatory preflight, preparation guidance and bounded official-source health information for England waste workflows.</p>
<h2>Not regulator approval or legal advice</h2>
<p>It does not issue Environment Agency decisions, permits, exemptions or registrations, submit regulatory filings, provide legal representation, or replace current official guidance or professional advice.</p>
<h2>Fail-closed boundary</h2>
<p>Unsupported, stale, changed, unavailable or incomplete evidence and facts are returned as review/unknown states rather than guessed conclusions.</p>
<h2>Payment boundary</h2>
<p>This public AI edition does not request or process payment and does not initiate or link to purchases or paid upgrades.</p>
<h2>Availability</h2>
<p>The service may change, be rate-limited, suspended or discontinued as official requirements and source evidence evolve.</p>
""",
    )


async def support_page(_request):
    email = escape(SUPPORT_EMAIL)
    return _page(
        "Support",
        f"""<h1>Support</h1><p>Email <strong><a href="mailto:{email}">{email}</a></strong>.</p>
<p>Include the approximate time, tool used and non-sensitive error text. Do not send passwords, payment credentials, private keys, seed phrases or unrelated sensitive documents.</p>""",
    )


async def openai_apps_challenge(_request):
    token = os.getenv("OPENAI_APPS_CHALLENGE", "").strip()
    if not token:
        return Response(status_code=404)
    return PlainTextResponse(token, media_type="text/plain")
