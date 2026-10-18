# Android mobile v1

## Product and supported flow

- App ID: `com.regevidencehub.waste` (target SDK 36, minimum SDK 26).
- Google Play one-time product: `waste_report_one` (consumable). The app shows only the localized price returned by Play ProductDetails.
- The free flow checks England scope, business role, activities and only the additional facts requested by the backend. Questions and answer choices come from `/api/mobile/v1/capabilities` and `/api/mobile/v1/readiness`.
- The decision and current-source gate are `waste_preflight()` and the existing source registry. Android displays bounded route/review/information/source-unverified states and returned evidence references; it does not encode regulatory rules.
- A case is created only after the existing human form validation succeeds. A historical check has no active case reference and cannot attach a purchase.
- A report is available after server verification, contains the existing engine result and has 24-hour case access. This mobile v1 chooses the general route/readiness flow; it does not turn the app into DWT recordkeeping or waste operations software.
- The API is under `/api/mobile/v1`: `capabilities`, `readiness`, `play/redeem`, and `report/recover`. Stripe is not exposed to Android. Web, MCP, Stripe and x402 behavior are otherwise unchanged.

## Purchase verification, idempotency and privacy

The backend verifies Google Play `ProductPurchaseV2`, exact package/product identity and a `PURCHASED`, unconsumed one-time purchase. An absent or invalid service-account verifier returns 503 and cannot create a report. `WASTE_PLAY_SERVICE_ACCOUNT_JSON` or `WASTE_PLAY_SERVICE_ACCOUNT_FILE` configures the verifier. The account needs Android Publisher access to the app.

The API persists only SHA-256 of the purchase token, case reference, the report JSON and whether consumption remains pending. A token binds to one case; a repeated token/case returns the same stored report. A token used on another case or a second grant for the same case is rejected. Report grant commits before Play consumption; retry consumes without rerunning the decision. Recovery requires both the unpredictable case reference and the original Play token. Android stores the token encrypted with a non-exportable Android Keystore AES-GCM key.

The existing durable case store expires unpaid cases after 24 hours by default (`WASTE_CASE_TTL_SECONDS`). When Play verification succeeds, the case expiry is extended to 24 hours from report grant, matching the paid access window. Mobile grants use `WASTE_RUNTIME_DIR/mobile_play_reports.sqlite3`. Local development defaults to `/tmp/waste-rule-mcp`; Railway must mount a persistent volume at `/data` and use the existing `/data/waste-rule-mcp` runtime path (or set `WASTE_RUNTIME_DIR` to a durable mounted directory). Loss of that volume loses report recovery records; do not enable mobile billing in production without a persistent volume and backup/restore plan.

## Store and release blockers

- Create/configure the Play app and `waste_report_one` one-time product, then validate the offer in a Play license-test track.
- Configure the Android Publisher service account and `WASTE_PLAY_SERVICE_ACCOUNT_JSON` or `_FILE` in the production runtime.
- Confirm the Railway persistent volume, backup/restore, privacy notice and retention policy before any production billing enablement.
- Review Play listing, data safety declaration, support/refund contact, localized listing and report access disclosures.
- Exercise purchase, pending/cancelled purchase, process death, restore and consume-retry paths on Play test devices. No Play transaction or deployment was performed for this implementation.

Release network traffic is HTTPS only. Cleartext is enabled in the debug variant only for `127.0.0.1`. Product price is not hard-coded. The app makes no regulator affiliation, permit approval, registration approval or compliance claim.
