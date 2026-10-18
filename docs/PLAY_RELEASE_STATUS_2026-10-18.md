# Android Play readiness status — 2026-10-18

## Verified locally

- Product: Waste; branch/worktree kept local, no push or merge.
- Android: `:app:testDebugUnitTest :app:assembleDebug` passed after optional upload-signing support was added. Debug APK: `android/app/build/outputs/apk/debug/app-debug.apk`.
- Backend Python suite: 77 passed.
- ADB: attached Huawei CLT-L04 (`DXU7N18815000043`); APK installed and launcher activity opened. The on-device startup smoke passed. Billing remains pending an Internal Testing install from Google Play.
- Release target/compile SDK: 36; version: 1.0.0 / code 1; BillingClient: 9.1.0; production API: HTTPS. The official Play target policy currently requires API 36 for new apps and updates from 2026-08-31; 9.1.0 is the current listed Google Play Billing release.
- Privacy, terms, and support pages returned HTTP 200 at the URLs in `docs/PLAY_INTERNAL_TESTING.md`.
- Upload signing is configured to read credentials from an external mode-0600 properties file. No app-specific properties or upload keystore was present, so no release AAB was generated.
- `.github/workflows` diff: empty. No production deploy, Play purchase, email, or customer contact occurred.


## Production mobile API check

- Read-only GET `https://waste.regevidencehub.com/api/mobile/v1/capabilities` returned HTTP 404 (`Not Found`) on 2026-10-18. The mobile API route is not currently available on the production host, so this build cannot complete a production-backed flow until the backend route is promoted through the normal release process. No deploy was performed.
- Waste phone check: the debug app starts; production-backed behavior remains blocked by the 404 above. No purchase was initiated.

## Play Console state

not inspected: Play Console browser session unavailable; app/product/service-account state unknown

The Chrome automation could not enumerate browser tabs because the browser request-header policy failed. Play Console app/product/service-account state remains unknown. No account credentials or service-account key was created or downloaded.

## Next human action

Open the existing Play Console app or create package com.regevidencehub.waste; verify/create waste_report_one / one-report, grant the existing Android Publisher service account access, and configure WASTE_PLAY_SERVICE_ACCOUNT_JSON or _FILE in Railway.

Then add internal/license testers, publish only to Internal Testing, install from Play, and run the billing recovery/consume tests in `docs/PLAY_INTERNAL_TESTING.md`.
