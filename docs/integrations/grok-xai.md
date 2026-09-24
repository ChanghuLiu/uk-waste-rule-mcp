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

The endpoint exposes seven read-only tools:

- `waste_service_info`
- `waste_rule_catalog`
- `waste_source_status`
- `waste_rule_preflight`
- `waste_carrier_broker_dealer_preflight`
- `waste_digital_tracking_readiness`
- `waste_permit_change_preflight`

It does not expose Stripe checkout, x402 payment challenges, purchase links, or commercial mutation behavior.

The connector provides conservative England waste-regulatory preflight information, not regulator approval or legal advice.
