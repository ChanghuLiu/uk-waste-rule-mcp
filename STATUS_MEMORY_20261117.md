# uk-waste-rule-mcp analytics memory release — 2026-11-17

## Ready, deployment pending
- Isolated branch codex/analytics-memory-20261117; basea5b8802ba61bb902190fe0f0a8958f615c61cfcd. Original dirty worktree preserved.
- Rollback existing Railway deployment4825d9dc-0a2b-49ab-bebf-9f6663b3f133; preserve existing volumes/variables/domains.
- Local full tests 79passed; Docker build and configured build gates pass.100000-event controlled aggregate output exactly matches old implementation; peak47848→24180KiB (~23.1MiB reduction).
- Exact old/new aggregate hash parity on a read-only live snapshot verified, raw event/client data not exported. Evidence validation/memory-20261117/live-parity.json; baseline-runtime.json.
- Live Python source matches exact base; Taxi uses /app/service/src rather than /app/src.
- Streaming reads/incremental aggregation only; all event history, source freshness/review flags, payment enforcement, attribution and retention preserved. No source review updates, real payments or business tool execution included.
- Post-deployment health/status/metrics/MCP/unpaid verification and loaded memory pending. No invoice savings claim.
