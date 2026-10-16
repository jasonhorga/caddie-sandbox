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
