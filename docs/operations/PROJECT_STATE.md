# Garmin AI Caddie Project State

> Short durable continuity ledger. Only this file is authoritative.
> Completed/history is preserved verbatim in dated `docs/archive/` files.

**Updated:** 2026-10-14 19:03 UTC, #427 deployment/public verification closed
**Canonical baseline:** main `128798fd` (Build87 source `bfe850b7`)
**Current slice:** `PR-FEEDBACK-CONTINUOUS` — `in-progress`

## Current state and unfinished queue

- `PR-FEEDBACK-CONTINUOUS` — `in-progress`: resume retained terminal
  `85049`; deduplicate external feedback and ignore Codex-owned bookkeeping.
  Do not create another monitor, edit its cursor, or use ad-hoc CI/ps polling.
- `BACKEND-NEARBY-MAP-STARTUP` — `evidence-open`: backend #427 is
  merged/deployed and its verification/cleanup is complete. Owner's on-wrist
  target (nearby seconds; unseen usable map <30 s) needs Claude's Watch
  integration and real device evidence. Coordination issue #426; deployed
  contract/timings comment `6176058201`. Detailed operations evidence:
  `2026-10-14-nearby-map-startup.md`.
- `WATCH-COLD-START-HARNESS` — `evidence-open`: Claude's branch
  `claude/watch-cold-start-timing-20261014` head `e7ed34a2` workflow
  `38626741763` is green but measured no map (`hole1_map_vector_s=-1`,
  `hole1_map_raster_s=-1`, repeated `upgrade_paused`). It is based on the
  known nullable `map.image` decoder blocker and is not an end-to-end pass.
  The harness also selects `topoReady==0` rather than proving no release/ZIP/
  mesh cache and searches 80 km instead of the 30 km acceptance radius.
  Feedback posted on #426 comment `6177682840`; rerun only on the fixed #425
  head with a hard first-vector assertion and cache-state evidence.
- `PR-425-COLD-WATCH-MAP` — `evidence-open`: head remains
  `c4fdddc9abb601aaefd599f6b31019a92a6680ec`; do not rerun the completed
  original-head review. Ordinary and Native `38594117897` passed,
  126 contracts + 12 parity passed; 47 Watch/97 iPhone snapshots matched #424.
  P1 `6172993813`: required Watch String rejects vector-only map.image:null.
  P2 `6173026392`: status-only retries miss geometry/generation progress.
  Timeline `6173093641`: 28242 front nine ready08:15:54 (~76 s), all18
  ready08:16:55 (~125 s); both precede final Watch retry. Original request
  bodies/start times absent. No server raster gate; previous loopback package
  110.098 s, warm3.255 s. Hold `6173187157`; Claude implements Watch fixes.
  Deployment reply `6176081318`; backend is now ready. Exact revised head,
  Native and first-vector behavior
  must pass before merge/delete. Review: `2026-10-14-pr425-cold-watch-map-review.md`.
- `PR-418-AUDIT-477EAAB6` — `evidence-open`: draft held for P1/P2
  author fixes and exact-head rerun.
- `PR-420-W01-49MM` — `evidence-open`: 49 mm first manual-shot rail
  still needs five successful first-try transitions.
- `PR-421-FEEDBACK-DELIVERY` — `evidence-open`: awaiting external review.
- #422 remains draft/test-only; never merge. Completed prototype review
  does not establish production callback behavior.
- #417 remains the Watch audit evidence issue; already-posted findings stand.
  `WATCH-IDLE-PHYSICAL-ACCEPTANCE` and `OWNER-DEVICE-BUILD87` —
  `evidence-open`: physical Crown, 45-min idle pause, <30-min relaunch,
  second-nine WCSession/GPS transport and Tee preselection remain owner checks.
- `NATIVE-FIXTURE-LAYOUT-STABILITY` and `IOS-STATUS-CONTRAST` — `queued`.

## Live verification baselines

- Production revision `128798fd8fd638227c8668a05de02c15eb3787a7`,
  container `aicaddie-release-128798fd-production-20261014`,
  loopback39055/container9000, public `https://caddie.taile36706.ts.net`.
  Matching sync image exists. Previous cbc17f4e container is stopped/retained
  for rollback. Existing ingress, protected private volume and cron preserved.
- Health/history/sync/prep/topo gates passed. Manual incremental sync
  18:36:47–18:37:27 UTC (40 s), exact revision, `sync ok`, `done`.
- Authenticated readiness HTTP200/authenticated:true remains the existing
  Build87 `degraded` internal baseline: absent private acceptance evidence,
  historical weather and legacy mobile event schema. Source/18-hole geometry/
  11 clubs/18 seeds are ready. No new runtime failure or full-ready claim.
- #427 exact-head full CI `38612115537` passed at `b9cf540a`;
  production image verification 258 pass, 2 data-dependent skips, plus original
  deployment gates; 39 supplemental map/auth tests had passed.
- Production cold28214: release/Tee0.6740 s + public drawable package5.7789 s
  =6.4529 s, immediate public warm0.2237 s/loopback0.1149 s.
  Before: no release, zero ZIPs/meshes. First map had true route/surface/FMB/GPS,
  geometry1/9, topo0/9; 15,540 wire bytes; Server-Timing total5.654 s.
  Samples originate on homeserver through Funnel, not wrist/Tokyo/Austria.
