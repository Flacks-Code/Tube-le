# Tube-le Codebase

## Overview
A Wordle-like game using the London Underground map. Players guess tube stations.

## Key Files
- `build_map_from_tfl_pdf.py` — main pipeline: extracts line paths and station positions from the TfL PDF and patches `index.html`.
- `index.html` — the game front-end. Contains `STATIONS`, `LINES`, `ALL_EDGES`, and `TFL_LINE_PATHS` JS constants.
- `tube_map_tfl.pdf` — source TfL standard tube map PDF (not committed, must be present locally).
- `tfl_lines.json` / `tfl_stations.json` — generated output (JSON inspection files).

## Architecture: build_map_from_tfl_pdf.py

### Station extraction pipeline
1. `_extract_text_labels(page)` — scans text spans at station-label point size (~4.2pt), builds a name→(cx,cy) dict using greedy chain matching.
2. `_find_graphical_markers(drawings)` — scans `page.get_drawings()` for:
   - **White station circles**: fill≈(1,1,1), ≥3 curve items, bounding box 4–9.5 PDF units wide/tall.
   - **Step-free access markers**: TfL cyan-blue rectangles, fill in R∈(0.05,0.30) G∈(0.55,0.85) B∈(0.75,1.0), bounding box 6.5–12 PDF units.
3. `extract_station_positions(page, drawings)` — calls both, snaps each text-label position to nearest graphical marker within `SNAP_RADIUS=90` PDF units. Falls back to text-label position with a warning on snap miss. `normalise()` expands fi/fl ligatures (U+FB01/U+FB02) before chain-matching so names like "Northfields" match the PDF's ligated form.

### Line extraction pipeline
- Uses `closest_target_line(rgb)` + `COLOUR_DIST_MAX=80` to match stroked paths to tube lines.
- Uses `collect_stroke_points` + `LINE_STATIONS` to validate strokes by station proximity (`STATION_NEAR_RADIUS=40` PDF units, `STATION_HITS_MIN=2`), rejecting Overground/Thameslink contamination.

### Transform
- `compute_transform` maps PDF coordinates → game 1400×900 viewBox with 40-unit margin.

## Tests
- `tests/test_station_extraction.py` — tests for `_find_graphical_markers` (7 tests, run with `uv run --no-project --script tests/test_station_extraction.py`).

## Running
```bash
uv run --no-project --script build_map_from_tfl_pdf.py
```
Requires `tube_map_tfl.pdf` and `index.html` present in the working directory.

## Development Notes
- `pymupdf` import is deferred into `main()` so the module can be imported in tests without pymupdf installed.
- Use `uv run --no-project` for all Python execution.
- TDD: always write failing tests first.
