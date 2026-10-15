# Purchase UI acceptance before user journeys

User instruction, 2026-10-03: finish the UI of every user-facing page before asking the owner to test its flow.

Apply to purchase forms, paid reports, recovery requests and confirmations, recovered-link loading and error states, checkout cancellation, and payment pending/unavailable pages. Before each next product journey, inspect its pages, fix unstyled pages, and verify desktop and mobile layouts.

Use readable spacing, contrasting text, clear headings, full-width form controls where appropriate, and visible keyboard focus. Present decision findings, next steps, limitations, fees and official evidence as readable content. Preserve the complete deterministic result in collapsed JSON. Payment verification must not imply regulatory approval. Mark registration fees separately from report prices. Recovery is optional and collapsed on the report page. Explain the actual access period.

Keep authentication, entitlement checks, recovery-link security, and decision semantics intact. Escape all report content, allow only HTTP(S) evidence links, and avoid putting tokens into visible content or logs.

Verify success, review-required, missing information, expired/unavailable, and cancellation states before handoff. The owner uses local Chrome; provide exact URLs and clearly distinguish Test/Sandbox checkout from Live payments.
