# Christchurch Underground: Plan

> Status: big-picture draft. The detail for each phase gets filled in once the phase before it is published.

## 1. Goal

A developer portfolio project aimed at Seequent: a live web app that shows the ground beneath part of Christchurch in 3D, built from real borehole/CPT data. It should make sense to someone within 30 seconds of opening it.

The project has to show:
- **Data handling**: messy geotechnical records turned into clean, validated, tested data.
- **Spatial maths**: coordinate systems, depth intervals, cross-sections, interpolation.
- **3D visualisation**: an interactive subsurface viewer in the browser.
- **Engineering practice**: CI, tests, a clear README and a decisions log.
- **Domain sense**: honesty about uncertainty ("what this can't tell you").

## 2. Guiding rules

1. **Publish every phase.** Each phase ends with something live and linkable. Phase 1 on its own is a complete portfolio piece.
2. **One area, one layer, one demo** until Phase 3.
3. **Finish a phase before starting the next one.** Ideas for later go in a backlog.
4. **Keep a decisions log** (`docs/decisions.md`): what was chosen, why, and what was rejected.

## 3. Phases at a glance

| Phase | Name | Size | Ships | Depends on |
|---|---|---|---|---|
| 0 | Data spike | S | Map of records + one parsed log | – |
| 1 | Christchurch Underground (the lead) | M | Live 3D viewer + cross-sections | 0 |
| 2 | Where we know least | M | Interpolated layer + confidence map | 1 |
| 3 | Dig Down | M–L | Drilling game | 2 |
| 4 | Underground GeoGuessr | S | Guess-the-location game | 1 (can come before 3) |
| – | Optional extras | ? | Evo integration / Minecraft export / sonification | Any |

### Phase 0: Data spike
- **Aim:** prove the data is usable before building anything.
- **Scope:** one area, a few hundred CPTs/boreholes, a LiDAR DEM, and the licence terms for each source.
- **Done when:** the records plot on a map, and one log's depth intervals parse into a clean structure.
- **Detail:** [docs/phase-0.md](docs/phase-0.md)

### Phase 1: Christchurch Underground (the lead)
- **Aim:** open the page and see the ground in 3D straight away.
- **Scope:** an ingestion and validation pipeline, an API, a 3D client with boreholes as coloured columns, a draw-a-line cross-section, a vertical exaggeration slider and log popups.
- **Done when:** there's a live link, CI is green, and the README has a GIF, an architecture section and a "what this can't tell you" section.

### Phase 2: Where we know least
- **Aim:** the first real analysis: estimate one surface between holes and show where the estimate is weak.
- **Scope:** interpolate one layer (for example the top of the gravels) and show a confidence/uncertainty map in the viewer.
- **Done when:** the viewer shows the estimated surface and highlights where it's unreliable.

### Phase 3: Dig Down
- **Aim:** a game built on the Phase 2 engine.
- **Scope:** a hidden ground model, a borehole budget, scoring of the player's interpretation, and uncertainty-guided hints.
- **Done when:** a stranger can play a full round without instructions.

### Phase 4: Underground GeoGuessr
- **Aim:** a cheap quick win that reuses the Phase 1 data and map.
- **Scope:** show a log without its location; the player guesses where it came from and is scored by distance.
- **Done when:** it's playable and linked from the main app.

## 4. Architecture

```
 Public data sources ──► Python pipeline ──► Clean dataset ──► API service ──► Web client
 (CPT/borehole, LiDAR)   (ingest, validate,   (versioned)       (FastAPI)       (TypeScript +
                          reproject, test)                                       deck.gl/Cesium)
```

- **Pipeline:** Python, pyproj, pytest. It runs offline and produces a static clean dataset.
- **Service:** FastAPI, for queries such as cross-sections and later interpolation results.
- **Client:** TypeScript, with a 3D map library (deck.gl or CesiumJS, decided in Phase 1).
- **Repo:** a single monorepo (`pipeline/`, `api/`, `web/`, `docs/`) with CI from day one.

## 5. Key decisions (open)

| Decision | When | Notes |
|---|---|---|
| Which area / suburb | Phase 0 | Central or eastern Christchurch: dense post-quake CPT data, varied ground |
| Data sources and licences | Phase 0 | Oregon State CPT collections as the first test case; NZGD access terms |
| Weekly time budget | Now | Sets the size of the phases and the target dates |
| deck.gl vs CesiumJS | Phase 1 | **Decided: deck.gl** (D-004) |
| Hosting (static + API) | Phase 1 | Needs to be cheap or free and stay up long term |
| Kriging vs Gaussian process | Phase 2 | |
| Real data with withheld holes vs a synthetic truth | Phase 3 | Real is more impressive; synthetic is easier to score fairly |

## 6. Risks

- **Data is messier or more restricted than expected**: Phase 0 exists to find this out early.
- **Scope creep**: the guiding rules and a backlog.
- **3D performance or complexity**: keep to one area, and simplify geometry where needed.
- **Hosting costs or upkeep**: prefer a static build where possible.

## 7. Timeline

To be set once the weekly time budget is decided.

| Phase | Target |
|---|---|
| 0 | TBD |
| 1 | TBD |
| 2 | TBD |
| 3 | TBD |
| 4 | TBD |

## 8. Next steps

1. Decide the weekly time budget.
2. Choose the area.
3. Start Phase 0 and write the detailed Phase 0 section of this plan.
