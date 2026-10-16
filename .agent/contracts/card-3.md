# Card #3 contract — health: `build.revision` becomes the 12-character short sha

Acceptance tests: `tests/acceptance/test_card3_health_short_build_revision.py`, plus the updated
`tests/acceptance/test_card1_health_build.py` (card #1's acceptance suite, rewritten for this contract).
Touches: `server_v2/main.py`, `server_v2/ci_fixture.py`, `tests/test_server_v2_health.py`, `tests/acceptance/**`,
`docs/operations/PROJECT_STATE.md`, `docs/archive/PROJECT_STATE-*.md`

## Interface

`GET /api/v2/health` (real app, `server_v2/main.py::health`) returns:

```json
{"schema": "ai-caddie-health-v2", "status": "ok", "service": "server_v2",
 "revision": R, "build": {"revision": R[:12]}}
```

where `R = os.getenv("AI_CADDIE_BUILD_REVISION", "unknown").strip() or "unknown"`. This is the existing
top-level rule. Keep it as it is, including evaluating it on every request. The only change is that
`build` becomes `{"revision": R[:12]}`. The old `build.revision` (full) and `build.short` both go.

In fixture mode (`AI_CADDIE_FIXTURE_MODE=1`, `server_v2/ci_fixture.py::health`), `build` becomes
`{"revision": FIXTURE_REVISION[:12]}` (`"ci-fixture-2"`). Everything else in the fixture payload stays the same,
including the `dataMode` / `source` / `fixtureRevision` markers. The fixture still ignores `AI_CADDIE_BUILD_REVISION`.

Implementation notes:
- Compute `R` once per request, then derive `build.revision` from it as `R[:12]`. Do not cache it at import time.
- Keep the return annotation of `main.py::health` as `dict[str, object]`. A nested dict fails `dict[str, str]`.
- `tests/test_server_v2_health.py::test_health_endpoint_returns_versioned_status` asserts the old exact
  payload. Change its expected `build` to `{"revision": "0123456789ab"}`. Do not delete the test.
- `docs/operations/PROJECT_STATE.md` line 13 describes `build.revision` and `build.short`. Update it
  following the ledger/archive rule in AGENTS.md §5.
- No other code reads `build.short` today (Fastlane, the preflight script and `ops/` only read
  `schema` and the top-level `revision`), so nothing else needs to change.

### G1 — `build.revision` is the first 12 characters of the top-level `revision`; `build.short` is removed; top-level fields unchanged

- With `AI_CADDIE_BUILD_REVISION=0123456789abcdef0123456789abcdef01234567`, the body equals the card's example
  exactly: `{"schema": "ai-caddie-health-v2", "status": "ok", "service": "server_v2",
  "revision": "0123456789abcdef0123456789abcdef01234567", "build": {"revision": "0123456789ab"}}`.
- `build` has exactly one key, `revision`. There is no `short` key.
- `build.revision == revision[:12]`, where `revision` has been stripped: `"  <40-char sha>\n"` → top level is the
  full 40-char sha and build is its first 12. `"abc123"` → `"abc123"`. The 12-char `"0123456789ab"` → itself.
  The 13-char `"0123456789abc"` → `"0123456789ab"`.
- The value follows the variable on every request. If it changes after import, both fields report the new value.
- Top-level `schema`, `status`, `service` and `revision` keep their current values. `revision` stays the full value.
  There are no other top-level keys.
- `build` is read-only. Spoofing query params (`revision`, `short`, `build`, `build.revision`, `build.short`) and
  spoofing headers (`X-AI-Caddie-Build-Revision`, `X-Build-Revision`) are ignored. POST/PUT/PATCH/DELETE return
  405, and a GET afterwards still reports `R[:12]`.
- Tests (card #3 file): `test_health_matches_card_example_exactly`,
  `test_build_revision_is_the_first_twelve_characters_of_the_stripped_revision`,
  `test_short_is_removed_top_level_is_unchanged_and_build_is_read_only`,
  `test_fixture_and_real_health_share_one_build_contract`.

### G2 — an unset or blank `AI_CADDIE_BUILD_REVISION` still gives `build.revision == "unknown"`

- If the variable is unset, `""`, `"   "`, `"\t\n"` or `" \r\n\t "`, the body is exactly
  `{"schema": "ai-caddie-health-v2", "status": "ok", "service": "server_v2", "revision": "unknown",
  "build": {"revision": "unknown"}}`. This holds both at process start and after a later change.
- The fallback is not sticky. Setting a real sha afterwards reports `sha[:12]`, and unsetting it or blanking it
  again returns `"unknown"`.
- Tests (card #3 file): `test_unset_revision_reports_unknown`, `test_blank_revision_reports_unknown`.

### G3 — the CI fixture health matches the new contract, and card #1's tests are updated

- In fixture mode (even with `AI_CADDIE_BUILD_REVISION` set), the health body equals exactly
  `{"schema": "ai-caddie-health-v2", "status": "ok", "service": "server_v2", "revision": "ci-fixture-20260827-v1",
  "build": {"revision": "ci-fixture-2"}, "dataMode": "ci_fixture", "source": "non_production",
  "fixtureRevision": "ci-fixture-20260827-v1"}`.
- The fixture's `/api/v2/readiness` body is unchanged and has no `build`.
- The fixture and the real API have the same `build` shape (`{"revision": revision[:12]}`). The fixture's
  top-level keys are the real API's keys plus the three markers.
- Card #1's tests follow the new contract. `python -m unittest tests.test_server_v2_health
  tests.acceptance.test_card1_health_build` exits 0. The acceptance half is already rewritten. Codex updates
  `tests/test_server_v2_health.py` as described above.
- Tests (card #3 file): `test_ci_fixture_health_uses_the_short_build_revision`,
  `test_fixture_and_real_health_share_one_build_contract`, `test_existing_health_tests_follow_the_new_contract`.
  The updated card #1 suite also covers this.

## How the tests run

Every test body calls `subprocess.run` itself. Most start a fresh interpreter that imports the real
`server_v2.main.app` with the environment already set and drives it through `TestClient(app)` without entering
its context manager. No lifespan runs, and the tests are offline and use no database.
`test_existing_health_tests_follow_the_new_contract` runs `python -m unittest` on card #1's two health modules.
Each test carries `# G<n>` comment lines. No test is `# pinned:`. Every test checks the new `build` shape
(directly or through card #1's suite), so every test fails on `main` with an `AssertionError`.

## Out of scope

Top-level `revision`, `/api/v2/readiness`, deploy scripts, Dockerfile/compose manifests and dependencies stay
unchanged. No other route changes.

## Required checks

- `python -m unittest tests.acceptance.test_card3_health_short_build_revision -v` passes.
- `python -m unittest tests.acceptance.test_card1_health_build tests.test_server_v2_health -v` passes.
- The full suite stays green: `uv run python -m unittest discover -s tests -v`.

## Post-release verification (read-only)

With the release variable `AI_CADDIE_API_BASE_URL` set to the production API, `GET /api/v2/health` must show
top-level `revision == <released sha>` and `build.revision == <released sha>[:12]`, with no `build.short`.
This check creates no data.
