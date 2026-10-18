# Google Play Internal Testing — Waste Route Preflight

## Product identity

- App: Waste Route Preflight
- Package: `com.regevidencehub.waste`
- In-app product / option: `waste_report_one` / `one-report` (one-time purchase)
- Release API: https://waste.regevidencehub.com (HTTPS)
- Privacy: https://waste.regevidencehub.com/privacy
- Terms: https://waste.regevidencehub.com/terms
- Support: https://waste.regevidencehub.com/support
- Play Billing Library: 9.1.0; target SDK 36; version 1.0.0 (code 1)

## Store listing draft

**Short description**

Review England waste routes, evidence gaps, and permit-change readiness.

**Full description**

Waste Route Preflight helps you assess a supported England waste activity against the existing regulatory route and evidence rules. Review source-linked findings and reporting or permit-change readiness for the facts supplied. It is not a waste logistics, tracking, or Digital Waste Tracking service, and does not replace regulator decisions or legal advice. A one-time report is available through Google Play; no subscription.

## Local release state (2026-10-18)

Unknown: no Play Console session or app/product listing was exposed for inspection. Verify or create the app/package and one-time product, then grant the existing Android Publisher service account access.

- Debug APK: `android/app/build/outputs/apk/debug/app-debug.apk` (for Works Watch: `app/build/outputs/apk/debug/app-debug.apk`). It was installed and launched on the attached ADB device; this was a sideloaded free-flow smoke only, not a Play Billing test.
- `:app:testDebugUnitTest :app:assembleDebug`: passed after the release signing configuration change.
- Release signing reads a local properties file outside the repository: `~/.config/regevidencehub/waste-upload.properties`. Override with `-PwasteUploadProperties=/absolute/path/to/file` (see the app Gradle file for the exact property name). Required keys are `storeFile`, `storePassword`, `keyAlias`, and `keyPassword`. Keep the file mode 0600 and the keystore outside the repository. No file was found, so no signed release AAB was generated.
- Required Play verifier setting: `WASTE_PLAY_SERVICE_ACCOUNT_JSON or WASTE_PLAY_SERVICE_ACCOUNT_FILE; WASTE_RUNTIME_DIR`. This is server-side only; never put it in the Android app. Runtime durability must use persistent Railway volume and existing runtime path /data/waste-rule-mcp.
- Data Safety notes: the client sends user-entered preflight data to the existing backend for processing; purchase tokens are sent to the backend for Play verification and retained server-side only as SHA-256 fingerprints. Recovery credentials are stored by the client using Android Keystore. Review the linked privacy notice and the backend retention rules before completing the Play Data Safety form.

## Internal testing checklist

1. Confirm the Play app exists with the exact package above; inspect app access for the existing Android Publisher service account.
2. Confirm the product and option IDs above match the backend. Confirm it is a one-time purchase; Works Watch must be non-renewing, and FactoryTalk/OPC UA packs retain the stated quota and 365-day expiry.
3. Add internal testers and license testers. Publish an Internal Testing release, then install it from the Play opt-in link.
4. Verify the localized price is read from Play `ProductDetails`, then test purchase, pending/cancelled purchase, app restart/recovery, idempotent replay, grant-before-consume, and consume retry.
5. Verify the release listing, privacy/terms/support links, Data Safety form, phone screenshots, and review declarations. Do not submit a production rollout as part of internal testing.

## Phone screenshots and smoke checklist

- Capture a clean home screen with the app name and independent-preflight scope visible.
- Capture one representative input/check screen with no real customer or sensitive data.
- Capture the free result with source/findings and any uncertainty or unsupported-input notice visible.
- Capture the purchase offer only from an Internal Testing install after Play returns its localized `ProductDetails` price; do not use a sideloaded build for this screenshot.
- Capture the recovered report or watch state after a license-tester flow, with test data only.
- Before store upload, review screenshots for personal information, debug banners, stale prices, and claims of approval, certification, compliance, or official affiliation.
- Smoke on a physical phone: cold launch, rotate/relaunch where supported, navigate all tabs, perform one safe free flow, confirm offline/API errors are understandable, background/restore, and check `adb logcat` for crashes. Do not make a real purchase.

## Console access and next human action

Console inspection was not possible: the available Chrome browser automation failed to expose tabs, and no Play Console connector is available. Unknown: no Play Console session or app/product listing was exposed for inspection. Verify or create the app/package and one-time product, then grant the existing Android Publisher service account access.
