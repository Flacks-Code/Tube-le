# SVG Map Redesign — Design Spec

**Date:** 2026-07-04
**Status:** Approved

## Problem

The current map pipeline extracts line geometry and station positions from the TfL PDF and re-renders everything dynamically. This produces incorrect results: line geometry drifts from the authentic Beck-style angles, and station markers are generic circles instead of the proper compound shapes. Iterative fixes have not converged on a correct result.

A pre-built SVG of the London Underground network (`london-tube-net.svg`) is now available. It contains correct Beck-style line geometry, interchange circle markers, the River Thames, and zone background shapes — all in a clean `1359×850` coordinate space. This spec describes a redesign that uses this SVG as the map layer directly.

---

## Scope Changes

**Removed from game:**
- Elizabeth line (all stations, edges, line definition)
- DLR (all stations, edges, line definition)

**Added to game:**
- Opening year for each station (new `year` field on `STATIONS` entries)
- Opening year as a progressive clue (clue 2 in the reveal sequence)

---

## Architecture

The SVG replaces all dynamic line drawing. `london-tube-net.svg` content is inlined into `index.html` as a hidden `<g id="tube-map-src">` element. Each render call clones this group and appends it (with clip and filter applied) into the active game SVG. The Thames, interchange circles, and line paths all come from the SVG — no separate extraction or dynamic rendering.

The game SVG has two layers rendered in order:

1. **Map layer** — cloned SVG group, clipped and/or desaturated per guess count
2. **Game elements layer** — target marker and neighbour dots drawn on top dynamically

### Coordinate system

The game's SVG `viewBox` changes from `0 0 1400 900` to `0 0 1359 850` to match `london-tube-net.svg` exactly. Station `coords` in `STATIONS` are re-derived by re-running `build_map_from_tfl_pdf.py` with `MAP_W=1359, MAP_H=850`. The pipeline continues to be used solely for station coordinate extraction — it no longer generates line paths or interchange markers.

### Removed from codebase

| Item | Reason |
|------|--------|
| `TFL_LINE_PATHS` JS constant | SVG handles line display |
| `TFL_INTERCHANGE_MARKERS` JS constant | SVG handles interchange circles |
| `THAMES_PATH` JS constant | Thames is in the SVG |
| `drawThames()` function | Redundant |
| `drawTargetExits()` function | Line stubs provided by SVG |
| `drawNeighbourGraph()` function | All lines visible via SVG |
| `extract_thames_from_pdf.py` script | No longer needed |
| Elizabeth and DLR in `STATIONS`, `LINES`, `LINE_ORDER`, `ALL_EDGES` | Scope reduction |
| `tests/test_svg_extraction.py`, `tests/test_station_extraction.py` | No testable pure functions remain |

---

## Progressive Reveal Sequence

6 guesses total. Each wrong guess unlocks the next clue:

| After wrong guess | Clue |
|---|---|
| 1 | Zone number shown in chip |
| 2 | Opening year shown in chip |
| 3 | Clip radius expands |
| 4 | Colour revealed (desaturation filter removed) |
| 5 | Full map shown (clip removed entirely) |
| Before guess 6 | First letter of station name shown |

**Initial state** (before any guess): map layer visible, fully desaturated (`filter: saturate(0)`), clipped to a small radius around the target station. Thames and interchange circles always visible within the clip. Zone and year chips hidden. Target marker shown.

**Clip radii** (in 1359×850 coordinate space):
- Guesses 0–2: radius `54`
- Guesses 3–4: radius `214`
- Guess 5+: no clip

---

## Data Changes

### Removing Elizabeth line and DLR

From `index.html`:
- Delete all `STATIONS` entries for stations served only by Elizabeth or DLR (e.g. Abbey Wood, Custom House, Pudding Mill Lane, Woolwich Arsenal, etc.)
- For stations shared with Underground lines (e.g. Paddington, Stratford, Canary Wharf), remove Elizabeth/DLR from their `lines` array only
- Remove `"Elizabeth"` and `"DLR"` from `LINES`, `LINE_ORDER`
- Remove all `ALL_EDGES` entries involving Elizabeth or DLR stations
- Remove any `display_only: true` stations that were added solely to support Elizabeth or DLR line rendering

### Opening year data

A one-off Python script (`fetch_station_years.py`) fetches opening years from the Wikipedia "List of London Underground stations" article (well-structured HTML table). Output: `station_years.json` mapping station name → integer year.

A second script (`apply_years.py`) reads `station_years.json` and patches each `STATIONS` entry in `index.html` to add `year: NNNN`.

For stations with complex histories, the rule is: **use the year the station first opened on the Underground network in any form**, not the year it was rebuilt, renamed, or extended.

Both scripts are single-use and can be deleted after the data is patched.

---

## Rendering Changes

### `drawPuzzleScene` (rewritten)

Three steps:
1. Create `<clipPath>` circle centred on `STATIONS[target].coords` with radius based on guess count (54 / 214 / none)
2. Clone `<g id="tube-map-src">`, apply `clip-path` and `filter: saturate(0)` (removed at guess 4), append to SVG
3. Draw target marker on top via `drawTargetMarker()`

### `drawFullMapScene` (rewritten)

Two steps:
1. Clone `<g id="tube-map-src">` with no clip, no filter, append to SVG
2. Draw target marker with label on top via `drawTargetMarker(svg, target, true)`

### `drawTargetMarker` (unchanged in interface, simplified in body)

Draws a white circle with red pulse ring at `STATIONS[target].coords`. No longer needs multi-circle compound shapes since the SVG already renders the correct interchange shape beneath it. Radius fixed at `10` regardless of line count.

### Inlined SVG source

`london-tube-net.svg` content (everything between the outer `<svg>` tags) is placed in `index.html` as:

```html
<g id="tube-map-src" style="display:none">
  <!-- london-tube-net.svg content here -->
</g>
```

The `renderMap()` function clones this group on each render via `document.getElementById('tube-map-src').cloneNode(true)`, removes `display:none`, applies transforms, and appends it to the active SVG.

---

## Verification

All verification is manual (no automated tests for this work):

1. **Coordinate alignment**: Set 5–6 major interchange stations (King's Cross, Waterloo, Bank, Paddington, Victoria, Liverpool Street) as the puzzle target in turn. Confirm the target marker dot sits on the correct line intersection in the SVG, not offset beside it. If misaligned, adjust `MAP_W`/`MAP_H` in the pipeline or apply a scale correction to all coords.

2. **Reveal sequence**: Make 6 wrong guesses and confirm each clue appears at the right moment — zone chip, year chip, clip expansion, colour reveal, full map, first letter.

3. **Data integrity**: Confirm no Elizabeth or DLR stations appear in the autocomplete. Confirm every remaining station has a non-zero `year` value.

4. **Regression**: win/lose flow, share grid, and compass bearings all work correctly after data changes.
