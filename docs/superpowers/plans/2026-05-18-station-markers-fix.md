# Station Markers Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix station position extraction to use graphical circle positions from the PDF (not text labels), add all missing Piccadilly branch stations, and normalize step-free access markers to standard circles.

**Architecture:** `extract_station_positions()` in `build_map_from_tfl_pdf.py` currently returns text label centres, which are offset from the actual white circle markers on the PDF. The fix splits this into two passes: (1) keep text-label matching to identify station names, then (2) snap each name to the nearest white filled circle from `page.get_drawings()`. Step-free markers (blue rectangles in the PDF) are treated as station positions too. Piccadilly branch stations are added as display-only entries following the same pattern as the previous map-data-fix session.

**Tech Stack:** Python/PyMuPDF (`uv run --no-project --script`), vanilla JS/SVG in `index.html`.

---

## File Structure

| File | Change |
|------|--------|
| `build_map_from_tfl_pdf.py` | Add 19 Piccadilly stations to `TARGETS` + `LINE_STATIONS`; refactor `extract_station_positions()` to snap to graphical circles |
| `index.html` | Add 19 display-only `STATIONS` entries; update `LINES["Piccadilly"].sequences` with full branch station lists |
| `tests/test_station_extraction.py` | New — unit tests for `_find_graphical_markers()` helper (no PyMuPDF needed, uses fake drawing dicts) |

---

## Task 1: Add Piccadilly stations to `build_map_from_tfl_pdf.py`

**Files:**
- Modify: `build_map_from_tfl_pdf.py` (TARGETS list ~lines 58–94, LINE_STATIONS["Piccadilly"] ~lines 228–235)

New stations — Uxbridge branch:
- Ealing Common → Rayners Lane: `North Ealing`, `Park Royal`, `Alperton`, `Sudbury Town`, `Sudbury Hill`, `South Harrow`
- Rayners Lane → Uxbridge: `Eastcote`, `Ruislip Manor`, `Ruislip`, `Ickenham`, `Hillingdon`

New stations — Heathrow branch (Acton Town → Heathrow T2&3):
`South Ealing`, `Northfields`, `Boston Manor`, `Osterley`, `Hounslow East`, `Hounslow Central`, `Hounslow West`, `Hatton Cross`

- [ ] **Step 1: Add to TARGETS**

In `build_map_from_tfl_pdf.py`, add a new comment block after the Heathrow entries in TARGETS (after line 57):

```python
    # --- Piccadilly: Uxbridge branch ---
    "North Ealing","Park Royal","Alperton","Sudbury Town","Sudbury Hill","South Harrow",
    "Eastcote","Ruislip Manor","Ruislip","Ickenham","Hillingdon",
    # --- Piccadilly: Heathrow branch ---
    "South Ealing","Northfields","Boston Manor","Osterley",
    "Hounslow East","Hounslow Central","Hounslow West","Hatton Cross",
```

- [ ] **Step 2: Add to LINE_STATIONS["Piccadilly"]**

Replace the current Piccadilly block (lines 228–235):

```python
    "Piccadilly": [
        "Cockfosters","Finsbury Park","King's Cross St. Pancras","Holborn",
        "Covent Garden","Leicester Square","Piccadilly Circus","Green Park",
        "South Kensington","Gloucester Road","Earl's Court","Barons Court",
        "Hammersmith","Turnham Green","Acton Town","Ealing Common",
        # Uxbridge branch
        "North Ealing","Park Royal","Alperton","Sudbury Town","Sudbury Hill","South Harrow",
        "Rayners Lane","Eastcote","Ruislip Manor","Ruislip","Ickenham","Hillingdon","Uxbridge",
        # Heathrow branch
        "South Ealing","Northfields","Boston Manor","Osterley",
        "Hounslow East","Hounslow Central","Hounslow West","Hatton Cross",
        "Heathrow Terminals 2 & 3","Heathrow Terminal 4","Heathrow Terminal 5",
    ],
```

- [ ] **Step 3: Commit**

```bash
git add build_map_from_tfl_pdf.py
git commit -m "feat: add Piccadilly branch stations to pipeline TARGETS and LINE_STATIONS"
```

---

## Task 2: Add display-only STATIONS entries and update LINES in `index.html`

