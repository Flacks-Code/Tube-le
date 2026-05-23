# SVG Map Extraction — Design Spec

**Date:** 2026-05-23
**Status:** Approved

## Problem

The current map pipeline extracts drawing primitives from the TfL PDF, re-derives coordinates via text-label snapping, and re-draws every element using the game's own rendering code. This produces two categories of error:

1. **Station marker shapes are wrong.** The game draws a generic `<circle>` for every station regardless of how many lines pass through it. The real TfL map uses compound shapes — two or three touching circles at major interchanges (King's Cross, Waterloo, etc.). This visual information is part of the game's hint system.
2. **Line geometry drifts.** Re-rendering from extracted coordinates introduces errors that accumulate across the coordinate transform, producing lines that don't sit at the correct Beck-style angles and positions relative to each other.

Iterating on the existing extraction approach is not converging. This spec describes a clean rewrite that embeds the TfL vector data directly.

---

## Approach

Instead of extracting individual drawing primitives and re-rendering, use PyMuPDF's `page.get_svg_image()` to export the full PDF page as a single SVG, then classify and filter the SVG elements. Accepted elements are embedded directly in the game — their geometry is exactly what TfL drew, not a re-derived approximation.

---

## Extraction Pipeline

**Script:** `build_map_from_tfl_pdf.py` (full rewrite, same filename)

**Input:** `tube_map_tfl.pdf` (page 0), `index.html`

**Steps:**

1. Export the PDF page as SVG via `page.get_svg_image()`.
2. Parse the SVG XML. Iterate all path elements in document order.
3. Classify each element into one of four buckets:

   | Bucket | Criteria |
   |--------|----------|
   | **Line path** | Has a stroke colour within `COLOUR_DIST_MAX=80` of one of the 12 `TARGET_LINE_COLOURS`. Overground/Thameslink are rejected because their colours fall outside this range for all Underground entries. |
   | **Interchange marker** | Has fill ≈ white (R,G,B each > 220), small bounding box (4–20 PDF units on each axis), and contains at least one cubic or quadratic curve command (`C`, `c`, `Q`, `q`) in its `d` attribute. |
   | **Thames** | Has a fill colour matching the TfL pale-blue (`R∈(150,220) G∈(210,250) B∈(230,255)`) and a large bounding box (> 5000 sq PDF units). |
   | **Discard** | Everything else: text, zone circles, Overground strokes, background fills. |

4. **Group interchange markers.** Markers whose bounding boxes overlap or sit within 8 PDF units of each other are merged into a single compound shape. This preserves the multi-circle form of major interchanges.

5. **Match markers to stations.** Each grouped marker is matched to the nearest entry in `TARGETS` by Euclidean distance from the group's bounding-box centre. The match is accepted if the distance is ≤ `MARKER_MATCH_RADIUS=40` PDF units. Unmatched groups are discarded with a warning.

6. **Derive station coordinates.** Each station's `coords` in `STATIONS` is set to the bounding-box centre of its matched marker group, in game coordinates (1400×900 viewBox, 40-unit margin). This replaces the text-label snapping approach entirely.

7. **Apply coordinate transform.** The same `compute_transform` as before maps all path `d` data from PDF coordinates to game coordinates.

8. **Patch `index.html`** with updated `TFL_LINE_PATHS`, new `TFL_INTERCHANGE_MARKERS`, updated `STATIONS[*].coords`, and `THAMES_PATH`.

**Removed from pipeline:** `_extract_text_labels`, `_find_graphical_markers`, `extract_station_positions`, `normalise` (ligature expansion), `SNAP_RADIUS`, `STATION_NEAR_RADIUS`, and the associated station-validation pass on line strokes. The SVG export already gives us the correct geometry; we no longer need to reconstruct it from primitives.

**Retained from pipeline:** `TARGET_LINE_COLOURS`, `COLOUR_DIST_MAX`, `TARGETS`, `ALIASES`, `compute_transform`, `MAP_W/MAP_H/MARGIN`, and the HTML patching logic.

---

## Data Format

Three JS constants in `index.html`:

### `TFL_LINE_PATHS` (unchanged format)

```js
const TFL_LINE_PATHS = {
  "Bakerloo": ["M … Z", "M … Z"],
  "Central":  ["M … Z", …],
  // … one entry per line, one d-string per continuous segment
};
```

### `TFL_INTERCHANGE_MARKERS` (new)

```js
const TFL_INTERCHANGE_MARKERS = {
  "Angel":                    ["M…C…Z"],
  "King's Cross St. Pancras": ["M…C…Z", "M…C…Z", "M…C…Z"],
  "Bank":                     ["M…C…Z", "M…C…Z"],
  // … one entry per station with a graphical marker in the PDF
};
```

Each value is an array of SVG path `d` strings — one per circle/shape in that station's compound marker. All markers render with `fill='#fff'` and a consistent dark stroke (`stroke='#1a1a1a'`, `stroke-width='1.5'`); these are hardcoded in the renderer, not stored per-marker.

### `THAMES_PATH` (unchanged format)

```js
const THAMES_PATH = "M … Z";
```

### `STATIONS[name].coords` (updated derivation)

Coords are now the bounding-box centre of `TFL_INTERCHANGE_MARKERS[name]` in game coordinates, patched into the existing `STATIONS` block by the pipeline. Format unchanged: `[cx, cy]`.

---

## Game Rendering Changes

### Marker drawing

A new helper function replaces all generic `<circle>` station rendering:

```js
function drawMarker(svg, name) {
  const paths = TFL_INTERCHANGE_MARKERS[name];
  if (paths) {
    for (const d of paths) {
      svg.appendChild(el('path', {
        d, fill: '#fff', stroke: '#1a1a1a', 'stroke-width': 1.5
      }));
    }
  } else {
    // fallback for display-only stations not in the PDF markers
    const [cx, cy] = STATIONS[name].coords;
    svg.appendChild(el('circle', {
      cx, cy, r: 3.5, fill: '#fff', stroke: '#1a1a1a', 'stroke-width': 1.2
    }));
  }
}
```

`drawTargetMarker` and the neighbour-marker loop both call `drawMarker`. No other rendering functions change.

### Everything else unchanged

- `clipPath` circle centred on `STATIONS[target].coords` — same logic
- Line colour control (`colored ? lineColor : '#b6b1a6'`) — same logic
- Guess thresholds for reveal (colours, neighbours, Thames, zone) — same
- `drawFullMapScene`, `drawThames`, `drawNeighbourGraph` — same structure

---

## Testing

### Unit tests: `tests/test_svg_extraction.py`

Replaces the deleted `tests/test_station_extraction.py`. No PyMuPDF dependency — uses fake SVG element dicts as input.

| Test | What it checks |
|------|---------------|
| `test_classifies_line_path` | A stroke-coloured element matching a known Underground colour → classified as that line |
| `test_rejects_overground_colour` | A stroke colour matching Mildmay blue → discarded |
| `test_classifies_interchange_marker` | White-filled small curved element → classified as marker |
| `test_discards_oversized_white_element` | White fill but large bbox → discarded |
| `test_discards_straight_white_element` | White fill, small bbox, no curves in `d` → discarded |
| `test_classifies_thames` | Pale-blue large fill → classified as Thames |
| `test_groups_nearby_markers` | Two marker bboxes within 8 PDF units → merged into one group |
| `test_separates_distant_markers` | Two marker bboxes > 8 PDF units apart → two separate groups |
| `test_matches_marker_to_station` | Grouped marker near a known station → matched by name |

Run with:
```bash
uv run --no-project --script tests/test_svg_extraction.py
```

### Integration check (requires PDF)

```bash
uv run --no-project --script build_map_from_tfl_pdf.py
```

Assert in output:
- `TFL_INTERCHANGE_MARKERS` has an entry for every playable (non-display-only) station
- King's Cross St. Pancras, Bank, and Waterloo each have ≥ 3 paths in their marker array
- No station `coords` is `[0, 0]`

### Visual check

Open `index.html` in browser. Verify:
- King's Cross shows a triple-circle interchange shape matching the real TfL map
- Single-line stations show a single small circle
- Line geometry sits at correct Beck-style 45° angles
- No Overground lines visible
- Thames visible from guess 5 onward
