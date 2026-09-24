# Waste Distribution Status

Updated: 2026-09-24

## Production

- Version: 0.4.1
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
| Official MCP Registry | DONE | v0.4.1 published and verified from `server.json` |
| OpenAI Plugins | NEEDS_RESYNC_AND_DEMO | Draft/domain/private MCP app are working; v0.3.0 renamed the public tools, so Scan Tools/test tool names must be refreshed before final Submit; reviewer-accessible demo recording URL is still required |
| Glama | LISTED_ONLINE_PENDING_CLAIM | Public connector exists, server responds, and 7 tools are visible. HTTP ownership challenge is deployed at `/.well-known/glama.json`; ownership confirmation and post-v0.3.0 TDQS rescore are pending |
| Smithery | DONE | Listing `liuchanghu2018/uk-waste-rule-mcp` is published. Commercial `/mcp` is healthy with 9 tools. A fresh Smithery release was published on 2026-09-24 after the v0.4.1 schema improvements; do not publish again unless the MCP contract changes. |
| Grok | DONE | Branded payment-free public-AI MCP connector was added and verified on 2026-09-24 |
| PayAI | PARTIAL | x402 compatibility and production smoke pass; latest Bazaar watch on 2026-09-24 19:23 UTC returned `indexed=false` |

## Public-AI v0.3.0 tools

1. `waste_service_info`
2. `waste_rule_catalog`
3. `waste_source_status`
4. `waste_rule_preflight`
5. `waste_carrier_broker_dealer_preflight`
6. `waste_digital_tracking_readiness`
7. `waste_permit_change_preflight`

v0.4.0 extended the same `waste_*` naming family to the commercial `/mcp` surface. v0.4.1 adds strict shared field-level input schemas to the paid commercial decision tools. Prices and x402 settlement behavior are unchanged.

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
- v0.4.1 retains improved routing descriptions and naming consistency and adds strict shared field-level schemas to target CQC-level agent-selection quality
- Ownership challenge token is served from `https://waste.regevidencehub.com/.well-known/glama.json`
- Pending: ownership confirmation and Glama re-score

## Smithery current state

- Publish URL: `https://smithery.ai/servers/new`
- Namespace: `liuchanghu2018`
- MCP Server URL: `https://waste.regevidencehub.com/mcp`
- Recommended Server ID: `uk-waste-rule-mcp`
- Repo metadata: `smithery.yaml` committed and CI-validated
- Listing published at `https://smithery.ai/servers/liuchanghu2018/uk-waste-rule-mcp`; prior quality baseline was 58. A fresh release was published after the v0.4.1 stricter-schema update. Do not publish another release unless the MCP contract changes.

## Next controllable work

1. Confirm Glama ownership once its HTTP challenge is checked/rechecked.
2. Record the refreshed Smithery quality score when Smithery finishes rescoring the latest release.
3. Re-check PayAI Bazaar indexing after external propagation.
4. Return to OpenAI: re-scan current 7 public-AI tools, refresh test tool names if needed, attach demo URL, then Submit.
