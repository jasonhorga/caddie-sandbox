HISTORICAL ARCHIVE — NON-AUTHORITATIVE

> Publication redaction (2026-10-16): host-specific filesystem roots
> are replaced with portable role labels following the public-repository
> leak rejection. Historical content is otherwise preserved.

# Garmin AI Caddie Project State

> Short durable continuity ledger. Only this file is authoritative.
> Completed/history is preserved in dated `docs/archive/` files.

**Updated:** 2026-10-15 22:23 UTC; #429 reviewed, merged and branch deleted
**Canonical baseline:** main `ec8cddfe1e9ed517202acc62750f7f72b01068e4`
**Current slice:** `PR-FEEDBACK-CONTINUOUS` — `in-progress`

## Current state and unfinished work

- `BACKEND-READINESS-428` — `done`: revision `e1243ba9` deployed as
  `aicaddie-release-e1243ba9-production-20261015`; authenticated readiness
  reports `runtimeStatus=ready`, `mobile_events=ready`, and
  `mobile_package=ready`. Matching sync image ran; log ended `sync ok`,
  `done`. Issue comment:
  https://github.com/jasonhorga/garmin-ai-caddie/issues/428#issuecomment-6194494187
- `TESTFLIGHT-89` — `done`: CD run
  https://github.com/jasonhorga/garmin-ai-caddie/actions/runs/38745733734
  completed without degraded-readiness opt-in. Uploaded `0.1.0 (89)`;
  provenance/backend revision match; IPA SHA-256
  `5027d1e0c8063ef69a4e84be92300b9a6b64491edd4e2570c6f0417de8b1fb59`.
  IPA contains iOS and WatchKit targets, both build 89.
- `APPLE-READONLY-89` — `done`: check
  https://github.com/jasonhorga/garmin-ai-caddie/actions/runs/38750039805
  reports build `VALID`, `internalState=IN_BETA_TESTING`,
  `usesNonExemptEncryption=false`; build 89 is in the existing internal
  group. Apple processed `com.ai-caddie.mobile` and
  `com.ai-caddie.mobile.watchkitapp`.
- #425 and #427 are merged/deployed. #417 remains an evidence issue;
  #418 is draft/evidence-open; #420 awaits the requested 49 mm transitions;
  #421 is done: exact head `62201d90` passed 19/19 provenance tests,
  `bash -n`, and `git diff --check`; PASS comment
  https://github.com/jasonhorga/garmin-ai-caddie/pull/421#issuecomment-6200552328;
  merge commit is `d9de84ad` and its branch is deleted. #422 is draft/test-only
  and must not merge.
- `MAIN-PROVENANCE-FIX` — `done`: `cf535491` changed the legacy feedback
  filter to require a final standalone attribution line and restored detailed
  self-receipt logs. The exact main snapshot passed 20/20 provenance tests;
  CI run https://github.com/jasonhorga/garmin-ai-caddie/actions/runs/38813163550
  passed backend, frontend and docker.
- `PR429-REVIEW` — `done`: rebased exact head `2b39d63a` passed 33/33
  deployment harness tests on homeserver and required CI `38813956158`.
  PASS comment (no P1/P2):
  https://github.com/jasonhorga/garmin-ai-caddie/pull/429#issuecomment-6203460746.
  Merged as `ec8cddfe`; remote branch deleted. Real sandbox deployment and
  agenthub cutover remain future operations; production is unchanged.
  Continue processing new PR heads/comments once their required CI is terminal.
- The owner target remains seconds for nearby maps and under 30 s for an unseen
  course. Keep Watch cold-start and caddie correctness evidence explicit.

## Live verification baselines

- Production: revision
  `e1243ba9c516f2983a56aab1cdbd032d4595ab9c`, container
  `aicaddie-release-e1243ba9-production-20261015`, public
  `https://caddie.taile36706.ts.net`; matching sync image exists.
