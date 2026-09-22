# Grok / xAI Custom MCP — RegEvidenceHub Waste

Date: 2026-09-22

Use the permanent payment-free vendor-neutral endpoint:

- MCP URL: `https://waste.regevidencehub.com/ai/mcp`
- Connector name: **RegEvidenceHub Waste**
- Description: Evidence-linked England waste-rule and permit-change preflight.
- Authentication: none

Current xAI connector documentation:
https://docs.x.ai/grok/connectors

Grok supports custom MCP connectors that point to a publicly reachable MCP server. The Waste public AI endpoint is intended for that path.

The endpoint exposes five read-only tools:

- `waste_rule_info`
- `list_waste_rules`
- `waste_source_status`
- `waste_rule_preflight`
- `permit_change_impact`

It does not expose Stripe checkout, x402 payment challenges, purchase links, or commercial mutation behavior.

The connector provides conservative England waste-regulatory preflight information, not regulator approval or legal advice.
