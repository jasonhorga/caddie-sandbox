# Card #1 contract — health: read-only `build` object

Acceptance tests: `tests/acceptance/test_card1_health_build.py`.
Touches: `server_v2/main.py`, `server_v2/ci_fixture.py`, `tests/`

## Interface

`GET /api/v2/health` (real app, `server_v2/main.py::health`) returns:

```json
{"schema": "ai-caddie-health-v2", "status": "ok", "service": "server_v2",
 "revision": R, "build": {"revision": R, "short": R[:12]}}
```

where `R = os.getenv("AI_CADDIE_BUILD_REVISION", "unknown").strip() or "unknown"`
(this is the existing top-level rule; leave it unchanged).

`GET /api/v2/health` in fixture mode (`AI_CADDIE_FIXTURE_MODE=1`,
`server_v2/ci_fixture.py::health`) returns the existing payload plus
`"build": {"revision": FIXTURE_REVISION, "short": FIXTURE_REVISION[:12]}`. The
`dataMode` / `source` / `fixtureRevision` markers stay as they are.

Implementation notes:
- FastAPI uses the return annotation as the response model. `health() -> dict[str, str]`
  rejects a nested object, so widen it (for example `dict[str, object]`), or the route returns 500.
- Compute `R` once and derive both `revision` fields from it, so top-level and
  `build.revision` cannot drift.
- `tests/test_server_v2_health.py::test_health_endpoint_returns_versioned_status`
  asserts the exact old payload. Update its expected dict to include
  `"build": {"revision": "0123456789abcdef", "short": "0123456789ab"}`. Do not delete it.

### G1 — health gains `build = {revision, short}`, and the top-level fields are unchanged

- With `AI_CADDIE_BUILD_REVISION=0123456789abcdef0123456789abcdef01234567`, the
  response equals the card's example exactly. No other keys are added.
- `build.revision` equals the top-level `revision` after stripping
  (`"  feedfacecafebeef1234\n"` → both `"feedfacecafebeef1234"`, short `"feedfacecafe"`).
- `build.short` is `revision[:12]`. A revision shorter than 12 characters is kept whole (`"abc123"`).
- `schema`, `status`, `service`, `revision` keep their current values.
- Tests: `test_health_matches_card_example_exactly`,
  `test_build_revision_equals_stripped_top_level_revision`,
  `test_short_revision_under_twelve_chars_is_kept_whole`,
  `test_fixture_and_real_build_objects_share_one_contract`.

### G2 — an unset or blank revision falls back to `"unknown"`

- If `AI_CADDIE_BUILD_REVISION` is unset, `""`, `"   "` or `"\t\n"`, then `revision`,
  `build.revision` and `build.short` are all `"unknown"`.
- Tests: `test_unset_revision_falls_back_to_unknown_everywhere`,
  `test_blank_revision_falls_back_to_unknown_everywhere`.

### G3 — the CI fixture health has the same `build` shape

- In fixture mode, `build == {"revision": "ci-fixture-20260827-v1", "short": "ci-fixture-2"}`.
  The top-level fields and fixture markers are unchanged.
- The fixture's `build` key set equals the real API's (`{"revision", "short"}`).
  Both satisfy `build.revision == revision` and `build.short == revision[:12]`, and all values are strings.
- Tests: `test_ci_fixture_health_carries_same_build_shape`,
  `test_fixture_and_real_build_objects_share_one_contract`.

## Out of scope

`/api/v2/readiness`, deploy scripts, Dockerfile/compose/fly/render manifests,
and dependencies stay unchanged. No other route changes.

## Required checks

- `python -m unittest tests.acceptance.test_card1_health_build -v` passes. Each test starts
  `server_v2.main.app` in a subprocess with the environment set before import. The tests run offline,
  start no lifespan, and use no database.
- `python -m unittest tests.test_server_v2_health -v` passes (with the updated expectation).
- Full suite: `uv run python -m unittest discover -s tests -v` stays green, including
  `test_live_course_catalogue_preflight`, `test_agenthub_deploy`, `test_codex_sec2` and
  `test_server_v2_admin_protection`, which read health.

## Post-release verification (read-only)

With `AI_CADDIE_API_BASE_URL` set to the production API, `GET /api/v2/health` must have
`build.revision == <released sha>` and `build.short == <released sha>[:12]`. This check creates no data.