**Files:**
- Modify: `index.html` (STATIONS block ~lines 753–1000, Piccadilly in LINES ~lines 1102–1112)

Zone and line data for each new station:

| Station | Zone | Lines |
|---------|------|-------|
| North Ealing | 3 | ["Piccadilly"] |
| Park Royal | 3 | ["Piccadilly"] |
| Alperton | 4 | ["Piccadilly"] |
| Sudbury Town | 4 | ["Piccadilly"] |
| Sudbury Hill | 4 | ["Piccadilly"] |
| South Harrow | 5 | ["Piccadilly"] |
| Eastcote | 5 | ["Metropolitan","Piccadilly"] |
| Ruislip Manor | 6 | ["Metropolitan","Piccadilly"] |
| Ruislip | 6 | ["Metropolitan","Piccadilly"] |
| Ickenham | 6 | ["Metropolitan","Piccadilly"] |
| Hillingdon | 6 | ["Metropolitan","Piccadilly"] |
| South Ealing | 3 | ["Piccadilly"] |
| Northfields | 3 | ["Piccadilly"] |
| Boston Manor | 4 | ["Piccadilly"] |
| Osterley | 4 | ["Piccadilly"] |
| Hounslow East | 4 | ["Piccadilly"] |
| Hounslow Central | 4 | ["Piccadilly"] |
| Hounslow West | 5 | ["Piccadilly"] |
| Hatton Cross | 6 | ["Piccadilly"] |

All new stations: `river:"far"`, `display_only:true`, `coords:[0,0]` (pipeline fills these).

- [ ] **Step 1: Add STATIONS entries**

Add after the existing Heathrow entries in the STATIONS block (find the line with `"Heathrow Terminal 5"` and insert after it):

```js
  // --- Piccadilly: Uxbridge branch ---
  "North Ealing":             { coords:[0,0], zone:3, lines:["Piccadilly"], river:"far", display_only:true },
  "Park Royal":               { coords:[0,0], zone:3, lines:["Piccadilly"], river:"far", display_only:true },
  "Alperton":                 { coords:[0,0], zone:4, lines:["Piccadilly"], river:"far", display_only:true },
  "Sudbury Town":             { coords:[0,0], zone:4, lines:["Piccadilly"], river:"far", display_only:true },
  "Sudbury Hill":             { coords:[0,0], zone:4, lines:["Piccadilly"], river:"far", display_only:true },
  "South Harrow":             { coords:[0,0], zone:5, lines:["Piccadilly"], river:"far", display_only:true },
  "Eastcote":                 { coords:[0,0], zone:5, lines:["Metropolitan","Piccadilly"], river:"far", display_only:true },
  "Ruislip Manor":            { coords:[0,0], zone:6, lines:["Metropolitan","Piccadilly"], river:"far", display_only:true },
  "Ruislip":                  { coords:[0,0], zone:6, lines:["Metropolitan","Piccadilly"], river:"far", display_only:true },
  "Ickenham":                 { coords:[0,0], zone:6, lines:["Metropolitan","Piccadilly"], river:"far", display_only:true },
  "Hillingdon":               { coords:[0,0], zone:6, lines:["Metropolitan","Piccadilly"], river:"far", display_only:true },
  // --- Piccadilly: Heathrow branch ---
  "South Ealing":             { coords:[0,0], zone:3, lines:["Piccadilly"], river:"far", display_only:true },
  "Northfields":              { coords:[0,0], zone:3, lines:["Piccadilly"], river:"far", display_only:true },
  "Boston Manor":             { coords:[0,0], zone:4, lines:["Piccadilly"], river:"far", display_only:true },
  "Osterley":                 { coords:[0,0], zone:4, lines:["Piccadilly"], river:"far", display_only:true },
  "Hounslow East":            { coords:[0,0], zone:4, lines:["Piccadilly"], river:"far", display_only:true },
  "Hounslow Central":         { coords:[0,0], zone:4, lines:["Piccadilly"], river:"far", display_only:true },
  "Hounslow West":            { coords:[0,0], zone:5, lines:["Piccadilly"], river:"far", display_only:true },
  "Hatton Cross":             { coords:[0,0], zone:6, lines:["Piccadilly"], river:"far", display_only:true },
```

- [ ] **Step 2: Update LINES["Piccadilly"] sequences**

Replace the current Piccadilly sequences block (lines 1102–1112):

