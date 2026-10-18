# Google Play Internal Testing — RegEvidenceHub Waste

## Product identity

- App: RegEvidenceHub Waste
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

RegEvidenceHub Waste helps you assess a supported England waste activity against the existing regulatory route and evidence rules. Review source-linked findings and reporting or permit-change readiness for the facts supplied. It is not a waste logistics, tracking, or Digital Waste Tracking service, and does not replace regulator decisions or legal advice. A one-time report is available through Google Play; no subscription.

## Local release state (2026-10-18)

- The account owner created this app in the authenticated Play Console on 2026-10-18. App: **RegEvidenceHub Waste**; package: `com.regevidencehub.waste`; Console app ID: `4973757322961384964`. The app-list currently shows Draft with 0 installed audience; no AAB/release has been uploaded and Internal Testing has not started.
- Required Developer Programme Policy and US export-law statements are part of the Console creation flow. The account owner completed app creation; this agent did not submit either declaration. The project still contains no export-classification record, so no independent classification review is recorded here.
- Expected one-time product: `waste_report_one / one-report`. The Console product catalog is not set up or verified yet. CQC and Waste product pages were checked and explicitly show no one-time products, requiring an uploaded Billing-enabled app artifact first. No app-specific signing file or signed AAB is present for this package.
- The existing Android Publisher service-account user is Active and has app-level Play Console access for this app (13 permissions shown). The owner extended the access to all eight RegEvidenceHub apps on 2026-10-18. This is app-level access; account-level permissions remain unselected. No credential/key was created or downloaded, so backend Android Publisher API authentication is still unconfigured.
- The production mobile API check on 2026-10-18 returned HTTP 404: `https://waste.regevidencehub.com/api/mobile/v1/capabilities`. No production deploy was made. The local debug startup/free-flow check remains as recorded below; a Play-installed Billing check is pending.

- Debug APK: `android/app/build/outputs/apk/debug/app-debug.apk` (for Works Watch: `app/build/outputs/apk/debug/app-debug.apk`). It was installed and launched on the attached ADB device; this was a sideloaded free-flow smoke only, not a Play Billing test.
- `:app:testDebugUnitTest :app:assembleDebug`: passed after the release signing configuration change.
- Release signing reads a local properties file outside the repository: `~/.config/regevidencehub/waste-upload.properties`. Override with `-PwasteUploadProperties=/absolute/path/to/file` (see the app Gradle file for the exact property name). Required keys are `storeFile`, `storePassword`, `keyAlias`, and `keyPassword`. Keep the file mode 0600 and the keystore outside the repository. No app-specific signing file was found, so no signed release AAB was generated. Do not reuse the Taxi key for this package.
- Required Play verifier setting: `WASTE_PLAY_SERVICE_ACCOUNT_JSON or WASTE_PLAY_SERVICE_ACCOUNT_FILE; WASTE_RUNTIME_DIR`. This is server-side only; never put it in the Android app. Runtime durability must use persistent Railway volume and existing runtime path /data/waste-rule-mcp.
- Data Safety notes: the client sends user-entered preflight data to the existing backend for processing; purchase tokens are sent to the backend for Play verification and retained server-side only as SHA-256 fingerprints. Recovery credentials are stored by the client using Android Keystore. Review the linked privacy notice and the backend retention rules before completing the Play Data Safety form.

## Internal testing checklist

1. The app package and app-level Play access for the existing Android Publisher service account are verified; provide its credential to the backend runtime through the documented secret setting.
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

The Play Console app entry exists as Draft under `com.regevidencehub.waste` (app ID `4973757322961384964`), but there is no uploaded release or verified one-time product. To reach Internal Testing:

1. Provide app-specific upload signing material securely at the documented external path. Do not reuse the Taxi key. Build and upload a signed AAB.
2. After Play accepts the Billing-enabled AAB, create/verify `waste_report_one / one-report` and any purchase option against the backend/client identifiers. Keep Works Watch as a one-time, non-renewing 30-day purchase.
3. Complete the store listing, app-content/Data Safety declarations, tester setup, and Internal Testing release. Install from the Play opt-in link to verify Billing and recovery.
4. Provide the existing Android Publisher service-account credential to the backend runtime using the documented secret setting; do not place it in Android or the repository.
5. Promote the mobile API route through the normal release process and recheck the HTTPS endpoint; do not use a production deployment solely as a test.

Production release still requires the required closed-test period and Play production-access approval. No public rollout or purchase was made.
