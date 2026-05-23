# SVG Map Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current station-position extraction (text-label snapping) with interchange-marker extraction that captures the actual compound circle shapes from the TfL PDF, and render those shapes in the game instead of generic circles.

**Architecture:** Three new pure functions — `_extract_interchange_markers`, `_group_markers`, `_match_markers_to_stations` — are added to `build_map_from_tfl_pdf.py` and tested without PyMuPDF. The pipeline `main()` is updated to derive station coords and SVG path data from the actual graphical marker shapes, storing them in a new `TFL_INTERCHANGE_MARKERS` JS constant. The game gains a `drawMarker(svg, name)` helper that renders the real marker shape instead of a synthetic circle.

**Tech Stack:** Python/PyMuPDF (`uv run --no-project --script`), vanilla JS/SVG in `index.html`. Tests run with `uv run --no-project --script tests/test_svg_extraction.py`.

---

## File Structure

| File | Change |
|------|--------|
| `build_map_from_tfl_pdf.py` | Add 3 new functions + constants; update `main()` |
| `tests/test_svg_extraction.py` | New — 9 unit tests (no PyMuPDF) |
| `tests/test_station_extraction.py` | Delete |
| `index.html` | Add `TFL_INTERCHANGE_MARKERS` placeholder; add `drawMarker`; update `drawTargetMarker`, `drawFullMapScene`, `drawNeighbourGraph` |

---

## Task 1: Delete old test file, scaffold new one

**Files:**
- Delete: `tests/test_station_extraction.py`
- Create: `tests/test_svg_extraction.py`

- [ ] **Step 1: Delete old test file**

```bash
rm tests/test_station_extraction.py
```

- [ ] **Step 2: Create new test file scaffold**

