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

Targeted tests: 229 passed, two missing-data skips. Contended cold and public
transport acceptance remain in progress; production remains cbc17f4e and
TestFlight remains 0.1.0 (87) at this checkpoint.

Persistent evidence, controls and resource manifest:
`/home/jason/garmin-ai-caddie-data/operations/map-startup-20261014`.
The baseline profile is instrumentation-affected; it identifies history/stat
and deferred-planner CPU but is not substituted for unprofiled timing.
