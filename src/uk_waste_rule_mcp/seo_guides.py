"""Human-facing, source-linked search guide pages."""
from __future__ import annotations

import json
from html import escape

GUIDE_PATH = "/guides/england-digital-waste-tracking-receiving-sites"
GUIDE_IMAGE_PATH = "/guides/assets/england-waste-receiving-site.jpg"
INDEXNOW_KEY = "e69d2ed78df416e0128996035aa76503"
TITLE = "Digital Waste Tracking for England Waste Receiving Sites: Scope and Checklist"
DESCRIPTION = (
    "Check whether your permitted or licensed site receiving controlled waste is in scope, "
    "what to report, the current deadline, and how to prepare."
)


def render_receiving_site_guide(public_origin: str) -> str:
    origin = escape(public_origin.rstrip("/"), quote=True)
    canonical = f"{origin}{GUIDE_PATH}"
    structured_data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": TITLE,
        "description": DESCRIPTION,
        "datePublished": "2026-11-03",
        "dateModified": "2026-11-03",
        "mainEntityOfPage": canonical,
        "publisher": {"@type": "Organization", "name": "RegEvidenceHub"},
    }
    schema = json.dumps(structured_data, ensure_ascii=True).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(TITLE)}</title>
<meta name="description" content="{escape(DESCRIPTION, quote=True)}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="article">
<meta property="og:title" content="{escape(TITLE, quote=True)}">
<meta property="og:description" content="{escape(DESCRIPTION, quote=True)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{origin}{GUIDE_IMAGE_PATH}">
<meta property="og:image:type" content="image/jpeg">
<meta property="og:image:alt" content="Illustration of a waste truck at a receiving-site weighbridge with an operator reviewing a tablet checklist.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{origin}{GUIDE_IMAGE_PATH}">
<meta name="twitter:image:alt" content="Illustration of a waste truck at a receiving-site weighbridge with an operator reviewing a tablet checklist.">
<script type="application/ld+json">{schema}</script>
<style>
:root{{color-scheme:light}}body{{font:18px/1.65 system-ui,sans-serif;color:#17202a;margin:0}}
main{{max-width:820px;margin:0 auto;padding:28px 22px 64px}}a{{color:#155eef}}
nav,.meta{{font-size:15px;color:#53636f}}h1{{font-size:clamp(2rem,5vw,3rem);line-height:1.12}}
h2{{margin-top:2rem;line-height:1.25}}.callout{{background:#f5f8fa;border-left:4px solid #155eef;padding:14px 18px;margin:24px 0}}
.cta{{background:#eef4ff;border-radius:8px;padding:20px;margin:28px 0}}
li{{margin:.45rem 0}}.sources li{{overflow-wrap:anywhere}}.disclaimer{{font-size:15px;color:#53636f}}
</style>
</head>
<body><main>
<nav><a href="/">RegEvidenceHub Waste</a> / Guides / England Digital Waste Tracking</nav>
<article>
<header>
<p class="meta">England · Receiving-site guide · Last reviewed 3 November 2026</p>
<h1>Digital Waste Tracking for England waste receiving sites: scope and checklist</h1>
<p><strong>Since 1 October 2026, permitted or licensed waste receiving sites in England must use the Report Receipt of Waste service to record each load of controlled waste they receive.</strong> First confirm whether the relevant operation and site are in scope. This is not a general rule for every business that produces or handles waste.</p>
<p class="meta">This guide summarizes current official guidance. Check the linked GOV.UK sources before acting because service instructions and requirements can change.</p>
</header>

<section class="callout">
<strong>Quick checklist</strong>
<ol>
<li>Confirm the legal operator, the site and its waste permit or licence.</li>
<li>Confirm whether controlled waste is received and whether an exception applies.</li>
<li>Choose the official service or suitable software for submitting records.</li>
<li>Assign responsibility for capturing, submitting and correcting each receipt.</li>
</ol>
</section>

<h2>Who needs to report?</h2>
<p>The England receiving-site requirement applies to organisations with a permit or licence to receive controlled waste. Official guidance includes permitted operations, installations and mobile plants, including sites located where waste is produced. An English household waste recycling centre does not have to use the service for household waste received from residents. A separate process applies to operators who meet the official definition of digitally excluded; preferring paper records, unfamiliarity with software, or added cost or time does not by itself meet that definition.</p>
<p>This guide covers England. The digital reporting requirement took effect in England and Wales on 1 October 2026; the corresponding start date in Scotland and Northern Ireland is 1 January 2027. Check the relevant national guidance for operations outside England.</p>
<p>Do not decide scope from a business name or simply because it handles waste. Confirm the legal operator, relevant permit or licence, site, and whether controlled waste is received. If these facts are uncertain, resolve them with the Environment Agency or a qualified adviser.</p>

<h2>When must a receipt be reported?</h2>
<p>For a receipt in England, submit the record within two working days, excluding weekends and bank holidays. The clock starts on the day after receipt. For example, a load received at 9 a.m. on Monday is due by 11:59 p.m. on Wednesday, assuming no bank holiday changes the working-day count.</p>
<p>If the service or software reports an error, official guidance says to correct the submission within the same two-working-day timeframe. Build this deadline into the site’s gate, weighbridge or administration process rather than relying on a later manual review.</p>
<h2>What records and returns continue?</h2>
<p>Digital reporting does not currently replace every existing waste record or return. Until further notice, continue waste transfer notes, Annex VII forms and hazardous-waste consignment notes where required. Continue waste returns required by the environmental permit and hazardous-waste consignee returns. If a hazardous load has multiple consignment notes, report the waste covered by each note as a separate entry.</p>
<h2>What if a record is wrong or the service is unavailable?</h2>
<p>Correct a submission error reported by the service or your software within the same two-working-day window. If you later discover an error in submitted data or in waste information given to you, correct it as soon as possible and within one month of discovering it.</p>
<p>If an outage prevents reporting, notify the regulator as soon as possible unless it has told you the service itself is unavailable. Make and retain a written receipt record within two working days from the day after receipt. Transfer it to the service within seven working days starting the day after the outage is resolved, and provide it to the regulator if requested.</p>

<h2>What information should the site prepare?</h2>
<p>The statutory data requirements cover details such as the waste movement, carrier and receiving site, waste classification, recovery or disposal route, and relevant hazardous-waste information. Use the official receipt-of-waste template and regulations to confirm the required fields for your case. Do not guess waste codes or hazardous status.</p>
<p>Before reporting, identify who captures each fact, where the information comes from, and how missing or rejected data will be corrected. Train relevant staff and test the process using current official instructions.</p>

<h2>Do sites need commercial software?</h2>
<p>Not necessarily. Official guidance describes both the Report Receipt of Waste service and a spreadsheet template; a site can use a combination of spreadsheet and API submissions. If choosing software for API uploads, check that it records and submits the required data, connects to the service API, and has completed the relevant Production Approval Test (PAT) scenarios. Providers must explain which scenarios their product does not support. The GOV.UK provider list is not exhaustive and listed providers self-certify compliance. The list is not an endorsement or a guarantee that a product fits every site, so check suitability against your operation and regulatory needs.</p>

<h2>Check permits and exemptions separately</h2>
<p>A digital reporting requirement does not confirm that a site has the correct environmental authorisation. Depending on the activity, the Environment Agency route may involve a regulatory position statement, a registered exemption, a standard-rules permit or a bespoke permit. Check the current conditions for the specific operation. GOV.UK says waste exemption reforms are scheduled to come into force in January 2027, subject to parliamentary approval; verify the current position before relying on an exemption affected by those changes.</p>

<h2>How can a preflight help?</h2>
<p>RegEvidenceHub Waste is an independent, read-only preflight service. The free human input check confirms that the supplied role, activities and required fields fit the supported intake; it does not run the full regulatory preflight. The optional £19 report evaluates the supplied facts and can show a route, missing information, official-source evidence and a fail-closed review status. It does not submit waste records or provide DWT submission software.</p>
<p>Source changes or missing facts can result in a review-required outcome. Payment does not remove that status or create an Environment Agency decision. The preflight is not legal advice or a substitute for official instructions.</p>

<section class="cta">
<h2>Check the facts for your operation</h2>
<p>Start with the free structured input check. If you need a case-specific evidence-linked review, the England Waste Compliance Preflight Report is £19 for 24-hour access.</p>
<p><a href="{origin}/compliance-report">Open the Waste preflight and report page</a></p>
</section>

<h2>Official sources</h2>
<ul class="sources">
<li><a href="https://www.gov.uk/guidance/digital-waste-tracking-check-if-you-need-to-report-the-waste-you-receive">GOV.UK: Check if you need to report the waste you receive</a></li>
<li><a href="https://www.gov.uk/guidance/report-receipt-of-waste">GOV.UK: Report receipt of waste</a></li>
<li><a href="https://www.gov.uk/government/publications/report-receipt-of-waste-choose-a-software-provider/report-receipt-of-waste-choose-a-software-provider">GOV.UK: Choose a software provider</a></li>
<li><a href="https://www.gov.uk/government/collections/digital-waste-tracking-guidance-and-information">GOV.UK: Digital Waste Tracking guidance and information</a></li>
<li><a href="https://www.gov.uk/guidance/register-your-waste-exemptions">GOV.UK: Register your waste exemptions</a></li>
<li><a href="https://www.gov.uk/government/publications/waste-exemptions-how-to-choose-register-and-pay/waste-exemptions-new-rules-from-january-2027">GOV.UK: Waste exemptions — new rules from January 2027</a></li>
<li><a href="https://www.gov.uk/guidance/waste-environmental-permits">GOV.UK: Waste environmental permits</a></li>
<li><a href="https://www.legislation.gov.uk/uksi/2026/729/contents/made">The Digital Waste Tracking (England) Regulations 2026</a></li>
</ul>
<p class="disclaimer">General information only. Not an Environment Agency approval, legal advice or a determination that a specific site is in scope. Verify your position with the current official sources and the regulator.</p>
</article>
<footer class="meta"><a href="/">RegEvidenceHub Waste home</a> · <a href="/pricing">Pricing</a> · <a href="/support">Support</a></footer>
</main></body></html>"""


def register_seo_guides(server, public_origin: str) -> None:
    from pathlib import Path
    from starlette.responses import FileResponse, HTMLResponse, PlainTextResponse

    @server.custom_route(f"/{INDEXNOW_KEY}.txt", methods=["GET"], include_in_schema=False)
    async def indexnow_verification(_request):
        return PlainTextResponse(INDEXNOW_KEY, headers={"Cache-Control": "public, max-age=86400"})

    @server.custom_route(GUIDE_PATH, methods=["GET"], include_in_schema=False)
    async def receiving_site_guide(_request):
        return HTMLResponse(
            render_receiving_site_guide(public_origin),
            headers={"Cache-Control": "public, max-age=300"},
        )

    @server.custom_route(GUIDE_IMAGE_PATH, methods=["GET"], include_in_schema=False)
    async def receiving_site_guide_image(_request):
        image_path = Path(__file__).parent / "assets" / "england-waste-receiving-site.jpg"
        return FileResponse(
            image_path,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"},
        )
