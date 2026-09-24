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
| OpenAI Plugins | PORTAL_RESYNC_AND_DEMO | Repo submission packet is fully synced to the current seven `waste_*` public-AI tools; the existing portal draft still needs Scan Tools/test-case refresh, then a reviewer-accessible demo recording URL before final Submit |
| Glama | DONE | Public connector is live and claimed. Server responds, 7 tools are visible, Admin/Analytics access is active, and TDQS is A / 4.3 as of 2026-09-24. |
| Smithery | DONE | Listing `liuchanghu2018/uk-waste-rule-mcp` is published. Commercial `/mcp` is healthy with 9 tools. A fresh Smithery release was published on 2026-09-24 after the v0.4.1 schema improvements; do not publish again unless the MCP contract changes. |
| Grok | DONE | Branded payment-free public-AI MCP connector was added and verified on 2026-09-24 |
| PayAI | EXTERNAL_INDEX_PENDING | x402 compatibility and production smoke pass; latest Bazaar watch on 2026-09-24 19:23 UTC returned `indexed=false` with no Waste tools listed |

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
- Repo packet, tool justifications, five positive cases and three negative cases are synced to the current seven-tool public-AI contract
- Portal draft still needs one Scan Tools/test-name refresh because it was created before the tool rename
- Remaining submission blocker after portal refresh: reviewer-accessible demo recording URL

## Glama current state

- Connector: `io.github.ChanghuLiu/uk-waste-rule-mcp`
- Listing: live
- Server health shown by Glama: responding
- Tool count: 7
- Current TDQS: A / 4.3 (CQC reference: A / 4.2)
- Tool routing descriptions, naming consistency, and strict field-level schemas now meet the intended CQC-level agent-selection quality target
- Ownership verified via `https://waste.regevidencehub.com/.well-known/glama.json`
- Admin and Analytics access are active

## Smithery current state

- Publish URL: `https://smithery.ai/servers/new`
- Namespace: `liuchanghu2018`
- MCP Server URL: `https://waste.regevidencehub.com/mcp`
- Recommended Server ID: `uk-waste-rule-mcp`
- Repo metadata: `smithery.yaml` committed and CI-validated
- Listing published at `https://smithery.ai/servers/liuchanghu2018/uk-waste-rule-mcp`; the UI currently shows Quality Score 58. Multiple Recent Releases are history for this one listing, not duplicate products. Do not publish again unless the MCP contract changes.

## Next controllable work

1. Wait for PayAI Bazaar external indexing; do not self-pay or mutate the product solely to force discovery.
2. Return to OpenAI portal: re-scan the current 7 public-AI tools and refresh the draft test tool names.
3. When a reviewer-accessible demo recording URL is available, attach it and Submit.


## 2026-09-24 distribution verification evidence

- Smithery: production proxy logs show `SmitheryBot/1.0 (+https://smithery.ai)` POST requests to `/mcp` returning HTTP 200 after publish. Multiple entries in Smithery Recent Releases are release history for the same server, not duplicate public listings.
- Grok: production proxy logs show `grok-connectors-manager/0.1.0` POST requests to `/ai/mcp` returning HTTP 200/202, and the Grok Plugins UI shows RegEvidenceHub Waste as Added.
- Glama: `/.well-known/glama.json` returns HTTP 200; ownership is confirmed by full Admin/Analytics/TDQS access. Current TDQS is A-grade with six tools evaluated at an average 4.5/5 and the seventh queued.


## Glama TDQS checkpoint — 2026-09-24

Ownership is verified and the connector administration pages are available. Current Glama TDQS snapshot:

- Average: 4.5/5 across 6 evaluated tools
- waste_digital_tracking_readiness: A, 4.1/5
- waste_permit_change_preflight: A, 4.5/5
- waste_rule_catalog: A, 4.5/5
- waste_source_status: A, 4.5/5
- waste_carrier_broker_dealer_preflight: A, 4.7/5
- waste_service_info: A, 4.7/5
- waste_rule_preflight: queued

No further schema/name churn should be made solely for TDQS until the queued tool is evaluated.


## External discovery traffic checkpoint — 2026-09-24

Production proxy logs show genuine third-party/indexer activity beyond owner tests:

- SmitheryBot hit commercial `/mcp` repeatedly with HTTP 200.
- `grok-connectors-manager/0.1.0` hit `/ai/mcp` with successful MCP 200/202 responses.
- Glama ownership challenge requests hit `/.well-known/glama.json` with HTTP 200.
- Additional discovery traffic reached the public-AI MCP from MCPHub, Talandor, Golemreach and research probes.
- PayAI facilitator support checks return HTTP 200, but Bazaar discovery still did not list the Waste endpoint at the latest 19:23 UTC watch.

Interpretation: distribution discovery is active; these machine/indexer hits are not counted as paying customers or revenue.
