# UK Waste Rule & Permit Change-Impact MCP

Local MVP for conservative, official-source-linked screening of waste regulatory routes in England.

This is deliberately not waste-management software. It does not create waste-transfer records, plan routes, manage vehicles, submit Digital Waste Tracking data, determine permit eligibility, or approve an operation.

## Implemented tools

- `waste_rule_preflight`: bounded route and missing-facts preflight.
- `classify_waste_route_tool`: routes activities to permit/exemption, digital-tracking, duty-of-care or review paths.
- `permit_change_impact_tool`: compares current and proposed operating facts and reports fields requiring regulatory review.
- `list_waste_rules_tool`: discovery catalogue.
- `get_source_registry`: official source metadata.
- `waste_source_status`: persisted fingerprint/freshness decision gate.
- `check_waste_sources`: live fetch and fingerprint comparison without changing a reviewed baseline.
- `get_service_status`: local MVP metadata.

The engine is intentionally fail-closed: unknown roles, unknown activities, unsupported nations and missing facts are surfaced as review or incomplete results. It never infers hazardous status, permit conditions, exemption eligibility, waste codes or quantity thresholds.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

To run as an MCP server:

```bash
pip install -e '.[mcp]'
uk-waste-rule-mcp
```

## Evidence boundary

The source registry is in `data/source_registry.json`. Runtime resolution prefers an explicit `WASTE_SOURCE_REGISTRY_PATH`, then the repository/container `data/source_registry.json`, then the wheel-installed shared data file. This keeps editable development, Docker deployment and installed-wheel execution on the same reviewed registry without requiring `PYTHONPATH`. Source checks are local-MVP monitoring only; a production deployment still needs durable runtime state, alerting and shared-platform integration.

## Commercial HTTP/MCP bridge

The optional `uk-waste-rule-mcp-http` entry point exposes free discovery and
source-health endpoints plus the two decision tools. Set
`WASTE_PAYMENT_ENFORCED=1` only with explicit `WASTE_X402_NETWORK`,
`WASTE_X402_PAY_TO`, `WASTE_X402_FACILITATOR_URL`, and HTTPS
`WASTE_PUBLIC_MCP_URL`. The bridge then uses the same x402-v2 MCP/Bazaar
payment boundary as the RegEvidenceHub vertical services. Install the
deployment environment's pinned x402 v2 package separately; it is intentionally
lazy-loaded so local/offline development remains testable.

Prices default to `$0.02` for `waste_rule_preflight` and `$0.03` for
`permit_change_impact`. Payment is disabled by default. No private key is
handled by this service.

## Container deployment

The `Dockerfile` installs the same pinned x402 v2 package used by the current
RegEvidenceHub vertical runtime and starts `uk-waste-rule-mcp-http`. The image
defaults to payment disabled. Only a staging environment with an explicit
`WASTE_PAYMENT_ENFORCED=1`, `WASTE_X402_NETWORK`, `WASTE_X402_PAY_TO`,
`WASTE_X402_FACILITATOR_URL`, and HTTPS `WASTE_PUBLIC_MCP_URL` may enable the
commercial gate. Buyer keys and payment signatures remain client-side.

## Source monitoring

The checked-in registry contains a semantic visible-text SHA-256 baseline for six official GOV.UK sources. A source is decision-usable only when it has a baseline, the latest observed fingerprint is `UNCHANGED`, and the check is within its freshness window. `CHANGED`, `FETCH_ERROR`, `MISSING_BASELINE`, and stale records fail closed to review.

Refresh observed status without changing reviewed baselines:

```bash
uk-waste-source-monitor --write
```

Establish a baseline only after manually reviewing a completely successful fetch:

```bash
uk-waste-source-monitor --establish-baseline
```
