# Customer-flow validation — 4 October 2026

Purchase and recovery handlers now reject email addresses with a missing local part
or domain before contacting the commercial service. Existing field feedback and
submitted-answer preservation apply.

Local regression checks exercise both handlers’ rejection predicates. The full
product suite is run with its existing test runtime. Staging deployment status
and browser acceptance are recorded in the portfolio progress record; local tests
do not establish live Stripe, live mail delivery or visual browser acceptance.

Production is unchanged.

The new guided-form tests cover all four existing strict scenario schemas,
explicit unknowns, conditional carrier facts, invalid choices, date and text
bounds, known facts for both permit operations, inactive controls, submitted
answer escaping/preservation and checkout creation without customer JSON.
Legacy JSON checkout and shared execution tests remain in the full suite.

## Source failure boundary

The 4 October official-source audit observed five changed fingerprints out of
eight sources. Reviewed hashes remain unchanged. When evidence is changed,
unavailable, stale or missing, registration and tracking results now withhold
determinate registration requirements, fee routes, lifecycle obligations,
phase-1 scope, mandatory dates and reporting timing. The supplied action and
facts remain available for review. A required source absent from the registry
now blocks the decision rather than disappearing from the freshness check.
Seventeen new regression cases check these boundaries and isolation between
tracking and registration dependencies.

Current official guidance also describes receiving-site exceptions, digitally
excluded reporting and pipeline timing. Those special branches are not fully
modeled by the current bounded readiness input and remain a release review
item. This source review does not accept changed baselines or expand the
modeled regulatory scope.
