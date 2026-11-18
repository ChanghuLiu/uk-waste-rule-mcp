# uk-waste-rule-mcp analytics memory release — 2026-11-17

## Deployed and verified
- Isolated branch codex/analytics-memory-20261117; basea5b8802ba61bb902190fe0f0a8958f615c61cfcd. Original dirty worktree preserved.
- Rollback existing Railway deployment4825d9dc-0a2b-49ab-bebf-9f6663b3f133; preserve existing volumes/variables/domains.
- Local full tests 79passed; Docker build and configured build gates pass.100000-event controlled aggregate output exactly matches old implementation; peak47848→24180KiB (~23.1MiB reduction).
- Exact old/new aggregate hash parity on a read-only live snapshot verified, raw event/client data not exported. Evidence validation/memory-20261117/live-parity.json; baseline-runtime.json.
- Live Python source matches exact base; Taxi uses /app/service/src rather than /app/src.
- Streaming reads/incremental aggregation only; all event history, source freshness/review flags, payment enforcement, attribution and retention preserved. No source review updates, real payments or business tool execution included.
- DONE: deployment9f6da127-d625-485d-bad0-e989c531eda6 SUCCESS,1/1 running,0crashed. Uploaded source bytes match0a7e44d; source snapshot is verified by hashes, not claimed Git-pinned Railway metadata.8live checks+3repeathealth pass, MCP discovery/free metadata and unpaid HTTP402; no payment proof sent or paid business result obtained. Process PID1 RSS137.3→142.5MiB after loading reports. Different uptime/restart effects apply; no invoice saving claim.

- Source remains on isolated pushed branch; drafthttps://github.com/ChanghuLiu/uk-waste-rule-mcp/pull/37. Not merged to avoid stopped staging reactivation. Future main-source releases must incorporate the recorded source commit. All four selected staging execution services independently confirmed Offline, no active deployments/pending work.
- Waste loaded process RSS did not decline in this sample (137.3→142.5MiB); do not count it as demonstrated production savings. Controlled100000-row peak allocation reduction remains valid.
