# Claude MCP Connection — RegEvidenceHub Waste

Date: 2026-09-22

Use the permanent payment-free vendor-neutral endpoint:

- MCP URL: `https://waste.regevidencehub.com/ai/mcp`
- Transport: Streamable HTTP
- Authentication: none
- Scope: England waste-rule and permit-change preflight

Current Anthropic MCP connector documentation:
https://docs.anthropic.com/en/docs/agents-and-tools/mcp-connector

The public AI endpoint exposes five read-only tools:

- `waste_rule_info`
- `list_waste_rules`
- `waste_source_status`
- `waste_rule_preflight`
- `permit_change_impact`

It does not expose Stripe checkout, x402 challenges, purchase links, or paid-upgrade behavior.

For Anthropic API use, configure the server as a URL-based MCP server and use the current MCP connector beta header documented by Anthropic. Keep tool access limited to the public AI inventory above.

This connector provides conservative preflight information only. It does not issue Environment Agency decisions, permits, exemptions or registrations and does not provide legal advice.