- Release evidence: `<project-data>/operations/release-readiness-428-20261015`.
  Apple waiter log:
  `<project-data>/operations/blocking-waits/wait-ci-38750039805-20261015T142108Z-3379555.log`.
- Existing cold-start baseline: nearby 28242 public drawable vector package
  `3.241 s`; cold 28214 first drawable package `6.453 s` through the
  homeserver Funnel. These are server/Funnel timings, not wrist/Tokyo/Austria
  timings.
- Build 87 remains in the internal group as historical baseline; Build 89 is
  the current release candidate verified above.
- #421 exact-head test snapshot was `<temporary-review-root>/codex-garmin-ai-caddie-pr421-62201d90`;
  it was removed immediately after the 19-test pass. No review snapshot remains.
- Main-fix verification snapshot `<temporary-review-root>/codex-main-waitfix-20261015` was
  removed after the 20-test pass.
- #429 test command: `python3 -m unittest -v tests.test_agenthub_deploy`
  in author's clean exact-head checkout
  `<session-checkouts>/garmin-ai-caddie-claude-deploy-20261015`;
  33 tests in 87.490 s, exit 0. No dependency installation or real Docker
  deployment; test temporary directories cleaned by unittest.

## Owned resources and cleanup

- The first isolated build process and image
  `garmin-ai-caddie-readiness-428:20261015` were absent at cleanup time.
  Exact context `<session-checkouts>/codex-readiness-428-20261015`
  (35 MB before cleanup) was removed using an exact allow-list:
  `<project-data>/operations/cleanup-codex-readiness-428-20261015.txt`.
  The temporary cleanup container was removed; shared BuildKit cache and
  production rollback container were left untouched.
- Release and Apple waiters are terminal; no temporary build or review
  container remains. Persistent release evidence above is retained.
- Existing review worktree
  `<historical-review-root>/garmin-ai-caddie-watch417-20261011`
  expires 2026-10-18 08:30 UTC. Historical `.codex-*` evidence is retained.
  Do not delete it without an explicit allow-list.

## Next action and stop conditions

1. Resume the retained feedback waiter in the same control turn for the next
   external PR/comment event; do not poll CI, processes, or monitor state.
   Process each event once and ignore Codex-only docs/state CI.
2. For a new code PR: review the exact head, run required remote tests, inspect
   Native artifacts when applicable, and comment with P1/P2/non-blocking evidence.
3. Owner stop condition: stop at the explicit owner stop, or after 48 hours with
   no new external PR event and no open PR. The previously recorded 2026-10-09
   wall-clock cutoff is historical/elapsed; newer owner requests keep this
   active slice authorized.
4. Every Codex GitHub comment/review ends `_Generated by Codex_`; every Codex
   commit ends `Generated-by: Codex`.


## Superseded card #1 startup state

HISTORICAL ARCHIVE — NON-AUTHORITATIVE

# Garmin AI Caddie Project State

> Short durable continuity ledger. Only this file is authoritative.
> Completed/history is preserved in dated `docs/archive/` files.

**Updated:** 2026-10-16; sandbox card #1 implementation
**Canonical baseline:** sandbox main `3ed25a98`
**Current slice:** `CARD-1-HEALTH-BUILD` — `in-progress`

## Current state and unfinished work

- `CARD-1-HEALTH-BUILD` — `in-progress`: implement the read-only health
  `build` object for real and CI-fixture APIs under contract
  `.agent/contracts/card-1.md` (Claude contract commit `85e50cbf`).
- Queued event: `contract:worker_done:2f4dd349003c:card:1`, successful.
- The previous production continuity ledger is preserved verbatim in
  `docs/archive/PROJECT_STATE-2026-10-16-pre-card-1.md`.
  Its production feedback slice is historical context for this sandbox.

## Live verification baselines

- Shared read-only Python environment:
  `<shared-environments>/caddie-drill-py312` (Python 3.12.3).
- Local checks pending: contract acceptance, existing health tests, and full
  backend unittest discovery. Tool network is disabled; no release verification.

## Owned resources and cleanup