```js
  "Piccadilly": {
    color:"#003688",
    sequences:[
      ["Cockfosters","Finsbury Park","King's Cross St. Pancras","Holborn","Covent Garden",
       "Leicester Square","Piccadilly Circus","Green Park","South Kensington",
       "Gloucester Road","Earl's Court","Barons Court","Hammersmith","Turnham Green","Acton Town"],
      ["Acton Town","South Ealing","Northfields","Boston Manor","Osterley",
       "Hounslow East","Hounslow Central","Hounslow West","Hatton Cross",
       "Heathrow Terminals 2 & 3","Heathrow Terminal 5"],
      ["Heathrow Terminals 2 & 3","Heathrow Terminal 4"],
      ["Acton Town","Ealing Common","North Ealing","Park Royal","Alperton",
       "Sudbury Town","Sudbury Hill","South Harrow","Rayners Lane",
       "Eastcote","Ruislip Manor","Ruislip","Ickenham","Hillingdon","Uxbridge"]
    ]
  },
```

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: add Piccadilly branch display-only stations and complete LINES sequences"
```

---

## Task 3: Rewrite station extraction to use graphical circles

**Files:**
- Create: `tests/test_station_extraction.py`
- Modify: `build_map_from_tfl_pdf.py` (refactor `extract_station_positions`, update `main`)

The current `extract_station_positions(page)` returns text-label centres. We split into:
1. `_extract_text_labels(page)` — existing matching logic, returns `{name: (pdf_x, pdf_y)}`
2. `_find_graphical_markers(drawings)` — new, returns list of `(cx, cy)` from white circles + step-free markers
3. `extract_station_positions(page, drawings)` — calls both, snaps text positions to nearest marker circle

**Marker detection criteria:**
- White filled station circles: `fill == (1.0, 1.0, 1.0)`, ≥3 curve items (`'c'`), bounding box width and height both in `4.0–9.5` PDF units
- Step-free markers: `fill` with R∈(0.05,0.3), G∈(0.55,0.85), B∈(0.75,1.0), bounding box width and height both in `6.5–12.0` PDF units
- Snapping threshold: nearest marker within **30 PDF units** of the text label

- [ ] **Step 1: Write failing tests for `_find_graphical_markers`**

Create `tests/test_station_extraction.py`:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Tests for _find_graphical_markers in build_map_from_tfl_pdf."""
import sys
sys.path.insert(0, '.')
from build_map_from_tfl_pdf import _find_graphical_markers


def _circle_drawing(cx, cy, r, fill=(1.0, 1.0, 1.0)):
    """Fake drawing dict matching what PyMuPDF returns for a filled white circle."""
    return {
        'fill': fill,
        'items': [('c', None, None, None), ('c', None, None, None), ('c', None, None, None)],
        'rect': (cx - r, cy - r, cx + r, cy + r),
        'type': 'f',
    }


def _rect_drawing(cx, cy, w, h, fill):
    """Fake drawing dict for a filled rectangle."""
    return {
        'fill': fill,
        'items': [('l', None, None), ('l', None, None), ('l', None, None), ('l', None, None)],
        'rect': (cx - w/2, cy - h/2, cx + w/2, cy + h/2),
        'type': 'f',
    }


def test_finds_white_station_circle():
    drawings = [_circle_drawing(100.0, 200.0, 2.8)]  # 5.6×5.6, white
    result = _find_graphical_markers(drawings)
    assert len(result) == 1
    assert abs(result[0][0] - 100.0) < 0.01
    assert abs(result[0][1] - 200.0) < 0.01


def test_ignores_white_circle_too_small():
    drawings = [_circle_drawing(100.0, 200.0, 1.0)]  # 2×2 — border circle, ignore
    result = _find_graphical_markers(drawings)
    assert len(result) == 0


def test_ignores_white_circle_too_large():
    drawings = [_circle_drawing(100.0, 200.0, 6.0)]  # 12×12 — interchange blob, ignore
    result = _find_graphical_markers(drawings)
    assert len(result) == 0


def test_finds_step_free_marker():
    sf_fill = (0.15, 0.70, 0.91)
    drawings = [_rect_drawing(50.0, 80.0, 8.2, 8.8, sf_fill)]
    result = _find_graphical_markers(drawings)
    assert len(result) == 1
    assert abs(result[0][0] - 50.0) < 0.01
    assert abs(result[0][1] - 80.0) < 0.01


def test_ignores_non_white_filled_circle():
    red_fill = (1.0, 0.0, 0.0)
    drawings = [_circle_drawing(100.0, 200.0, 2.8, fill=red_fill)]
    result = _find_graphical_markers(drawings)
    assert len(result) == 0


def test_ignores_drawings_with_no_curves():
    d = {
        'fill': (1.0, 1.0, 1.0),
        'items': [('l', None, None), ('l', None, None)],
        'rect': (97.2, 197.2, 102.8, 202.8),
        'type': 'f',
    }
    result = _find_graphical_markers([d])
    assert len(result) == 0


def test_returns_multiple_markers():
    drawings = [
        _circle_drawing(100.0, 200.0, 2.8),
        _circle_drawing(300.0, 400.0, 2.8),
        _rect_drawing(500.0, 600.0, 8.2, 8.8, (0.15, 0.70, 0.91)),
    ]
    result = _find_graphical_markers(drawings)
    assert len(result) == 3


if __name__ == '__main__':
    tests = [v for k, v in list(globals().items()) if k.startswith('test_')]
    passed = 0
    for t in tests:
        try:
            t()
            print(f'  PASS  {t.__name__}')
            passed += 1
        except Exception as e:
            print(f'  FAIL  {t.__name__}: {e}')
    print(f'\n{passed}/{len(tests)} passed')
    raise SystemExit(0 if passed == len(tests) else 1)
```

