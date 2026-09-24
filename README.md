# RegEvidenceHub Waste

Evidence-linked, deterministic regulatory preflight for England waste workflows. The service is designed for AI agents and workflow automation and fails closed when decisive official evidence is stale, changed, unavailable, unreviewed, conflicting, or required facts are missing.

Production origin: `https://waste.regevidencehub.com`

- Commercial MCP: `https://waste.regevidencehub.com/mcp`
- Payment-free public AI MCP: `https://waste.regevidencehub.com/ai/mcp`
- Health: `/health`
- Status: `/status`
- Metrics: `/metrics`
- Agent card: `/.well-known/agent-card.json`
- MCP discovery: `/.well-known/mcp.json`
- x402 metadata: `/.well-known/x402`
- OpenAPI: `/openapi.json`
- LLM guide: `/llms.txt`

## Decision workflows

Commercial decision tools:

- `waste_rule_preflight` — general England waste route and missing-facts preflight — **$0.02 USDC**
- `waste_carrier_broker_dealer_preflight` — carrier/broker/dealer registration, renewal and change lifecycle — **$0.02 USDC**
- `waste_digital_tracking_readiness` — phase-1 Digital Waste Tracking readiness for receiving sites — **$0.03 USDC**
- `waste_permit_change_preflight` — current-vs-proposed operational change impact — **$0.03 USDC**

Free discovery/evidence tools include `waste_service_info`, `waste_rule_catalog`, `waste_source_status`, `waste_source_audit` and `waste_source_registry`.

The separate `/ai/mcp` and `/openai/mcp` public-AI surface is permanently payment-free and read-only. It exposes seven bounded tools: service info, rule catalogue, source status, general preflight, carrier/broker/dealer registration preflight, DWT receipt readiness and permit-change impact.

## Evidence model

The checked-in registry contains eight official GOV.UK / Environment Agency sources. All eight now have reviewed semantic fingerprints. On 24 September 2026, a live production audit confirmed five existing baselines unchanged; the carrier/broker/dealer registration source and waste environmental-permits source were manually reviewed and promoted, and the software-provider source was re-reviewed after GOV.UK updated its provider list without changing the modeled DWT obligation or 1 October 2026 timing.

A source is decision-usable only when:

1. a reviewed semantic SHA-256 baseline exists;
2. the latest observed fingerprint is `UNCHANGED`;
3. the check is inside its freshness window.

`CHANGED`, `FETCH_ERROR`, `MISSING_BASELINE` and stale records fail closed to review.

The service does **not** infer hazardous status, waste codes, permit conditions, exemption eligibility, regulator approval, or legal advice.

## Digital Waste Tracking scope

The DWT workflow models the current England phase-1 receiving-site requirement and keeps later phases separate. It does not create or submit Digital Waste Tracking records.

## Production operations

The production surface provides a RegEvidenceHub-style operations contract:

- `/health` — serving/source/payment state
- `/status` — evidence state, prices and 24h metrics
- `/version` — release/deployment identity
- `/metrics` — aggregate discovery/tool/payment funnel telemetry

Analytics are privacy-minimal: scenario payloads are not intentionally persisted. Owner/test payment activity is separated from external/unattributed activity.

## Payment

x402 v2 is opt-in through `WASTE_PAYMENT_ENFORCED=1`. Production uses Base USDC when configured. Required settings:

- `WASTE_X402_NETWORK`
- `WASTE_X402_PAY_TO`
- `WASTE_X402_FACILITATOR_URL`
- `WASTE_PUBLIC_MCP_URL`

`WASTE_PAYMENT_MODE=maintenance` is a fail-closed kill switch: paid tools remain discoverable but execute no regulatory decision and request no payment.

No buyer private key or seed phrase is handled by this service.

## Source monitoring

Use the durable registry path in production:

```bash
export WASTE_SOURCE_REGISTRY_PATH=/data/waste/source_registry.json
uk-waste-source-monitor --write
```

Only after manual review of a completely successful source audit:

```bash
uk-waste-source-monitor --establish-baseline
```

## Development and CI

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[mcp,dev]' 'x402[evm]==2.21.0'
python -m compileall -q src
pytest -q
```

GitHub CI and the Docker build both run compile + tests before a production image is accepted.

## Boundary

This is regulatory **preflight**, not waste-management execution software. It does not submit carrier registrations, environmental permits, exemptions, DWT records, or regulator filings; it does not approve an operation.
