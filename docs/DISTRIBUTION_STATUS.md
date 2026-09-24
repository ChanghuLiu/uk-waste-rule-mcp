# Waste Distribution Status

Updated: 2026-09-24

## Production

- Version: 0.3.0
- Canonical commercial MCP: https://waste.regevidencehub.com/mcp
- Payment-free public AI MCP: https://waste.regevidencehub.com/ai/mcp
- OpenAI MCP alias: https://waste.regevidencehub.com/openai/mcp
- Railway project: mcp-production
- Branded TLS/domain: active
- Payment: x402 v2 on Base mainnet
- Official-source health: production gate enabled
- Discovery source attribution: enabled for Smithery, Glama, OpenAI, Claude, Grok, Official Registry, PayAI and bounded unknown-machine traffic
- Public-AI contract: seven read-only tools with a consistent `waste_*` naming family

## Distribution

| Channel | Status | Current gate |
| --- | --- | --- |
| Official MCP Registry | DONE | v0.3.0 published and verified from `server.json` |
| OpenAI Plugins | NEEDS_RESYNC_AND_DEMO | Draft/domain/private MCP app are working; v0.3.0 renamed the public tools, so Scan Tools/test tool names must be refreshed before final Submit; reviewer-accessible demo recording URL is still required |
| Glama | LISTED_ONLINE_PENDING_CLAIM | Public connector exists, server responds, and 7 tools are visible. HTTP ownership challenge is deployed at `/.well-known/glama.json`; ownership confirmation and post-v0.3.0 TDQS rescore are pending |
| Smithery | UI_READY_TO_PUBLISH | `smithery.yaml` points to the commercial `/mcp`; publish page is available under the existing `liuchanghu2018` namespace; final form submit is pending |
| Grok | READY_TO_CONNECT | Branded payment-free public-AI MCP is ready; connector add/verification is pending |
| PayAI | PARTIAL | x402 compatibility and production smoke pass; last Bazaar watch on 2026-09-24 16:13 UTC returned `indexed=false` |

## Public-AI v0.3.0 tools

1. `waste_service_info`
2. `waste_rule_catalog`
3. `waste_source_status`
4. `waste_rule_preflight`
5. `waste_carrier_broker_dealer_preflight`
6. `waste_digital_tracking_readiness`
7. `waste_permit_change_preflight`

The v0.3.0 naming cleanup is intentionally limited to the public-AI/directory surface. Existing commercial `/mcp` tool names and x402 behavior remain unchanged.

## OpenAI current state

- Submission packet: 7 tools, 5 positive cases, 3 negative cases
- Domain verification challenge endpoint: working
- Private test plugin: working in ChatGPT Work through registered MCP App
- Public-AI tool contract changed after the draft was first scanned; re-scan the v0.3.0 tools before submission
- Remaining external blocker after re-scan: reviewer-accessible demo recording URL

## Glama current state

- Connector: `io.github.ChanghuLiu/uk-waste-rule-mcp`
- Listing: live
- Server health shown by Glama: responding
- Tool count: 7
- Pre-v0.3.0 TDQS: D / 1.5
- v0.3.0 improved routing descriptions, strict input schemas and naming consistency to target the CQC-level agent-selection quality
- Ownership challenge token is served from `https://waste.regevidencehub.com/.well-known/glama.json`
- Pending: ownership confirmation and Glama re-score

## Smithery current state

- Publish URL: `https://smithery.ai/servers/new`
- Namespace: `liuchanghu2018`
- MCP Server URL: `https://waste.regevidencehub.com/mcp`
- Recommended Server ID: `uk-waste-rule-mcp`
- Repo metadata: `smithery.yaml` committed and CI-validated
- Pending: final UI submit, then add the final Smithery listing backlink to the Waste discovery surface

## Next controllable work

1. Confirm Glama ownership once its HTTP challenge is checked/rechecked.
2. Complete the Smithery publish form and capture the final listing slug.
3. Add the final Smithery backlink to production and verify crawler discovery.
4. Add/verify the Grok connector.
5. Re-check PayAI Bazaar indexing.
6. Return to OpenAI: re-scan v0.3.0 tools, refresh test tool names, attach demo URL, then Submit.