- Regionally warmed public26557 first/repeat1.4252/0.8883 s;
  nearby28242 public3.2413/2.6722 s. GPS options/nearby0.8146/1.1234 s
  initially, later0.1980/0.2160 s. All17 actual nearby journals verified.
- Original26557 probe used :front from initial catalogue18; release267 is9
  (:all). HTTP422 excluded/preserved. Fresh nearby/Tee both now9.
  Test stale Watch option + new Tee authority (withTees preserves old count);
  this is a source risk, not a reproduced fresh-search Watch failure.
- Client first-map contract: `map_only=true&background_geometry=true`,
  nullable image + actual overlay.route/surfaces; draw before topo/installready.
  Ordinary package separately enriches clubs/caddie; retain map/personal model.
- Internal TestFlight iOS/watchOS0.1.0(87): CD `38529901074`,
  Apple `38532148335`, VALID/IN_BETA_TESTING, internal group contains87.
  Source `bfe850b7`, release backendcbc17f4e. No new backend-slice upload.
  Full diagnosis/device handoff: `2026-10-14-internal-testflight87.md`.
  IPA SHA256 `b847f3fdc2c461f176494c732f92a32322b0bdf3da3a3fc313b2bbc782596b0a`.
- #424 merged `6bb684fa`; final exact head `5ac993ef`, ordinaryCI
  `38446895152`/Native `38446895372` passed. Harness `799762d0`,
  run `38453004091`: 41/42/45/46/49mm taps390/390 each, record/undo10/10,
  simulated second-nine sync2/2;45mm first fairway tap succeeds. Physical
  scale/GPS/Crown/WCSession/OLED behavior remains unproven by these simulators.
  #423 merged `46f9c8ff`; #424 release replies6162864583/6163465026/
  6164079823 handled. Do not redispatch on duplicate Build87 requests.

## Owned resources and cleanup

- One implementation worktree:
  `/home/ubuntu/claude-web-data/repo/garmin-ai-caddie-watch417-20261011`,
  owner Codex, branch `codex/map-startup-deploy-verification-20261014`,
  renewed 2026-10-14, expires 2026-10-21. Historical untracked audit controls
  remain; root main's Codex-owned stale ledger is archived for reconciliation.
- Shared remote checkout (never switch HEAD/index):
  `/home/jason/codex-runs/garmin-ai-caddie-claude-takeover-20261005`.
- Backend evidence:
  `/home/jason/garmin-ai-caddie-data/operations/map-startup-20261014`.
  Verification source archived/removed before build. Build source
  `/dev/shm/codex-map-startup-deploy-20261014`, candidate
  `codex-map-startup-128798fd-candidate-20261014`(39088), disposable volume
  `codex-map-startup-128798fd-private-20261014` all removed; source archive
  checksum/open-file checks passed; production health confirmed. Test/probe
  containers auto-removed. No build/sync/probe terminal remains in flight.
  Protected maps/production volume, production images, rollback and regional
  install jobs remain intentionally persistent. Capacity ~44GiB free.
- Successful deployment reports under evidence/deployment:
  `live-map-28214-20261014T185721Z.json`,
  `live-map-26557-20261014T185658Z.json`, `catalogue-26557-identity.json`,
  `cleanup-result.json`; failed original `live-map-timings.json` retained.
- #425 snapshot and test container removed; evidence
  `/home/jason/garmin-ai-caddie-data/operations/pr425-c4fdddc9-20261014`.
  No review service/port/tunnel/environment remains.
- #424 evidence: project operations `pr424-5ac993ef-native-20261013`
  and `pr424-5ac993ef-native-ci-20261013`; audit branch deleted.
  Build87 evidence: operations `release87-20261014`; controls closed.
- Feedback85049 is retained/unobserved;19026's already-reviewed Native event
  deduplicated. Prior waiters/release/Apple terminals returned. Do not replace
  the pending feedback handle or edit `blocking-waits/feedback-cursor`.
- Displaced states preserved verbatim in dated2026-10-14 map-startup
  archives (before-public-closeout, deployed-before-close, root-before-reconcile).

## Next action and stop conditions

1. Finish publishing deployment evidence/ledger with real operations work;
   reconcile root main, then resume terminal85049 in the same turn.
2. On a revised #425/Watch integration head, inspect first-map decoding/
   surfaces/progress, stale-course identity and personal enrichment preservation;
   run relevant exact-head tests and wait for Native CI, inspect its artifacts,
   merge/delete only without blocking findings. Original c4fdddc9 is handled.
3. Recheck the cold-start harness after #425's fixed head; a green harness
   with all map timings `-1` is a failed measurement, not acceptance.
4. Continue #417/other actionable external feedback once, preserving evidence.
   No CI-result-only commits; Codex bookkeeping never resets the quiet clock.
5. End after48 hours with no external PR events and no open PRs, or an explicit
   owner stop. Every Codex GitHub comment ends `_Generated by Codex_`;
   every Codex commit ends `Generated-by: Codex`.