- [ ] **Step 2: Run tests to confirm they fail (function doesn't exist yet)**

```bash
uv run --no-project --script tests/test_station_extraction.py
```

Expected: fails with `ImportError: cannot import name '_find_graphical_markers'`

- [ ] **Step 3: Implement `_find_graphical_markers` and refactor extraction**

In `build_map_from_tfl_pdf.py`:

**3a.** Add the new helper immediately before `extract_station_positions`:

```python
def _find_graphical_markers(drawings: list) -> list[tuple[float, float]]:
    """Return centres of white station circles and step-free access markers.

    White station circles: fill=(1,1,1), curve items, bounding box 4–9.5 PDF units.
    Step-free markers: blue rectangular fill, bounding box 6.5–12 PDF units.
    """
    markers: list[tuple[float, float]] = []
    for d in drawings:
        fill = d.get('fill')
        if fill is None:
            continue
        rect = d.get('rect')
        if rect is None:
            continue
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        cx = (rect[0] + rect[2]) / 2
        cy = (rect[1] + rect[3]) / 2
        items = d.get('items', [])

        r, g, b = fill[0], fill[1], fill[2]
        curve_count = sum(1 for item in items if item[0] == 'c')

        # White station circles
        if (all(abs(c - 1.0) < 0.05 for c in (r, g, b))
                and curve_count >= 3
                and 4.0 <= w <= 9.5
                and 4.0 <= h <= 9.5):
            markers.append((cx, cy))
            continue

        # Step-free access markers (TfL cyan-blue rectangles)
        if (0.05 < r < 0.30 and 0.55 < g < 0.85 and 0.75 < b < 1.0
                and 6.5 <= w <= 12.0
                and 6.5 <= h <= 12.0):
            markers.append((cx, cy))

    return markers
```

**3b.** Rename the existing `extract_station_positions` body (everything from the first `td = page.get_text(...)` line through to the final `return out`) to `_extract_text_labels(page)`. The signature becomes:

```python
def _extract_text_labels(page) -> dict[str, tuple[float, float]]:
```

Keep the body exactly as-is (return `out` — the dict of station name → text-label centre).

**3c.** Add the new top-level `extract_station_positions`:

```python
SNAP_RADIUS = 30  # PDF units: max text-label → circle distance for snapping

def extract_station_positions(page, drawings: list) -> dict[str, tuple[float, float]]:
    """Extract station centres from the PDF.

    First finds text-label positions (for station-name matching), then snaps
    each label position to the nearest white circle or step-free marker within
    SNAP_RADIUS PDF units. Falls back to the text-label position if no marker
    is close enough (prints a warning).
    """
    text_pos = _extract_text_labels(page)
    markers = _find_graphical_markers(drawings)

    out: dict[str, tuple[float, float]] = {}
    for name, (tx, ty) in text_pos.items():
        best_dist = float('inf')
        best_pos: tuple[float, float] | None = None
        for mx, my in markers:
            d = ((mx - tx) ** 2 + (my - ty) ** 2) ** 0.5
            if d < best_dist:
                best_dist = d
                best_pos = (mx, my)
        if best_pos is not None and best_dist <= SNAP_RADIUS:
            out[name] = best_pos
        else:
            print(f'  snap miss ({best_dist:.1f}u): {name} — using text label')
            out[name] = (tx, ty)
    return out
```

**3d.** Update the call in `main()` — change:

```python
    raw_stations = extract_station_positions(page)
```

to:

```python
    raw_stations = extract_station_positions(page, drawings)
```

(`drawings` is already fetched two lines earlier in `main()`.)

- [ ] **Step 4: Run tests — expect all to pass**

```bash
uv run --no-project --script tests/test_station_extraction.py
```

Expected output:
```
  PASS  test_finds_white_station_circle
  PASS  test_ignores_white_circle_too_small
  PASS  test_ignores_white_circle_too_large
  PASS  test_finds_step_free_marker
  PASS  test_ignores_non_white_filled_circle
  PASS  test_ignores_drawings_with_no_curves
  PASS  test_returns_multiple_markers

7/7 passed
```

- [ ] **Step 5: Commit**

```bash
git add build_map_from_tfl_pdf.py tests/test_station_extraction.py
git commit -m "feat: extract station positions from graphical circles, normalize step-free markers"
```

---

## Task 4: Run pipeline and verify

**Files:** No code changes — run existing scripts and check output.

- [ ] **Step 1: Run the main extraction pipeline**

```bash
uv run --no-project --script build_map_from_tfl_pdf.py
```

Expected output (approximately):
```
Diagram bounds (from stations): X ...
Strokes accepted: N, skipped (colour off-target): M, skipped (station validation): K
  snap miss (NNu): <station> — using text label    ← zero or a handful
Patched N STATIONS entries.
```

If you see more than ~5 `snap miss` lines, the threshold may need adjusting — increase `SNAP_RADIUS` to 40 and re-run. If you see `?: <name>` lines (station not found in text labels at all), the station name may need an ALIASES entry.

- [ ] **Step 2: Run Thames extraction**

```bash
uv run --no-project --script extract_thames_from_pdf.py
```

Expected: prints path length, patches `THAMES_PATH` in `index.html`.

- [ ] **Step 3: Verify in browser**

Open `index.html` in a browser (file:// is fine). Check:

- Piccadilly line shows all stations from Acton Town through to Uxbridge with no gaps (should see ~12 dots between Ealing Common and Uxbridge)
- Piccadilly line shows all stations on Heathrow branch (South Ealing through Hatton Cross before splitting to T4/T5)
- Station dots sit ON the coloured line strokes, not offset beside them
- Single-line stations show as small white circles on their line stroke (the "tick" appearance)
- Interchange stations (multi-line) show as larger circles
- Step-free stations appear as standard white circles (not blue rectangles)
- Display-only stations do NOT appear in the autocomplete dropdown when typing a guess
- Existing gameplay is unaffected (win/lose, share grid, compass bearings work normally)

- [ ] **Step 4: Commit if all looks good**

```bash
git add index.html tfl_stations.json tfl_lines.json
git commit -m "chore: regenerate map data — graphical positions, full Piccadilly branches"
```

---

## Self-Review

**Spec coverage:**
- ✅ Graphical circle extraction (Task 3 replaces text-label extraction)
- ✅ Step-free marker normalization (`_find_graphical_markers` detects blue markers, treats as standard circles)
- ✅ Piccadilly Uxbridge branch: 11 stations added (Tasks 1–2)
- ✅ Piccadilly Heathrow branch intermediates: 8 stations added (Tasks 1–2)
- ✅ Pipeline run (Task 4)
- ✅ Browser verification checklist (Task 4, Step 3)

**Placeholder scan:** No TBD or TODO items. All code blocks are complete.

**Type consistency:** `_find_graphical_markers(drawings: list) -> list[tuple[float, float]]` — used consistently in both the tests and `extract_station_positions`. The `drawings` parameter in `main()` is already a list from `page.get_drawings()`.