- Work is in the assigned checkout
  `<session-checkouts>/caddie-drill-main-g1`, branch
  `agenthub/card-1-health-build`; no delegated session or new worktree.
- No dependency installation, containers, volumes, servers, or tunnels created.

## Next action and stop conditions

1. Run the contract checks; fix regressions within the card scope.
2. Commit locally with `Generated-by: Codex` and return an `open_pr` action;
   never push directly from this checkout.
3. Keep readiness, deployment manifests, dependencies, and other routes unchanged.


## Superseded initial card publication state

HISTORICAL ARCHIVE — NON-AUTHORITATIVE

# Garmin AI Caddie Project State

> Short durable continuity ledger. Only this file is authoritative.
> Completed/history is preserved in dated `docs/archive/` files.

**Updated:** 2026-10-16; card #1 public-path publication retry
**Canonical baseline:** sandbox main `3ed25a98`
**Current slice:** `CARD-1-HEALTH-BUILD` — `evidence-open`

## Current state and unfinished work

- `CARD-1-HEALTH-BUILD` — `evidence-open`: real and CI-fixture health now
  expose `build.revision` and `build.short` (first 12 characters), preserving
  existing fields, fixture markers, and the stripped/unknown revision rule.
  Real-route response typing accepts the nested object.
- Contract: `.agent/contracts/card-1.md`, Claude commit `85e50cbf`.
  Queued event: `contract:worker_done:2f4dd349003c:card:1`, successful.
- Implementation and focused checks are complete; ordinary CI remains needed
  because the dev sandbox cannot run the full suite without environment errors.
- Previous production ledger and card startup state are preserved with
  host-specific filesystem roots redacted in
  `docs/archive/PROJECT_STATE-2026-10-16-pre-card-1.md`.

- The initial `open_pr` action was rejected for host paths in newly added
  ledger/archive content. The unpublished implementation commit is being
  rewritten with portable filesystem role labels before retrying publication.

## Live verification baselines

- Shared read-only Python: `<shared-environments>/caddie-drill-py312`.
  No dependency installation. Tool network is disabled.
- Supplied acceptance tests (7) and existing health tests (2): 9/9 passed,
  44.939 s, via `python -m unittest tests.acceptance.test_card1_health_build
  tests.test_server_v2_health -v`.
- Sandbox limitation: ordinary TestClient hangs even for a minimal FastAPI app.
  Both successful test runs used a temporary external `sitecustomize.py` that
  wraps `asyncio.DefaultEventLoopPolicy.new_event_loop` to schedule a recurring
  `loop.call_later(0.01, pulse)`. This keeps thread notifications responsive;
  no repository runtime or test code was patched for the workaround.
- Full `python -m unittest discover -s tests -v` with that workaround completed
  2371 tests in 178.693 s: 10 failures, 2 errors, 46 skipped.
  All 10 failures cite missing `awk` in the branch-cleanup harness.
  Native evidence rejects the sandbox temporary path; topo forkserver socket
  binding raises `PermissionError`. The six implicated source/test files are
  byte-identical to main. The 33 deployment-harness tests skip for missing awk.
- The health, catalogue preflight, auth-policy, and admin-protection tests pass.
  Python compilation, canonical authority check, and `git diff --check` pass.

## Owned resources and cleanup

- Assigned checkout: `<session-checkouts>/caddie-drill-main-g1`, branch
  `agenthub/card-1-health-build`; no delegated session or new worktree.
- Local test processes ended. Temporary timer shim and test logs were removed
  using their exact paths after recording results here.
- No containers, volumes, preview servers, tunnels, or dependency installs.

## Next action and stop conditions

1. Return an `open_pr` action for card:1 with local evidence and limitations.
2. Obtain ordinary required CI and review before any gated merge.
3. Never push directly from this checkout; every Codex commit includes
   `Generated-by: Codex`. No release or production verification is claimed.


## Superseded pre-release verification state

HISTORICAL ARCHIVE — NON-AUTHORITATIVE

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
