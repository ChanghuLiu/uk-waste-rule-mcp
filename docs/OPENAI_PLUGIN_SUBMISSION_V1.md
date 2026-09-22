# OpenAI Plugin Submission V1 — RegEvidenceHub Waste

Date: 2026-09-22

## Submission target

OpenAI Plugin submission portal / remote MCP review.

- Display name: **RegEvidenceHub Waste**
- Remote MCP URL: `https://waste.regevidencehub.com/openai/mcp`
- Transport: Streamable HTTP
- Authentication: none
- Product page: `https://waste.regevidencehub.com/waste-rule-preflight`
- Privacy: `https://regevidencehub.com/privacy/`
- Terms: `https://regevidencehub.com/terms/`
- Support: `https://regevidencehub.com/support/`

Official review guidance:
- https://developers.openai.com/plugins/deploy/app-review
- https://developers.openai.com/plugins/deploy/submission

## Public-review boundary

The OpenAI endpoint is permanently payment-free and isolated from the commercial `/mcp` endpoint.

It exposes only:

1. `waste_rule_info`
2. `list_waste_rules`
3. `waste_source_status`
4. `waste_rule_preflight`
5. `permit_change_impact`

All five tools advertise:
- `readOnlyHint=true`
- `destructiveHint=false`
- `idempotentHint=true`
- `openWorldHint=false`

The endpoint does not expose x402, Stripe checkout, purchase links, payment challenges, or commercial mutation behavior.

## Review checklist

Before submission:

1. Public HTTPS endpoint is reachable.
2. MCP initialize succeeds.
3. `tools/list` returns exactly the five public-review tools.
4. Tool annotations are present and match the read-only boundary.
5. Structured-output metadata is present.
6. Server instructions describe England scope, fail-closed evidence behavior and non-approval boundary.
7. Product page and shared privacy/terms/support pages return HTTP 200.
8. `/.well-known/openai-apps-challenge` returns the exact configured challenge token when enabled.
9. Five positive and three negative test cases pass.
10. No public-AI response exposes x402, Stripe checkout, paid upgrade steering or payment credentials.
11. Publisher identity/organization verification and required app-management permissions are complete in the OpenAI platform portal.

Do not claim public directory availability until OpenAI review is approved.
