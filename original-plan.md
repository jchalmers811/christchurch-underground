# Christchurch Underground: Phased Portfolio Project Plan

A phased plan for a Seequent-focused developer portfolio project. Each phase ships publicly, so the project is application-ready after Phase 1.

## Overview

The lead should be something someone can open and understand within thirty seconds, with the games layered on top of it. The plan runs from a data spike, through a 3D subsurface viewer (the lead), to an uncertainty layer, and then two playful extras: Dig Down and Underground GeoGuessr.

## Phase 0: Data spike (small)

Pick one area of Christchurch and confirm you can get usable data before building anything: a few hundred CPTs or boreholes, plus a LiDAR DEM for the surface. Check each source's terms while you're there. The Oregon State CPT collections are a good test case because they come with coordinates and groundwater depths.

- **Done when:** you can plot your records on a map and read at least one log's depth intervals into a clean data structure.
- **Why first:** if the data is messier than expected, you want to find out in a weekend, not a month.

## Phase 1: The lead, "Christchurch Underground" (medium)

A live web page that opens straight into a 3D view of the ground beneath one area, with boreholes as coloured columns. The user draws a line on the map and gets a vertical cross-section.

- **Includes:** the ingestion and validation pipeline (Python, pyproj, pytest), a FastAPI service, and a TypeScript client with deck.gl or CesiumJS. Add a vertical exaggeration slider and clear log popups.
- **Done when:** there's a live link, CI is passing, and the README has a 60-second GIF at the top, a short architecture section and a "what this can't tell you" section.
- **Why this works as the lead:** it shows data handling, 3D, spatial maths and testing in one view, and it needs no explanation.

## Phase 2: "Where we know least" (medium)

Add interpolation between holes for one layer, for example the top of the gravels, with a confidence map beside it. Interpolate with PyKrige or a Gaussian process.

- **Done when:** the viewer shows an estimated surface and highlights where it's unreliable.
- **Why it's here:** it's your first real analysis, and it's the engine that Dig Down needs.

## Phase 3: Dig Down (medium to large)

The drilling game: a hidden ground model, a budget of boreholes, a score on how close the player's interpretation gets, and uncertainty-guided hints.

- **Needs from Phase 2:** the interpolation and uncertainty code. The game is mostly a new front end and scoring layer.
- **Done when:** someone you've never met can play a full round without instructions.
- **Decision to make then:** whether the hidden truth is real data (with some holes withheld) or a synthetic model. Withholding real holes is more impressive but harder to score fairly.

## Phase 4: Underground GeoGuessr (small)

Show a log with no location and let the player guess where it came from, scored by distance. It reuses the Phase 1 data and map, so it's cheap.

- **Tip:** it needs no interpolation, so you can build it earlier if you want a quick win or a break from Phase 3.

## Optional extras

Only if time allows: Seequent Evo integration, a Minecraft export, or sonification. Treat these as bonuses, and credit the earlier work in each case.

## Rules to keep it from sprawling

- **Finish and publish each phase before starting the next.** Phase 1 alone is a complete portfolio piece.
- **One area, one layer, one demo** until Phase 3.
- **Keep a short decisions log** in the repo (why this data, why this interpolation method, what you rejected). Interviewers like reading it.

## Next step

Phase 0: choose the suburb. Central Christchurch and the eastern suburbs have lots of post-earthquake CPT data and strongly varying ground, so they would make a more interesting cross-section than a uniform area. Decide how much time you can give this each week, which determines how to size the phases.