Create `tests/test_svg_extraction.py`:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Tests for interchange marker extraction in build_map_from_tfl_pdf."""
import sys
sys.path.insert(0, '.')
from build_map_from_tfl_pdf import (
    _extract_interchange_markers,
    _group_markers,
    _group_centre,
    _match_markers_to_stations,
)


def _circle_d(cx, cy, r, fill=(1.0, 1.0, 1.0)):
    """Fake drawing dict for a white filled circle (station marker)."""
    return {
        'fill': fill,
        'rect': (cx - r, cy - r, cx + r, cy + r),
        'type': 'f',
        'items': [
            ('c', None, None, None, None),
            ('c', None, None, None, None),
            ('c', None, None, None, None),
            ('c', None, None, None, None),
        ],
    }


def _rect_d(cx, cy, w, h, fill=(1.0, 1.0, 1.0)):
    """Fake drawing dict for a filled rectangle (no curves)."""
    return {
        'fill': fill,
        'rect': (cx - w/2, cy - h/2, cx + w/2, cy + h/2),
        'type': 'f',
        'items': [('l', None, None), ('l', None, None), ('l', None, None)],
    }


def _mk(cx, cy, r=3):
    """Minimal marker dict for grouping/matching tests."""
    return {'rect': (cx - r, cy - r, cx + r, cy + r), 'items': []}


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

- [ ] **Step 3: Verify scaffold runs (zero tests, zero failures)**

```bash
uv run --no-project --script tests/test_svg_extraction.py
```

Expected:
```
0/0 passed
```

---

## Task 2: Implement `_extract_interchange_markers` (TDD)

**Files:**
- Modify: `build_map_from_tfl_pdf.py` (after `_find_graphical_markers`, around line 450)
- Modify: `tests/test_svg_extraction.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_svg_extraction.py` (before the `if __name__ == '__main__':` block):

```python
# --- _extract_interchange_markers ---

def test_extracts_white_curved_drawing():
    result = _extract_interchange_markers([_circle_d(100, 100, 3)])
    assert len(result) == 1

def test_rejects_non_white_fill():
    result = _extract_interchange_markers([_circle_d(100, 100, 3, fill=(1.0, 0.0, 0.0))])
    assert len(result) == 0

def test_rejects_oversized_marker():
    # bbox = 30×30, exceeds MARKER_BBOX_MAX=20
    result = _extract_interchange_markers([_circle_d(100, 100, 15)])
    assert len(result) == 0

def test_rejects_undersized_marker():
    # bbox = 3×3, below minimum 4
    result = _extract_interchange_markers([_circle_d(100, 100, 1.5)])
    assert len(result) == 0

def test_rejects_straight_only_drawing():
    result = _extract_interchange_markers([_rect_d(100, 100, 8, 8)])
    assert len(result) == 0
```

- [ ] **Step 2: Run to confirm all 5 fail**

```bash
uv run --no-project --script tests/test_svg_extraction.py
```

Expected: 5 FAIL with `ImportError` or `AttributeError` on `_extract_interchange_markers`.

- [ ] **Step 3: Implement the function**

Add to `build_map_from_tfl_pdf.py` after the `SNAP_RADIUS` / `normalise` block (around line 450). Add the constant and function:

```python
MARKER_BBOX_MAX = 20.0  # PDF units — max side length of a station circle bbox

def _extract_interchange_markers(drawings: list) -> list[dict]:
    """Return all white-filled curved drawings — the station circle markers."""
    out = []
    for d in drawings:
        fill = d.get('fill')
        if not fill or not all(c > 0.85 for c in fill[:3]):
            continue
        rect = d.get('rect')
        if rect is None:
            continue
        if isinstance(rect, tuple):
            x0, y0, x1, y1 = rect
        else:
            x0, y0, x1, y1 = rect.x0, rect.y0, rect.x1, rect.y1
        w, h = x1 - x0, y1 - y0
        if not (4.0 <= w <= MARKER_BBOX_MAX and 4.0 <= h <= MARKER_BBOX_MAX):
            continue
        if not any(it[0] == 'c' for it in d.get('items', [])):
            continue
        out.append(d)
    return out
```

- [ ] **Step 4: Run tests — expect 5 pass**

```bash
uv run --no-project --script tests/test_svg_extraction.py
```

Expected:
```
  PASS  test_extracts_white_curved_drawing
  PASS  test_rejects_non_white_fill
  PASS  test_rejects_oversized_marker
  PASS  test_rejects_undersized_marker
  PASS  test_rejects_straight_only_drawing

5/5 passed
```

---

## Task 3: Implement `_group_markers` and `_group_centre` (TDD)

**Files:**
- Modify: `build_map_from_tfl_pdf.py`
- Modify: `tests/test_svg_extraction.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_svg_extraction.py` (before `if __name__ == '__main__':`):

```python
# --- _group_markers ---

def test_groups_adjacent_circles():
    # gap between bboxes = 107-103 = 4 < threshold 8 → one group
    m1, m2 = _mk(100, 100), _mk(107, 100)
    result = _group_markers([m1, m2])
    assert len(result) == 1
    assert len(result[0]) == 2

def test_separates_distant_circles():
    # gap = 120-103 = 17 > threshold 8 → two groups
    m1, m2 = _mk(100, 100), _mk(120, 100)
    result = _group_markers([m1, m2])
    assert len(result) == 2

def test_groups_three_touching():
    # Major interchange: three touching circles
    m1, m2, m3 = _mk(100, 100), _mk(107, 100), _mk(114, 100)
    result = _group_markers([m1, m2, m3])
    assert len(result) == 1
    assert len(result[0]) == 3

# --- _group_centre ---

def test_group_centre_single():
    group = [{'rect': (100, 100, 108, 108)}]
    cx, cy = _group_centre(group)
    assert cx == 104.0 and cy == 104.0

def test_group_centre_compound():
    group = [{'rect': (100, 100, 108, 108)}, {'rect': (108, 100, 116, 108)}]
    cx, cy = _group_centre(group)
    assert cx == 108.0 and cy == 104.0
```

- [ ] **Step 2: Run to confirm 5 new failures**

```bash
uv run --no-project --script tests/test_svg_extraction.py
```

Expected: 5 FAIL on `_group_markers` and `_group_centre`.

- [ ] **Step 3: Implement the functions**

Add to `build_map_from_tfl_pdf.py` after `_extract_interchange_markers`:

```python
MARKER_GROUP_DIST = 8.0  # PDF units — max gap between adjacent circles in a compound shape

def _bbox_gap(d1: dict, d2: dict) -> float:
    """Minimum distance between the bounding boxes of two marker dicts."""
    def coords(d):
        r = d['rect']
        return r if isinstance(r, tuple) else (r.x0, r.y0, r.x1, r.y1)
    ax0, ay0, ax1, ay1 = coords(d1)
    bx0, by0, bx1, by1 = coords(d2)
    dx = max(0.0, max(ax0, bx0) - min(ax1, bx1))
    dy = max(0.0, max(ay0, by0) - min(ay1, by1))
    return (dx * dx + dy * dy) ** 0.5

def _group_markers(markers: list[dict], threshold: float = MARKER_GROUP_DIST) -> list[list[dict]]:
    """Group nearby markers into compound interchange shapes using union-find."""
    n = len(markers)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            if _bbox_gap(markers[i], markers[j]) <= threshold:
                pi, pj = find(i), find(j)
                if pi != pj:
                    parent[pi] = pj

    from collections import defaultdict
    groups: dict[int, list[dict]] = defaultdict(list)
    for i, m in enumerate(markers):
        groups[find(i)].append(m)
    return list(groups.values())

def _group_centre(group: list[dict]) -> tuple[float, float]:
    """Bounding-box centre of the union of all markers in a compound group."""
    def coords(d):
        r = d['rect']
        return r if isinstance(r, tuple) else (r.x0, r.y0, r.x1, r.y1)
    all_coords = [coords(d) for d in group]
    x0 = min(c[0] for c in all_coords)
    y0 = min(c[1] for c in all_coords)
    x1 = max(c[2] for c in all_coords)
    y1 = max(c[3] for c in all_coords)
    return (x0 + x1) / 2, (y0 + y1) / 2
```

- [ ] **Step 4: Run tests — expect 10 pass**

```bash
uv run --no-project --script tests/test_svg_extraction.py
```

Expected:
```
  PASS  test_extracts_white_curved_drawing
  ... (5 from Task 2)
  PASS  test_groups_adjacent_circles
  PASS  test_separates_distant_circles
  PASS  test_groups_three_touching
  PASS  test_group_centre_single
  PASS  test_group_centre_compound

10/10 passed
```

---

## Task 4: Implement `_match_markers_to_stations` (TDD)

**Files:**
- Modify: `build_map_from_tfl_pdf.py`
- Modify: `tests/test_svg_extraction.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_svg_extraction.py` (before `if __name__ == '__main__':`):

```python
# --- _match_markers_to_stations ---

def test_matches_close_group_to_station():
    # Group centre = (104, 104), text label = (106, 106) → distance ~2.8 — should match
    groups = [[_mk(104, 104)]]
    text_pos = {'Angel': (106.0, 106.0)}
    result = _match_markers_to_stations(groups, text_pos)
    assert 'Angel' in result
    assert result['Angel'] is groups[0]

def test_does_not_match_distant_station():
    # Group centre = (104, 104), station text label at (250, 250) → ~207 units away > 100
    groups = [[_mk(104, 104)]]
    text_pos = {'Morden': (250.0, 250.0)}
    result = _match_markers_to_stations(groups, text_pos)
    assert 'Morden' not in result

def test_does_not_reuse_group():
    # Two stations competing for the same nearest group — only the closer one wins
    groups = [[_mk(100, 100)]]
    text_pos = {'Angel': (102.0, 100.0), 'Bank': (110.0, 100.0)}
    result = _match_markers_to_stations(groups, text_pos)
    assert 'Angel' in result
    assert 'Bank' not in result
```

- [ ] **Step 2: Run to confirm 3 new failures**

```bash
uv run --no-project --script tests/test_svg_extraction.py
```

Expected: 10 pass, 3 fail on `_match_markers_to_stations`.

- [ ] **Step 3: Implement the function**

Add to `build_map_from_tfl_pdf.py` after `_group_centre`:

```python
MARKER_MATCH_RADIUS = 100.0  # PDF units — max text-label to marker distance for a match

def _match_markers_to_stations(
    groups: list[list[dict]],
    text_positions: dict[str, tuple[float, float]],
    match_radius: float = MARKER_MATCH_RADIUS,
) -> dict[str, list[dict]]:
    """Match each marker group to a station name using text-label positions as reference.

    For each station in text_positions, finds the nearest unused group within
    match_radius PDF units of the text-label position. Groups beyond match_radius
    produce a warning and the station is omitted from the result.
    """
    used: set[int] = set()
    result: dict[str, list[dict]] = {}

    for name, (tx, ty) in text_positions.items():
        best_dist = float('inf')
        best_i = -1
        for i, group in enumerate(groups):
            if i in used:
                continue
            cx, cy = _group_centre(group)
            dist = ((cx - tx) ** 2 + (cy - ty) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best_i = i

        if best_i >= 0 and best_dist <= match_radius:
            result[name] = groups[best_i]
            used.add(best_i)
        else:
            print(f'  marker miss ({best_dist:.1f}u): {name}')

    return result
```

- [ ] **Step 4: Run tests — expect all 13 pass**

```bash
uv run --no-project --script tests/test_svg_extraction.py
```

Expected:
```
  PASS  test_extracts_white_curved_drawing
  PASS  test_rejects_non_white_fill
  PASS  test_rejects_oversized_marker
  PASS  test_rejects_undersized_marker
  PASS  test_rejects_straight_only_drawing
  PASS  test_groups_adjacent_circles
  PASS  test_separates_distant_circles
  PASS  test_groups_three_touching
  PASS  test_group_centre_single
  PASS  test_group_centre_compound
  PASS  test_matches_close_group_to_station
  PASS  test_does_not_match_distant_station
  PASS  test_does_not_reuse_group

13/13 passed
```

- [ ] **Step 5: Commit**

```bash
git add build_map_from_tfl_pdf.py tests/test_svg_extraction.py
git commit -m "feat: add interchange marker extraction — _extract_interchange_markers, _group_markers, _match_markers_to_stations"
```

---

## Task 5: Update `main()` to use new marker-based station coords and generate `TFL_INTERCHANGE_MARKERS`

**Files:**
- Modify: `build_map_from_tfl_pdf.py` (the `main()` function, ~lines 635–815)

The current `main()` calls `extract_station_positions(page, drawings)` to get station coords from text-label snapping. We replace this with the new marker-based flow. The line stroke extraction and patching logic are otherwise unchanged.

- [ ] **Step 1: Replace station coord derivation in `main()`**

Find this block in `main()`:

```python
    # Extract stations first — their positions bound the diagram area
    # (excluding the legend/key boxes on the right of the page).
    raw_stations = extract_station_positions(page, drawings)
    if not raw_stations:
        raise SystemExit('No stations extracted')
    sxs = [p[0] for p in raw_stations.values()]
    sys_ = [p[1] for p in raw_stations.values()]
    pad = 25
    mn_x = min(sxs) - pad; mx_x = max(sxs) + pad
    mn_y = min(sys_) - pad; mx_y = max(sys_) + pad
    print(f'Diagram bounds (from stations): '
          f'X {mn_x:.1f}..{mx_x:.1f}, Y {mn_y:.1f}..{mx_y:.1f}')
```

Replace with:

```python
    # Extract station positions from graphical marker shapes, not text labels.
    text_positions = _extract_text_labels(page)
    raw_markers = _extract_interchange_markers(drawings)
    grouped = _group_markers(raw_markers)
    matched = _match_markers_to_stations(grouped, text_positions)
    if not matched:
        raise SystemExit('No interchange markers matched to stations')

    raw_stations: dict[str, tuple[float, float]] = {
        name: _group_centre(group) for name, group in matched.items()
    }
    sxs = [p[0] for p in raw_stations.values()]
    sys_ = [p[1] for p in raw_stations.values()]
    pad = 25
    mn_x = min(sxs) - pad; mx_x = max(sxs) + pad
    mn_y = min(sys_) - pad; mx_y = max(sys_) + pad
    print(f'Diagram bounds (from markers): '
          f'X {mn_x:.1f}..{mx_x:.1f}, Y {mn_y:.1f}..{mx_y:.1f}')
```

- [ ] **Step 2: Add `TFL_INTERCHANGE_MARKERS` generation after the station coord block**

Find this line in `main()`:

```python
    tx = mn_x - off_x / scale
    ty = mn_y - off_y / scale
```

After that line (and before the `by_line` loop), add:

```python
    # Generate SVG path data for each interchange marker compound shape.
    interchange_markers: dict[str, list[str]] = {}
    for name, group in matched.items():
        paths = []
        for d in group:
            d_attr = items_to_d(d.get('items', []), tx, ty, scale)
            if d_attr:
                paths.append(d_attr)
        if paths:
            interchange_markers[name] = paths
```

- [ ] **Step 3: Add `TFL_INTERCHANGE_MARKERS` patching after `TFL_LINE_PATHS` patching**

Find this block at the end of `main()`:

```python
    HTML.write_text(html2)
    return 0
```

Replace with:

```python
    # 3) Inject (or replace) TFL_INTERCHANGE_MARKERS const after TFL_LINE_PATHS.
    markers_js = 'const TFL_INTERCHANGE_MARKERS = ' + json.dumps(interchange_markers, indent=2) + ';\n'
    if 'const TFL_INTERCHANGE_MARKERS' in html2:
        html2 = re.sub(
            r'const TFL_INTERCHANGE_MARKERS = \{[\s\S]*?\};\n',
            markers_js,
            html2,
            count=1,
        )
    else:
        # Insert immediately after TFL_LINE_PATHS block.
        marker = 'const TFL_LINE_PATHS'
        idx = html2.find(marker)
        if idx == -1:
            print('Could not find TFL_LINE_PATHS insertion point', file=sys.stderr)
            return 1
        end_block = html2.find(';\n', idx)
        if end_block == -1:
            print('Could not find end of TFL_LINE_PATHS block', file=sys.stderr)
            return 1
        insert_at = end_block + 2
        html2 = html2[:insert_at] + markers_js + html2[insert_at:]
        print('Inserted TFL_INTERCHANGE_MARKERS after TFL_LINE_PATHS.')

    HTML.write_text(html2)
    return 0
```

- [ ] **Step 4: Add `TFL_INTERCHANGE_MARKERS` placeholder to `index.html`**

Find in `index.html` the line:

```js
const TFL_LINE_PATHS = {
```

The pipeline will insert TFL_INTERCHANGE_MARKERS after TFL_LINE_PATHS on the first run. To make the placeholder present for the regex on subsequent runs, add it manually right after the closing `};` of TFL_LINE_PATHS:

```js
const TFL_INTERCHANGE_MARKERS = {}; // patched by build_map_from_tfl_pdf.py
```

Search for the end of TFL_LINE_PATHS (the `};` on its own line after the line paths block) and insert the placeholder on the next line.

- [ ] **Step 5: Run the pipeline**

```bash
uv run --no-project --script build_map_from_tfl_pdf.py
```

Expected output (approximately):
```
Diagram bounds (from markers): X 15.0..1027.5, Y 99.8..695.8
Strokes accepted: 39, skipped (colour off-target): 18, skipped (station validation): 67
tfl_lines.json: 39 path strings across 12 lines
tfl_stations.json: 227 stations
Patched 227 STATIONS entries.
Inserted TFL_INTERCHANGE_MARKERS after TFL_LINE_PATHS.  ← first run only
```

If you see many `marker miss` lines, increase `MARKER_MATCH_RADIUS` in steps of 20 and re-run until misses are below 5.

- [ ] **Step 6: Verify TFL_INTERCHANGE_MARKERS in index.html**

```bash
grep -c '"M' index.html
```

This should be significantly higher than before (each path `d` string starts with `M`). Also verify:

```bash
python3 -c "
import json, re
html = open('index.html').read()
m = re.search(r'const TFL_INTERCHANGE_MARKERS = (\{[\s\S]*?\});', html)
data = json.loads(m.group(1))
kc = data.get(\"King's Cross St. Pancras\", [])
print(f\"King's Cross paths: {len(kc)}\")
print(f'Total stations: {len(data)}')
" 2>/dev/null || uv run --no-project python3 -c "
import json, re
html = open('index.html').read()
m = re.search(r'const TFL_INTERCHANGE_MARKERS = (\{[\s\S]*?\});', html)
data = json.loads(m.group(1))
kc = data.get(\"King\'s Cross St. Pancras\", [])
print(f\"King\'s Cross paths: {len(kc)}\")
print(f'Total stations: {len(data)}')
"
```

Expected: King's Cross paths ≥ 3, Total stations ≈ 200+.

- [ ] **Step 7: Run tests to confirm nothing broken**

```bash
uv run --no-project --script tests/test_svg_extraction.py
```

Expected: 13/13 passed.

- [ ] **Step 8: Commit**

```bash
git add build_map_from_tfl_pdf.py index.html tfl_stations.json tfl_lines.json
git commit -m "feat: derive station coords from interchange markers, generate TFL_INTERCHANGE_MARKERS"
```

---

## Task 6: Add `drawMarker` to game rendering and update callers

**Files:**
- Modify: `index.html`

- [ ] **Step 1: Add `drawMarker` helper function**

Find the `drawTargetMarker` function in `index.html` (around line 2089). Insert the following NEW function directly before it:

```js
function drawMarker(svg, name, opts = {}) {
  // Renders the actual TfL interchange marker shape for a station.
  // Falls back to a synthetic circle if TFL_INTERCHANGE_MARKERS is absent
  // or the station has no entry (display-only stations not in the PDF).
  const { stroke = '#0a0a0a', strokeWidth = 1.8, fill = '#fff' } = opts;
  const paths = (typeof TFL_INTERCHANGE_MARKERS !== 'undefined')
    ? TFL_INTERCHANGE_MARKERS[name]
    : null;
  if (paths && paths.length) {
    for (const d of paths) {
      svg.appendChild(el('path', {
        d, fill, stroke, 'stroke-width': strokeWidth,
        'stroke-linejoin': 'round'
      }));
    }
  } else {
    // Fallback: plain circle at station coords
    const s = STATIONS[name];
    if (!s) return;
    const r = s.lines.length >= 2 ? 4.5 : 3.3;
    svg.appendChild(el('circle', {
      cx: s.coords[0], cy: s.coords[1], r,
      fill, stroke, 'stroke-width': strokeWidth
    }));
  }
}
```

- [ ] **Step 2: Update `drawTargetMarker` to use `drawMarker`**

Replace the body of `drawTargetMarker` (lines ~2089–2145). Find:

```js
function drawTargetMarker(svg, targetName, showLabel) {
  const t = STATIONS[targetName];
  const lineCount = t.lines.length;
  // For interchange (2+ lines), TFL uses an oblong white shape with black outline.
  // For single-line stations we'd use a tick — but visually for the puzzle we always
  // use the interchange shape so the central station is unmistakable.
  const g = el('g', { class:'target-marker' });
  const r = Math.min(14, 9 + lineCount * 0.8);
  if (lineCount === 1) {
    g.appendChild(el('circle', {
      cx:t.coords[0], cy:t.coords[1], r:8,
      fill:'#fff', stroke:'#0a0a0a','stroke-width':3
    }));
  } else {
    g.appendChild(el('circle', {
      cx:t.coords[0], cy:t.coords[1], r:r,
      fill:'#fff', stroke:'#0a0a0a','stroke-width':3.2
    }));
    g.appendChild(el('circle', {
      cx:t.coords[0], cy:t.coords[1], r:r*0.45,
      fill:'#0a0a0a'
    }));
  }
  // pulse on first render
  const pulse = el('circle', {
    cx:t.coords[0], cy:t.coords[1], r:r+2,
    fill:'none', stroke:'#DC241F','stroke-width':2
  });
```

Replace the entire function body up to (but not including) the `showLabel` block and closing `svg.appendChild(g)`) with:

```js
function drawTargetMarker(svg, targetName, showLabel) {
  const t = STATIONS[targetName];
  const g = el('g', { class:'target-marker' });

  // Real interchange marker shape from TfL PDF data
  drawMarker(g, targetName, { strokeWidth: 2.5 });

  // Pulse ring — centred on station coords, radius independent of shape
  const pulse = el('circle', {
    cx: t.coords[0], cy: t.coords[1], r: 14,
    fill: 'none', stroke: '#DC241F', 'stroke-width': 2
  });
```

Then find the `pulse.animate(` call and update its starting `r` to match:

```js
  pulse.animate(
    [{ r: 14, opacity: 0.7 }, { r: 44, opacity: 0 }],
    { duration: 1800, iterations: 1, easing:'cubic-bezier(.2,.7,.2,1)' }
  );
  g.appendChild(pulse);
```

Leave the `if (showLabel)` block and final `svg.appendChild(g)` unchanged.

- [ ] **Step 3: Update `drawFullMapScene` all-stations loop to use `drawMarker`**

Find in `drawFullMapScene`:

```js
  // 3. All station markers
  const markers = el('g', { class:'all-stations' });
  for (const [name, s] of Object.entries(STATIONS)) {
    if (name === target) continue; // target drawn last on top
    const r = s.lines.length >= 2 ? 4.5 : 3.3;
    const g = el('g', { class:'stn-marker' });
    g.appendChild(el('circle', {
      cx: s.coords[0], cy: s.coords[1], r,
      fill:'#fff', stroke:'#0a0a0a', 'stroke-width': 1.6
    }));
    // hover tooltip via SVG <title>
    const title = document.createElementNS('http://www.w3.org/2000/svg','title');
    title.textContent = `${name} · Zone ${s.zone}`;
    g.appendChild(title);
    markers.appendChild(g);
  }
```

Replace with:

```js
  // 3. All station markers
  const markers = el('g', { class:'all-stations' });
  for (const [name, s] of Object.entries(STATIONS)) {
    if (name === target) continue; // target drawn last on top
    const g = el('g', { class:'stn-marker' });
    drawMarker(g, name, { strokeWidth: 1.6 });
    // hover tooltip via SVG <title>
    const title = document.createElementNS('http://www.w3.org/2000/svg','title');
    title.textContent = `${name} · Zone ${s.zone}`;
    g.appendChild(title);
    markers.appendChild(g);
  }
```

- [ ] **Step 4: Update neighbour markers in `drawNeighbourGraph` to use `drawMarker`**

Find in `drawNeighbourGraph`:

```js
  // small marker for each neighbour (no label)
  for (const n of neighborSet) {
    const c = STATIONS[n].coords;
    g.appendChild(el('circle', {
      cx:c[0], cy:c[1], r:6.5,
      fill:'#fff', stroke:'#0a0a0a','stroke-width':2.2,
      opacity:0
    }));
  }
```

Replace with:

```js
  // small marker for each neighbour (no label)
  for (const n of neighborSet) {
    const ng = el('g', { style: 'opacity:0' });
    drawMarker(ng, n, { strokeWidth: 2.0 });
    g.appendChild(ng);
  }
```

Note: the `opacity:0` is now on the `<g>` wrapper; the animation at the bottom of `drawNeighbourGraph` iterates `[...g.children]` and sets `opacity:'1'` on each child — this will now set opacity on the `<g>` wrappers, which is correct.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat: add drawMarker helper, use real TfL interchange shapes in game rendering"
```

---

## Task 7: Visual verification

**Files:** No code changes — open browser and verify.

- [ ] **Step 1: Open `index.html` in a browser**

```bash
# WSL: open via Windows file explorer, or:
explorer.exe "$(wslpath -w index.html)"
```

Or navigate to the file in any browser.

- [ ] **Step 2: Check puzzle mode (before any guess)**

Start a new puzzle. Verify:
- The target interchange shows the actual marker shape from the TfL map (e.g. if the target is King's Cross, you should see three touching circles, not a single large circle)
- Lines are grey (uncoloured) and show only short stubs

- [ ] **Step 3: Make guesses and check progressive reveal**

- After guess 1: lines turn to their TfL colours
- After guess 2: neighbour stations appear with their actual marker shapes
- After guess 4: full network visible with Thames
- After guess 5+: zone revealed

- [ ] **Step 4: Check the full post-game map**

Trigger a win or use the share button to see the full map. Verify:
- Every station shows its proper marker shape (compound circles at interchanges, single circles at terminal/single-line stations)
- No Overground lines visible
- Line geometry has correct Beck-style 45° angles

- [ ] **Step 5: Fix any issues found**

Common issues and fixes:
- **Many `marker miss` warnings at pipeline runtime**: increase `MARKER_MATCH_RADIUS` from 100 to 120 in `build_map_from_tfl_pdf.py` and re-run the pipeline.
- **Marker shapes appear tiny or in wrong position**: check that `items_to_d` is being called with the correct `tx, ty, scale` values (should be the same values used for line paths).
- **Neighbour markers don't fade in**: check that the animation loop in `drawNeighbourGraph` still references `[...g.children]` — the wrapper `<g>` elements should be direct children.

- [ ] **Step 6: Commit final state if fixes were made**

```bash
git add build_map_from_tfl_pdf.py index.html
git commit -m "fix: adjust marker extraction parameters after visual verification"
```

---

## Task 8: Update CLAUDE.md and clean up

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update CLAUDE.md**

Find the station extraction pipeline section and update it to reflect the new architecture:

Replace:
```
1. `_extract_text_labels(page)` — scans text spans at station-label point size (~4.2pt), builds a name→(cx,cy) dict using greedy chain matching.
2. `_find_graphical_markers(drawings)` — scans `page.get_drawings()` for:
   - **White station circles**: fill≈(1,1,1), ≥3 curve items, bounding box 4–9.5 PDF units wide/tall.
   - **Step-free access markers**: TfL cyan-blue rectangles, fill in R∈(0.05,0.30) G∈(0.55,0.85) B∈(0.75,1.0), bounding box 6.5–12 PDF units.
3. `extract_station_positions(page, drawings)` — calls both, snaps each text-label position to nearest graphical marker within `SNAP_RADIUS=90` PDF units. Falls back to text-label position with a warning on snap miss. `normalise()` expands fi/fl ligatures (U+FB01/U+FB02) before chain-matching so names like "Northfields" match the PDF's ligated form.
```

With:
```
1. `_extract_text_labels(page)` — scans text spans at ~4.2pt, builds name→(cx,cy) for use as reference positions in station matching. `normalise()` expands fi/fl ligatures (U+FB01/U+FB02).
2. `_extract_interchange_markers(drawings)` — scans `page.get_drawings()` for white-filled curved elements (fill > 0.85, bbox 4–20 PDF units, ≥1 cubic curve item). Returns the full drawing dicts (including `items` for SVG path generation).
3. `_group_markers(markers)` — union-find grouping of markers whose bboxes are within `MARKER_GROUP_DIST=8` PDF units. Compound interchanges (King's Cross, Waterloo etc.) produce multi-element groups.
4. `_match_markers_to_stations(groups, text_positions)` — matches each group to the nearest text-label position within `MARKER_MATCH_RADIUS=100` PDF units. Group bounding-box centres become station coords.
5. SVG path data for each marker group is generated via `items_to_d` and stored as `TFL_INTERCHANGE_MARKERS` in `index.html`.
```

Also update the Tests section:
```
## Tests
- `tests/test_svg_extraction.py` — 13 tests for `_extract_interchange_markers`, `_group_markers`, `_group_centre`, and `_match_markers_to_stations` (run with `uv run --no-project --script tests/test_svg_extraction.py`).
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md — new interchange marker extraction architecture"
```

---

## Self-Review

**Spec coverage:**
- ✅ Correct Beck-style line geometry — line paths unchanged; still extracted from PDF via `items_to_d`
- ✅ Interchange marker shapes — `_extract_interchange_markers` + `_group_markers` + SVG path data stored in `TFL_INTERCHANGE_MARKERS`
- ✅ Station coords from marker positions — `_group_centre` replaces text-label snapping
- ✅ Thames — unchanged (`extract_thames_from_pdf.py` / `THAMES_PATH`)
- ✅ No Overground — station-proximity validation retained (colour-only filtering insufficient for Mildmay/Piccadilly proximity)
- ✅ Compound interchange shapes in rendering — `drawMarker` renders real path data; `drawFullMapScene`, `drawTargetMarker`, `drawNeighbourGraph` all updated
- ✅ Tests — 13 unit tests, no PyMuPDF dependency

**Placeholder scan:** No TBDs or TODOs. All code is complete.

**Type consistency:**
- `_group_centre` returns `tuple[float, float]` — used correctly everywhere
- `_match_markers_to_stations` returns `dict[str, list[dict]]` — `matched.items()` used correctly in main()
- `drawMarker(svg, name, opts)` — called consistently with `(g, name)` or `(g, name, {...})` in all three call sites
