# Android mobile v1 status

## Implementation

Implemented in the isolated `codex/android-client-v1` worktree. Native Kotlin and Compose Material 3 app ID is `com.regevidencehub.waste`, target SDK 36 / minimum SDK 26, with BillingClient 9.1.0 and product `waste_report_one`.

The selected flow is the existing free England waste route and evidence readiness preflight. The server asks for nation, role, activity and engine-required facts one question at a time. It delegates all decisions and source freshness checks to the existing Waste engine. The Android client displays structured findings and source references and offers a report only after the existing human form accepts the facts.

## Durability and privacy

Play purchase verification uses Google Play ProductPurchaseV2. The backend persists token SHA-256 only, binds each token to one case, grants the stored report before consume, and retries consume without re-running the decision. Unpaid cases expire after 24 hours; a verified purchase extends its case and report access for 24 hours from grant. Expired report JSON is scrubbed at startup and on mobile API requests; its token digest remains to preserve one-case binding. Android recovery tokens are encrypted with Android Keystore AES-GCM. Production requires `WASTE_PLAY_SERVICE_ACCOUNT_JSON` or `WASTE_PLAY_SERVICE_ACCOUNT_FILE`, plus the existing durable Railway runtime volume at `/data/waste-rule-mcp` (or a configured persistent `WASTE_RUNTIME_DIR`).

## Verification and remaining release gates

- Backend mobile, human report, engine, source-refresh and HTTP/shared-case focused tests: **38 passed**.
- Full Python suite: **77 passed**.
- `:app:testDebugUnitTest` and `:app:assembleDebug`: **passed**; one Android unit test passed.
- ADB phone check: pending; `adb devices -l` found no attached devices.
- Play test-track purchase, restore and consume-retry validation: pending.
- Play listing/product setup, service-account configuration, Railway persistent-volume confirmation and privacy/data-safety review: pending.

No push, pull request, workflow change, deployment, Play Console action or payment was performed.
