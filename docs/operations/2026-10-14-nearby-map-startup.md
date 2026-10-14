# Nearby and cold map startup

Coordination: https://github.com/jasonhorga/garmin-ai-caddie/issues/426.
Codex owns backend; Claude owns Watch nearby download and vector drawing.

The owner target is a nearby map in seconds and a genuinely unseen usable map
under 30 s. These measurements are backend calls, not wrist/public-network claims.

Implementation queues every provider course within 30 km on GPS discovery;
uses one shared public-assets journal per physical course; checks actual hole
counts from the release; bounds regional work to one hole and selected work
to two holes per coordinator pass; and prioritizes a playing-hole download.
Factual vectors persist by physical-hole/release/Tee fingerprint independently
of the player's history and topo raster. Personalized planning stays scoped
to the requesting player and can enrich the partial factual prep later.

`coursePrep.holes[*].map.image` remains null for vector-only rows. The overlay
adds `surfaces` with actual mesh rings (`kind`, `polygons`, `outerPx`, `holesPx`)
in the shared raster frame. Route, green/fairway outlines, hazard edges and
F/M/B/GPS projection are included. Do not gate drawing on `topoReady` or the
install's all-assets `ready` phase. #425's null-image/progress fixes are required.

## Measured first draw

2026-10-14, existing production dependency image with candidate source, real
Garmin data/session paths. Before 28263 (Drachenwand): no cached release, no
ZIPs, no decoded holes. No data was removed to manufacture a cold measurement.

| Phase | Seconds |
|---|---:|
| Release metadata | 0.299 |
| ZIP download | 0.733 |
| Key retrieval + extraction | 2.086 |
| Draco decode | 0.967 |
| Distance export | 0.980 |
| Hazard export | 1.549 |
| File install | 0.001 |
| Geometry ensure (includes authority/other overhead) | 6.393 |
| Factual vectors | 0.152 |
| First drawable physical hole | 6.844 |
| History load | 2.388 |
| Facts/stats/caddie package | 4.857 |
| Route/vector seeds | 0.024 |
| First package with drawable map | 14.125 |
| Immediate repeat while remaining install pending | 0.615 |

The map contains real fairway/fringe/tee/green/bunker rings and green F/M/B
317/331/344 yd. Nine-hole geometry+topo completed 17:30:00Z, about 63 s after
enqueue (17:28:57Z), about 77 s after the cold request began. First-map
availability and full install completion are different measured milestones.

An earlier 30180 probe omitted the production session symlink and failed
decryption. Its captures remain failed-verification evidence, excluded from
successful timing claims. The corrected probe reads the existing protected
session path; no credential is copied to evidence or logs.

## Regional contention and first-map response

All 17 provider courses around 47.8688854, 13.1455506 were enqueued, with a
foreground cold selection. No release, ZIP or mesh existed for the named
selection before each measurement. Direct backend results:

| Selection/request | First package | Vector preparation | History | Facts/player package |
|---|---:|---:|---:|---:|
| 30189, ordinary cold package | 24.061 s | 8.176 s | 7.189 s | 8.661 s |
| 30189, warm package | 4.718 s | 0.023 s | 2.559 s | 2.094 s |
| 30189, warm after selected nine ready | 8.315 s | 0.026 s | 2.381 s | 4.362 s |
| 28241, cold factual map package | 7.643 s | 7.445 s | 0.000 s | 0.166 s |
| 28241, immediate warm factual map | 0.450 s | 0.186 s | 0.000 s | 0.217 s |
| 28241, warm after selected nine ready | 0.618 s | 0.032 s | 0.000 s | 0.343 s |
| 28245, final code cold factual map | 11.613 s | 10.676 s | 0.000 s | 0.836 s |
| 28245, immediate warm factual map | 0.321 s | 0.053 s | 0.000 s | 0.213 s |

Different courses are separate samples, not a paired latency benchmark. The
ordinary path still waits for player projection after its map is drawable.
The explicit `map_only=true&background_geometry=true` package request removes
that dependency: the same v2 schema carries the complete ordered hole list,
factual vectors and deferred player enrichment. It returns empty clubProfiles
and no synthetic recommendations; fetch the ordinary package separately for
personal clubs/history/caddie. Keep the first map and any existing personal
club model while that enrichment arrives. This is the visible tradeoff: map
first, recommendations later. Raster completion is never a drawing gate.

The 28241 nine-hole install succeeded (geometry 9/9 + topo 9/9), but hole 9
alone spent 36.266 s exporting distances and 54.052 s exporting hazards.
This remains a full-install optimization opportunity, independent of usable
first-map delivery. Optional CourseView route authority is now observed before
the foreground export so A/B greens bind to the selected layout; missing
catalogues are shared per release and retried hourly instead of per hole.

Targeted final code tests: 231 passed, two missing-data skips. These include
the map-only history/stats/planning/raster isolation and ordered back→front
identity, plus optional catalogue release invalidation/backoff. The final
cold 28245 sample includes optional route authority (metadata 0.765 s),
geometry 8.609 s and factual vectors 1.286 s, with all 17 regional courses
queued. The first response had a real map with topo still pending; its
verification-owned remaining install was cancelled/drained after first-map
measurements. Public transport acceptance is pending. Production remains
cbc17f4e and TestFlight remains 0.1.0 (87) at this checkpoint.

Persistent evidence, controls and resource manifest:
`/home/jason/garmin-ai-caddie-data/operations/map-startup-20261014`.
The baseline profile is instrumentation-affected; it identifies history/stat
and deferred-planner CPU but is not substituted for unprofiled timing.
