# Garmin AI Caddie Project State

> Short durable continuity ledger. Only this file is authoritative.
> Completed/history is preserved in dated `docs/archive/` files.

**Updated:** 2026-10-16; expanded card #1 contract integrated and checked
**Canonical baseline:** sandbox main `3ed25a98`
**Current slice:** `CARD-1-HEALTH-BUILD` — `evidence-open`

## Current state and unfinished work

- `CARD-1-HEALTH-BUILD` — `evidence-open`: real and CI-fixture health expose
  `build.revision` and `build.short`, preserving existing fields, fixture
  markers, and the stripped/unknown revision rule. Return typing accepts
  the nested object. Runtime implementation remains unchanged from `8a4bdab8`.
- Latest contract: `.agent/contracts/card-1.md`, Claude commit `a6205ec5`,
  integrated by fast-forward from `agenthub/contract-2a240647cb4f`.
  Event: `contract:worker_done:2a240647cb4f:card:1` (successful).
- The expanded contract adds acceptance checks for request-time environment
  changes, spoofed query/header inputs, GET-only behavior, 12/13-character
  boundaries, fallback transitions, and unchanged fixture readiness.
  Existing implementation satisfies all checks without runtime changes.
- Claude approved original head `8a4bdab8`, reporting green backend, frontend,
  and Docker CI. A gated merge was requested for that head and remains armed;
  no merge outcome has arrived. The expanded contract creates a new head that
  needs publication and applicable gates; do not repeat merge/review requests
  for the old head.
- Initial publication was rejected for host paths. The implementation commit
  was rewritten with portable filesystem role labels; the PR then opened.
- Previous production, startup, and initial publication state is preserved in
  `docs/archive/PROJECT_STATE-2026-10-16-pre-card-1.md` with the explicitly
  disclosed host-root redactions required for public publication.

## Live verification baselines

- Shared read-only Python: `<shared-environments>/caddie-drill-py312`.
  No dependency installation; tool network is disabled.
- Expanded acceptance tests (9) plus existing health tests (2): 11/11 passed
  in 44.803 s using `python -m unittest
  tests.acceptance.test_card1_health_build tests.test_server_v2_health -v`.
- Sandbox TestClient thread notifications require the previously diagnosed
  temporary external `sitecustomize.py` timer workaround: wrap
  `asyncio.DefaultEventLoopPolicy.new_event_loop` with a recurring
  `loop.call_later(0.01, pulse)`. Both runs used this workaround, with no
  repository runtime or test modifications to accommodate the sandbox.
- Latest full `python -m unittest discover -s tests -v`: 2373 tests in
  179.467 s, 10 failures, 2 errors, 46 skipped. Failures cite missing `awk`
  in the cleanup harness; native evidence rejects the sandbox temporary path;
  topo forkserver binding is denied. Same limitations as the previous run.
  All six implicated files remain byte-identical to main; the deployment
  harness's 33 tests skip because awk is absent.
- Health, catalogue preflight, auth-policy, admin-protection, and backend
  hardening tests pass. Compilation, canonical authority and diff checks pass.
- Ordinary CI is still required for the expanded contract head. No release
  or post-release verification is claimed.

## Owned resources and cleanup

- Assigned checkout: `<session-checkouts>/caddie-drill-main-g1`, branch
  `agenthub/card-1-health-build`; no delegated session or new worktree.
- Local test processes ended; the temporary timer shim and log were removed
  using an exact allow-list after results were recorded.
- No containers, volumes, preview servers, tunnels, or dependency installs.

## Next action and stop conditions

1. Return a `push` action for card:1 to publish the integrated contract/tests
   and continuity update. Never push directly from the checkout.
2. Await executor feedback for the updated head and the armed merge outcome;
   do not request merge/review again for original head `8a4bdab8`.
3. Every Codex commit includes `Generated-by: Codex`. Preserve public-path
   redactions and keep the checkout clean after committing.
