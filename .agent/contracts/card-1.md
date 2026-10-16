# Card #1 contract — health: read-only `build` object

Acceptance tests: `tests/acceptance/test_card1_health_build.py` (package marker `tests/acceptance/__init__.py`).
Touches: `server_v2/main.py`, `server_v2/ci_fixture.py`, `tests/`, `docs/operations/PROJECT_STATE.md`, `docs/archive/PROJECT_STATE-*.md`

## Interface

`GET /api/v2/health` (real app, `server_v2/main.py::health`) returns:

```json
{"schema": "ai-caddie-health-v2", "status": "ok", "service": "server_v2",
 "revision": R, "build": {"revision": R, "short": R[:12]}}
```

where `R = os.getenv("AI_CADDIE_BUILD_REVISION", "unknown").strip() or "unknown"`.
This is the existing top-level rule. Keep it unchanged, including evaluating it on every request.

`GET /api/v2/health` in fixture mode (`AI_CADDIE_FIXTURE_MODE=1`,
`server_v2/ci_fixture.py::health`) returns the existing payload plus
`"build": {"revision": FIXTURE_REVISION, "short": FIXTURE_REVISION[:12]}`. The
`dataMode` / `source` / `fixtureRevision` markers stay as they are, and the
`AI_CADDIE_BUILD_REVISION` variable is ignored, as it is today.

Implementation notes:
- FastAPI uses the return annotation as the response model. `health() -> dict[str, str]`
  rejects a nested object, so widen it (for example `dict[str, object]`), or the route returns 500.
- Compute `R` once per request and derive both `revision` fields from it, so top-level and
  `build.revision` cannot drift. Do not cache it at import time.
- `build` is output only. No query parameter, header or request body may change it, and
  `/api/v2/health` stays GET-only (other methods keep returning 405).
- `tests/test_server_v2_health.py::test_health_endpoint_returns_versioned_status`
  asserts the exact old payload. Update its expected dict to include
  `"build": {"revision": "0123456789abcdef", "short": "0123456789ab"}`. Do not delete it.

### G1 — health gains `build = {revision, short}`, and the top-level fields are unchanged

- With `AI_CADDIE_BUILD_REVISION=0123456789abcdef0123456789abcdef01234567`, the
  response equals the card's example exactly. No other keys are added.
- `build.revision` equals the top-level `revision` after stripping
  (`"  feedfacecafebeef1234\n"` → both `"feedfacecafebeef1234"`, short `"feedfacecafe"`).
- `build.short` is `revision[:12]`: `"abc123"` → `"abc123"`, the 12-char `"0123456789ab"` →
  itself, and the 13-char `"0123456789abc"` → `"0123456789ab"`.
- `build` follows the top-level `revision` on every request. If the variable changes after
  import, both fields report the new value.
- `build` is read-only. With spoofing query params (`revision`, `short`, `build`, `build.revision`) and
  spoofing headers (`X-AI-Caddie-Build-Revision`, `X-Build-Revision`), `build` still reports `R`.
  POST/PUT/PATCH/DELETE on `/api/v2/health` return 405, and a GET afterwards still reports `R`.
- `schema`, `status`, `service` and `revision` keep their current values.
- Tests: `test_health_matches_card_example_exactly`,
  `test_build_revision_is_the_stripped_top_level_revision`,
  `test_short_is_the_first_twelve_characters`,
  `test_build_tracks_the_top_level_revision_on_every_request`,
  `test_build_cannot_be_overridden_or_written`,
  `test_fixture_and_real_health_share_one_contract`.

### G2 — an unset or blank revision falls back to `"unknown"`

- If `AI_CADDIE_BUILD_REVISION` is unset, `""`, `"   "`, `"\t\n"` or `" \r\n\t "`, then
  `revision`, `build.revision` and `build.short` are all `"unknown"`. This holds both when the
  value is present at process start and when it changes later. The fallback is not sticky:
  setting a real revision afterwards reports it, and unsetting it again returns `"unknown"`.
- Tests: `test_unset_revision_falls_back_to_unknown_everywhere`,
  `test_blank_revision_falls_back_to_unknown_everywhere`.

### G3 — the CI fixture health has the same `build` shape

- In fixture mode (even with `AI_CADDIE_BUILD_REVISION` set), the health body equals exactly
  `{"schema": "ai-caddie-health-v2", "status": "ok", "service": "server_v2", "revision": "ci-fixture-20260827-v1",
  "build": {"revision": "ci-fixture-20260827-v1", "short": "ci-fixture-2"}, "dataMode": "ci_fixture",
  "source": "non_production", "fixtureRevision": "ci-fixture-20260827-v1"}`.
- The fixture's `/api/v2/readiness` body is unchanged and has no `build` (the card leaves readiness alone).
- The fixture's `build` key set equals the real API's (`{"revision", "short"}`). The fixture's top-level
  keys are exactly the real API's keys plus the three markers. Both satisfy `build.revision == revision`
  and `build.short == revision[:12]`, and all `build` values are strings.
- Tests: `test_ci_fixture_health_carries_the_same_build_shape`,
  `test_fixture_and_real_health_share_one_contract`.

## How the tests run

Every test body calls `subprocess.run` itself. The subprocess is a fresh interpreter that imports
the real `server_v2.main.app` with the environment already set, then drives it through
`TestClient(app)` without entering its context manager. No lifespan runs, and the tests are offline
and use no database. A probe step may set or unset `AI_CADDIE_BUILD_REVISION` before its request.
Each test carries `# G<n>` comment lines naming its goals. No test is `# pinned:`. Every test asserts
on the `build` object, so every test fails on `main` with an `AssertionError`.

## Out of scope

`/api/v2/readiness`, deploy scripts, Dockerfile/compose/fly/render manifests,
and dependencies stay unchanged. No other route changes.

## Required checks

- `python -m unittest tests.acceptance.test_card1_health_build -v` passes.
- `python -m unittest tests.test_server_v2_health -v` passes with the updated expectation.
- Full suite: `uv run python -m unittest discover -s tests -v` stays green, including
  `test_live_course_catalogue_preflight`, `test_agenthub_deploy`, `test_codex_sec2`,
  `test_p1_backend_hardening` and `test_server_v2_admin_protection`, which read health.

## Post-release verification (read-only)

With `AI_CADDIE_API_BASE_URL` set to the production API, `GET /api/v2/health` must have
`build.revision == <released sha>` and `build.short == <released sha>[:12]`. This check creates no data.
