# Tube-le Codebase

## Overview
A Wordle-like game using the London Underground map. Players guess tube stations.

## Key Files
- `build_map_from_tfl_pdf.py` — extracts station positions from the TfL PDF and patches `STATIONS[*].coords` in `index.html`. Used solely for coordinate extraction; no longer generates line paths, Thames, or interchange markers.
- `index.html` — the game front-end. Contains `STATIONS`, `LINES`, `ALL_EDGES` JS constants. Lines and Thames are rendered via the inlined `london-tube-net.svg` group.
- `london-tube-net.svg` — the pre-built Beck-style tube map SVG (1359×850 coordinate space). Inlined into `index.html` as `<g id="tube-map-src" style="display:none">` and cloned on each render.
- `tube_map_tfl.pdf` — source TfL standard tube map PDF (not committed, must be present locally for pipeline runs).

## Architecture: build_map_from_tfl_pdf.py

### Coordinate system
- `MAP_W=1359, MAP_H=850, MARGIN=40` — matches `london-tube-net.svg` coordinate space exactly.

### Station extraction pipeline
1. `_extract_text_labels(page)` — scans text spans at station-label point size (~4.2pt), builds a name→(cx,cy) dict using greedy chain matching.
2. `_find_graphical_markers(drawings)` — scans `page.get_drawings()` for white station circles and step-free access markers.
3. `extract_station_positions(page, drawings)` — snaps each text-label to nearest graphical marker within `SNAP_RADIUS=90` PDF units. `normalise()` expands fi/fl ligatures before matching.

### What the pipeline no longer does
- Does NOT generate `TFL_LINE_PATHS` (lines come from `london-tube-net.svg`)
- Does NOT generate `THAMES_PATH` (Thames is in `london-tube-net.svg`)
- Does NOT generate interchange markers (interchange circles are in `london-tube-net.svg`)

## Rendering Architecture

### Map layer (london-tube-net.svg)
The SVG is inlined in `index.html` as `<g id="tube-map-src" style="display:none">`. On each render:
- `drawPuzzleScene`: clones the group, applies clipPath (r=54/214/none) and `filter:saturate(0)` per guess count
- `drawFullMapScene`: clones the group with no clip/filter

### Progressive reveal sequence (6 guesses total)
| After wrong guess | Clue |
|---|---|
| 1 | Zone shown in chip |
| 2 | Opening year shown in chip |
| 3 | Clip expands (r=54 → r=214) |
| 4 | Colour revealed (saturate filter removed) |
| 5 | Full map (clip removed) + first letter chip |
| 6 | Game over if still wrong |

### Game data
- Elizabeth line and DLR removed from the game entirely.
- Each STATIONS entry has a `year:` field (opening year on Underground network).
- No `display_only` stations exist for Elizabeth or DLR.

## Tests
No automated tests (all verification is manual per spec).

## Running
```bash
uv run --no-project --script build_map_from_tfl_pdf.py
```
Requires `tube_map_tfl.pdf` and `index.html` present in the working directory.

## Development Notes
- Use `uv run --no-project` for all Python execution.
- `pymupdf` import is deferred into `main()` so the module can be imported without pymupdf installed.
- `SNAP_RADIUS=90`, `STATION_NEAR_RADIUS=40` PDF units (widened to handle stations with labels far from graphical circles).
