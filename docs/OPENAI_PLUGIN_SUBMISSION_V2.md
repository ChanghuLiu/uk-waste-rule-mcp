# OpenAI Plugin Submission V2 — RegEvidenceHub Waste

Prepared: 2026-09-24

This is the current OpenAI Platform **With MCP** submission packet for the branded RegEvidenceHub Waste public AI surface.

## Submission

- Type: **With MCP**
- MCP URL mode: **Universal**
- Authentication: **None**
- Custom UI: **None**
- Production MCP URL: `https://waste.regevidencehub.com/openai/mcp`
- Commercial MCP remains separate at `https://waste.regevidencehub.com/mcp`
- Import file: `chatgpt-app-submission.json`

## App Info

- Display name: `RegEvidenceHub Waste`
- Subtitle: `England waste compliance preflight`
- Category: `BUSINESS`
- Website: `https://regevidencehub.com/products/waste.html`
- Product page: `https://waste.regevidencehub.com/waste-rule-preflight`
- Support: `https://waste.regevidencehub.com/plugin/support`
- Privacy: `https://waste.regevidencehub.com/plugin/privacy`
- Terms: `https://waste.regevidencehub.com/plugin/terms`
- Support email: `launchcircle.server@gmail.com`

## Tool snapshot

Expected Scan Tools result: exactly seven tools:

1. `waste_rule_info`
2. `list_waste_rules`
3. `waste_source_status`
4. `waste_rule_preflight`
5. `carrier_broker_dealer_registration_preflight`
6. `digital_waste_tracking_receipt_readiness`
7. `permit_change_impact`

Every tool must scan with `readOnlyHint=true`, `openWorldHint=false`, and `destructiveHint=false`.

The public-AI endpoint is payment-free and must not expose x402, Stripe, checkout, purchase links, or commercial payment credentials.

## Starter prompts

1. `We receive non-hazardous controlled waste at our permitted site in England. What waste-rule route should we check first?`
2. `Our England business transports other companies' waste and needs a new waste carrier registration. What should we check?`
3. `Our permitted receiving site in England accepts controlled waste. Are we ready for Digital Waste Tracking receipt reporting?`

## Testing packet

The import JSON contains exactly five positive and three negative cases.

Positive coverage: general waste-rule routing; carrier/broker/dealer registration lifecycle; Digital Waste Tracking receiving-site readiness; permit-change impact; official-source health.

Negative coverage: no inferred hazardous classification or EWC code; no regulatory filing/submission; no guaranteed legal conclusion from unseen permit conditions.

## Domain verification

The service exposes `/.well-known/openai-apps-challenge`. When the portal issues a token, set that exact value in production variable `OPENAI_APPS_CHALLENGE` and verify:

`https://waste.regevidencehub.com/.well-known/openai-apps-challenge`

The endpoint returns only the configured token as `text/plain`.

## Review boundary

The submitted surface is read-only regulatory preflight and evidence-status guidance. It does not expose the commercial x402 endpoint, request payment, submit to the Environment Agency, determine hazardous status or waste codes from insufficient facts, issue permits/exemptions/registrations, or provide legal advice.

## Portal steps

1. Create a new **With MCP** plugin.
2. Upload `chatgpt-app-submission.json` on the Info step if import is offered; otherwise copy the same packet fields manually.
3. Select the verified developer/business identity already used for the RegEvidenceHub submissions.
4. Enter `https://waste.regevidencehub.com/openai/mcp` as the Universal MCP URL.
5. Complete domain verification if requested.
6. Select **Scan Tools** and confirm the exact seven-tool snapshot above.
7. Add the three starter prompts.
8. Confirm the exact five positive and three negative test cases from the import packet.
9. Set availability and policy attestations consistently with the existing RegEvidenceHub submissions.
10. Submit for review.

Do not claim directory availability until OpenAI review is approved and the plugin is subsequently published.
