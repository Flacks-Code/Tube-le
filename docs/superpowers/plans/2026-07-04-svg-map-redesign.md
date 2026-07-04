# SVG Map Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all dynamic map rendering with a pre-built SVG (`london-tube-net.svg`), drop Elizabeth and DLR from the game, add opening year as a progressive clue, and adjust the coordinate space to 1359×850.

**Architecture:** The SVG is inlined into index.html as a hidden `<g id="tube-map-src">`. Each render call clones this group and appends it (clipped and/or desaturated) to the game SVG. Station coordinates are re-derived by re-running the PDF pipeline with the new dimensions. The PDF pipeline continues to be used solely for station coordinate extraction.

**Tech Stack:** HTML/JS (single-file game), Python/uv (pipeline scripts), london-tube-net.svg (new map source)

**Spec:** `docs/superpowers/specs/2026-07-04-svg-map-redesign.md`

**Note on testing:** The approved spec explicitly states "All verification is manual (no automated tests for this work)." Tasks therefore have no failing-test steps.

---

## File Structure

| File | Change |
|------|--------|
| `build_map_from_tfl_pdf.py` | Change `MAP_W=1400, MAP_H=900` → `1359, 850` |
| `index.html` | All data and rendering changes (see tasks below) |
| `fetch_station_years.py` | New one-use script — Wikipedia scraper |
| `apply_years.py` | New one-use script — patches year: field into STATIONS |
| `inline_svg.py` | New one-use script — inlines london-tube-net.svg into index.html |
| `extract_thames_from_pdf.py` | Delete |
| `tests/test_station_extraction.py` | Delete |

---

## Task 1: Update pipeline dimensions and regenerate station coordinates

**Files:**
- Modify: `build_map_from_tfl_pdf.py:30`
- Side effect: patches `index.html` STATIONS coords when run

**Context:** `build_map_from_tfl_pdf.py` has `MAP_W, MAP_H = 1400, 900` at line 30. The new SVG coordinate space is 1359×850. Changing these constants and re-running the pipeline regenerates all station `coords` in the new space. The pipeline still produces correct station coordinates because it uses text-label snapping from the PDF — the coordinate transform output just maps to the new game dimensions.

- [ ] **Step 1: Change MAP_W and MAP_H**

In `build_map_from_tfl_pdf.py`, change line 30:
```python
# old
MAP_W, MAP_H = 1400, 900
# new
MAP_W, MAP_H = 1359, 850
```

- [ ] **Step 2: Run the pipeline**

```bash
uv run --no-project --script build_map_from_tfl_pdf.py
```

Expected output: station coord extraction completes, warnings about snap misses are normal. The pipeline will patch `STATIONS[*].coords` in index.html with values in the 1359×850 coordinate space.

- [ ] **Step 3: Commit**

```bash
git add build_map_from_tfl_pdf.py index.html
git commit -m "feat: update pipeline and station coords to 1359×850 coordinate space"
```

---

## Task 2: Remove Elizabeth line and DLR from game data

**Files:**
- Modify: `index.html` — LINES, TFL_LINE_PATHS, STATIONS, LINE_ORDER, LINE_EMOJI

**Context:** The new SVG has no Elizabeth or DLR geometry. These lines and their exclusive stations must be removed from all JS data structures. The changes are:

**STATIONS — delete these entries entirely** (DLR/Elizabeth only, no other Underground lines):
- `"Lewisham"` — DLR only
- `"Woolwich"` — Elizabeth only  
- `"Abbey Wood"` — Elizabeth only

**STATIONS — remove Elizabeth/DLR from `lines` arrays** (stations that remain but shared with Underground):
- `"Farringdon"` — remove `"Elizabeth"` (keep Circle, H&C, Metropolitan)
- `"Paddington"` — remove `"Elizabeth"` (keep Bakerloo, Circle, District, H&C)
- `"Bond Street"` — remove `"Elizabeth"` (keep Central, Jubilee)
- `"Tottenham Court Road"` — remove `"Elizabeth"` (keep Central, Northern)
- `"Liverpool Street"` — remove `"Elizabeth"` (keep Central, Circle, H&C)
- `"Whitechapel"` — remove `"Elizabeth"` (keep District, H&C)
- `"Canary Wharf"` — remove `"DLR"` and `"Elizabeth"` (keep Jubilee)
- `"Stratford"` — remove `"DLR"` and `"Elizabeth"` (keep Central, Jubilee)
- `"West Ham"` — remove `"DLR"` (keep District, H&C, Jubilee)
- `"Canning Town"` — remove `"DLR"` (keep Jubilee)
- `"Bank"` — remove `"DLR"` (keep Central, Northern, Waterloo & City)
- `"Ealing Broadway"` — remove `"Elizabeth"` (keep Central, District)
- `"Heathrow Terminals 2 & 3"` — remove `"Elizabeth"` (keep Piccadilly)
- `"Heathrow Terminal 4"` — remove `"Elizabeth"` (keep Piccadilly)
- `"Heathrow Terminal 5"` — remove `"Elizabeth"` (keep Piccadilly)

**LINES — delete these entire entries:**
- `"DLR": { color: ..., sequences: [...] }` (lines ~1151–1173 in current file)
- `"Elizabeth": { color: ..., sequences: [...] }` (lines ~1174–1192)

**TFL_LINE_PATHS — delete these entries:**
- `"DLR": [...]`
- `"Elizabeth": [...]`

**LINE_ORDER — remove `'DLR'` and `'Elizabeth'`:**
```js
// old
const LINE_ORDER = ['Bakerloo','Central','Circle','District','Hammersmith & City',
                    'Jubilee','Metropolitan','Northern','Piccadilly','Victoria',
                    'Waterloo & City','DLR','Elizabeth'];
// new
const LINE_ORDER = ['Bakerloo','Central','Circle','District','Hammersmith & City',
                    'Jubilee','Metropolitan','Northern','Piccadilly','Victoria',
                    'Waterloo & City'];
```

**LINE_ABBREV — remove `"DLR"` and `"Elizabeth"` entries:**
```js
// old
const LINE_ABBREV = {
  "Bakerloo":"BAK","Central":"CEN","Circle":"CIR","District":"DIS",
  "Hammersmith & City":"H&C","Jubilee":"JUB","Metropolitan":"MET",
  "Northern":"NOR","Piccadilly":"PIC","Victoria":"VIC",
  "Waterloo & City":"W&C","DLR":"DLR","Elizabeth":"ELZ"
};
// new
const LINE_ABBREV = {
  "Bakerloo":"BAK","Central":"CEN","Circle":"CIR","District":"DIS",
  "Hammersmith & City":"H&C","Jubilee":"JUB","Metropolitan":"MET",
  "Northern":"NOR","Piccadilly":"PIC","Victoria":"VIC",
  "Waterloo & City":"W&C"
};
```

**LINE_EMOJI — remove `"DLR"` and `"Elizabeth"` entries:**
```js
// old
const LINE_EMOJI = {
  "Bakerloo":"🟧","Central":"🟥","Circle":"🟨","District":"🟩",
  "Hammersmith & City":"🟪","Jubilee":"⬜","Metropolitan":"🟪",
  "Northern":"⬛","Piccadilly":"🟦","Victoria":"🟦",
  "Waterloo & City":"🟨","DLR":"⬛","Elizabeth":"🟪"
};
// new
const LINE_EMOJI = {
  "Bakerloo":"🟧","Central":"🟥","Circle":"🟨","District":"🟩",
  "Hammersmith & City":"🟪","Jubilee":"⬜","Metropolitan":"🟪",
  "Northern":"⬛","Piccadilly":"🟦","Victoria":"🟦",
  "Waterloo & City":"🟨"
};
```

- [ ] **Step 1: Delete Lewisham, Woolwich, Abbey Wood from STATIONS**

Find these three entries (lines ~856–858 in pre-task-1 index.html, coords may differ after task 1) and delete them:
```js
  "Lewisham":   { coords:[...], zone:2, lines:["DLR"], river:"far" },
  "Woolwich":   { coords:[...], zone:4, lines:["Elizabeth"], river:"close" },
  "Abbey Wood": { coords:[...], zone:4, lines:["Elizabeth"], river:"close" },
```

- [ ] **Step 2: Remove Elizabeth/DLR from shared station lines arrays**

For each station listed above, remove the `"Elizabeth"` or `"DLR"` string from its `lines` array. Example:
```js
// old
"Bank": { coords:[...], zone:1, lines:["Central","Northern","Waterloo & City","DLR"], river:"close" },
// new
"Bank": { coords:[...], zone:1, lines:["Central","Northern","Waterloo & City"], river:"close" },
```

Apply similarly to all 15 stations listed above.

- [ ] **Step 3: Delete LINES["DLR"] and LINES["Elizabeth"]**

In the `LINES` constant, delete the entire `"DLR": { ... }` block and `"Elizabeth": { ... }` block (both with their sequences arrays). These are large multi-line blocks.

- [ ] **Step 4: Delete TFL_LINE_PATHS["DLR"] and TFL_LINE_PATHS["Elizabeth"]**

In the `TFL_LINE_PATHS` constant, delete the `"DLR": [...]` and `"Elizabeth": [...]` entries.

- [ ] **Step 5: Update LINE_ORDER, LINE_ABBREV, and LINE_EMOJI**

Replace all three constants with the new versions shown above.

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "feat: remove Elizabeth line and DLR from all game data"
```

---

## Task 3: Fetch and apply station opening years

**Files:**
- Create: `fetch_station_years.py` (one-use)
- Create: `apply_years.py` (one-use)
- Modify: `index.html` (adds `year:` field to every STATIONS entry)

**Context:** Opening year is a new progressive clue (revealed after wrong guess 2). It is stored as a `year:` field on each STATIONS entry. Data is sourced from the Wikipedia "List of London Underground stations" article.

- [ ] **Step 1: Create fetch_station_years.py**

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["requests", "beautifulsoup4"]
# ///

import json
import re
import requests
from bs4 import BeautifulSoup

url = "https://en.wikipedia.org/wiki/List_of_London_Underground_stations"
resp = requests.get(url, headers={"User-Agent": "Tube-le/1.0"})
resp.raise_for_status()
soup = BeautifulSoup(resp.text, "html.parser")

table = soup.find("table", {"class": "wikitable"})
headers = [th.get_text(strip=True).lower() for th in table.find_all("tr")[0].find_all(["th", "td"])]
print("Headers:", headers)

year_col = next((i for i, h in enumerate(headers) if "open" in h or "year" in h), None)
if year_col is None:
    raise ValueError(f"Could not find year column. Headers: {headers}")
print(f"Year column index: {year_col}")

years = {}
for row in table.find_all("tr")[1:]:
    cells = row.find_all(["td", "th"])
    if len(cells) <= year_col:
        continue
    name = re.sub(r"\[.*?\]", "", cells[0].get_text(strip=True)).strip()
    year_text = cells[year_col].get_text(strip=True)
    m = re.search(r"\b(\d{4})\b", year_text)
    if m and name:
        years[name] = int(m.group(1))

with open("station_years.json", "w") as f:
    json.dump(years, f, indent=2, sort_keys=True)

print(f"Fetched {len(years)} station years → station_years.json")
```

- [ ] **Step 2: Run it**

```bash
uv run --no-project --script fetch_station_years.py
```

Expected: `station_years.json` created with entries like `"Angel": 1901`, `"Bank": 1900`, etc. Verify it has 250+ entries.

- [ ] **Step 3: Create apply_years.py**

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import json
import re

with open("station_years.json") as f:
    year_data = json.load(f)

def norm(s):
    return s.lower().replace("'", "'").replace("’", "'").replace("&", "and").strip()

year_lookup = {norm(k): v for k, v in year_data.items()}

with open("index.html") as f:
    lines = f.readlines()

modified = 0
missing = []
for i, line in enumerate(lines):
    m = re.match(r'\s+"([^"]+)":\s*\{.*\bzone:\d+', line)
    if not m:
        continue
    station_name = m.group(1)
    if "year:" in line:
        continue  # already patched
    key = norm(station_name)
    if key in year_lookup:
        year = year_lookup[key]
        lines[i] = re.sub(r"(\bzone:(\d+))", rf"\1, year:{year}", line, count=1)
        modified += 1
    else:
        missing.append(station_name)

if missing:
    print(f"WARNING — no year data for {len(missing)} stations:")
    for s in sorted(missing):
        print(f"  {s}")

with open("index.html", "w") as f:
    f.writelines(lines)

print(f"\nApplied year to {modified} stations.")
```

- [ ] **Step 4: Run it**

```bash
uv run --no-project --script apply_years.py
```

Expected: output shows years applied to most stations. Review the WARNING list carefully. For any station in the missing list that IS a playable station (not display_only), look up the year manually on Wikipedia and add `year:NNNN` to that entry in index.html directly.

Stations likely to require manual lookup (name mismatches with Wikipedia): "Hammersmith" (disambiguation), "Edgware Road", "King's Cross St. Pancras".

Use the rule from the spec: **use the year the station first opened on the Underground network in any form**, not the year it was rebuilt or renamed.

- [ ] **Step 5: Verify year coverage**

Confirm with a quick grep that every non-display_only STATIONS entry has a year field:

```bash
grep -P '"[^"]+": \{ coords' index.html | grep -v display_only | grep -v "year:" | head -20
```

Expected: no output (all non-display_only stations have year). If any are missing, add manually.

- [ ] **Step 6: Commit**

```bash
git add index.html fetch_station_years.py apply_years.py station_years.json
git commit -m "feat: add opening year to all STATIONS entries"
```

---

## Task 4: Inline london-tube-net.svg into index.html

**Files:**
- Create: `inline_svg.py` (one-use)
- Modify: `index.html` — adds `<g id="tube-map-src">` before `</body>`

**Context:** The SVG file (`london-tube-net.svg`, 741KB) contains the complete Beck-style tube map. Its inner content (everything between the outer `<svg>` tags) is wrapped in a hidden `<g>` and injected into index.html. This group is cloned each render by the JS rendering code.

The SVG's `<style>` block uses short class names (`.j`, `.k`, etc.) that will apply globally when the SVG content is part of the HTML document. This is expected and correct — no naming conflicts with existing index.html CSS which uses descriptive class names.

- [ ] **Step 1: Create inline_svg.py**

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import re

with open("london-tube-net.svg", "r", encoding="utf-8") as f:
    svg = f.read()

# Strip the outer <svg ...> opening tag and </svg> closing tag
inner = re.sub(r"^<svg[^>]*>\s*", "", svg.strip(), flags=re.DOTALL)
inner = re.sub(r"\s*</svg>\s*$", "", inner, flags=re.DOTALL)

group = f'<g id="tube-map-src" style="display:none">\n{inner}\n</g>'

with open("index.html", "r", encoding="utf-8") as f:
    html = f.read()

if 'id="tube-map-src"' in html:
    print("ERROR: tube-map-src already present in index.html — aborting")
    raise SystemExit(1)

html = html.replace("</body>", f"{group}\n</body>")

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"Done — tube-map-src group ({len(group):,} chars) injected before </body>")
```

- [ ] **Step 2: Run it**

```bash
uv run --no-project --script inline_svg.py
```

Expected: prints "Done — tube-map-src group (... chars) injected before </body>".

- [ ] **Step 3: Verify injection**

```bash
grep -c 'tube-map-src' index.html
```

Expected: `2` (one on the `<g>` opening tag, one as a reference later — or `1` if no references yet).

```bash
grep -n 'tube-map-src\|</body>' index.html | tail -5
```

Expected: the `<g id="tube-map-src">` line appears just before `</body>`.

- [ ] **Step 4: Commit**

```bash
git add index.html inline_svg.py
git commit -m "feat: inline london-tube-net.svg as hidden tube-map-src group"
```

---

## Task 5: Update game SVG constants, add chip-year HTML/CSS, update legend

**Files:**
- Modify: `index.html` — JS constants MAP_W/MAP_H/ASPECT, HTML chips, legend text

**Context:** Three independent changes in this task:
1. Game JS coordinate constants must match new SVG space (1359×850)
2. A new `chip-year` element is added between chip-zone and chip-letter in the HTML overlay
3. The legend text in the map panel is updated to show the new reveal sequence

- [ ] **Step 1: Update MAP_W, MAP_H, and ASPECT**

Find (around line 1598):
```js
const MAP_W = 1400, MAP_H = 900;
const ASPECT = 9/14;
```

Replace with:
```js
const MAP_W = 1359, MAP_H = 850;
const ASPECT = 850/1359;
```

- [ ] **Step 2: Add chip-year HTML element**

Find (around line 674–675):
```html
      <div class="chip" id="chip-zone"><span class="dot"></span><span id="chip-zone-text">Zone —</span></div>
      <div class="chip" id="chip-letter"><span class="dot" style="background:var(--bar)"></span><span id="chip-letter-text">Starts with —</span></div>
```

Replace with:
```html
      <div class="chip" id="chip-zone"><span class="dot"></span><span id="chip-zone-text">Zone —</span></div>
      <div class="chip" id="chip-year"><span class="dot"></span><span id="chip-year-text">Opened —</span></div>
      <div class="chip" id="chip-letter"><span class="dot" style="background:var(--bar)"></span><span id="chip-letter-text">Starts with —</span></div>
```

- [ ] **Step 3: Update legend text**

Find (around line 701–708):
```html
    <div class="legend" id="legend">
      <strong>The reveal</strong>
      <div class="legend-row"><b>Guess 1+</b> Lines light up in colour</div>
      <div class="legend-row"><b>Guess 3+</b> Connecting tracks appear</div>
      <div class="legend-row"><b>Guess 4+</b> Zone revealed</div>
      <div class="legend-row"><b>Guess 5+</b> River Thames shown</div>
      <div class="legend-row"><b>Guess 6</b> First letter revealed</div>
    </div>
```

Replace with:
```html
    <div class="legend" id="legend">
      <strong>The reveal</strong>
      <div class="legend-row"><b>Wrong guess 1</b> Zone revealed</div>
      <div class="legend-row"><b>Wrong guess 2</b> Opening year revealed</div>
      <div class="legend-row"><b>Wrong guess 3</b> Map view expands</div>
      <div class="legend-row"><b>Wrong guess 4</b> Colour revealed</div>
      <div class="legend-row"><b>Wrong guess 5</b> Full map shown</div>
      <div class="legend-row"><b>Wrong guess 6</b> First letter revealed</div>
    </div>
```

- [ ] **Step 4: Add chip-year to resetPuzzle()**

Find (around line 1348–1349):
```js
  $('#chip-zone').classList.remove('show');
  $('#chip-letter').classList.remove('show');
```

Replace with:
```js
  $('#chip-zone').classList.remove('show');
  $('#chip-year').classList.remove('show');
  $('#chip-letter').classList.remove('show');
```

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat: update coordinate constants, add chip-year, update legend for new reveal sequence"
```

---

## Task 6: Rewrite drawPuzzleScene with SVG clone rendering

**Files:**
- Modify: `index.html` — `drawPuzzleScene` function (currently lines ~1797–1872)

**Context:** The current drawPuzzleScene iterates TFL_LINE_PATHS, draws coloured line segments, draws neighbour markers, and calls drawTargetMarker. The new version simply clones the pre-built SVG group, applies clip and desaturation filter, and calls drawTargetMarker. All line geometry, Thames, and interchange circles are in the SVG already.

**New reveal logic within the puzzle scene:**
- `guessCount < 3` (wrong guesses 0, 1, 2): clip radius 54
- `guessCount 3–4` (wrong guesses 3, 4): clip radius 214
- `guessCount >= 5` (wrong guess 5): no clip (full map)
- `guessCount < 4`: apply `filter: saturate(0)` (desaturated)
- `guessCount >= 4`: no filter (full colour)

- [ ] **Step 1: Replace the entire drawPuzzleScene function**

Find the entire function from `function drawPuzzleScene(svg, target, guessCount) {` through its closing `}`, and replace with:

```js
function drawPuzzleScene(svg, target, guessCount) {
  const t = STATIONS[target];

  // Clip radius: 54 for guesses 0-2, 214 for guesses 3-4, none at 5+
  const clipR = guessCount < 3 ? 54 : guessCount < 5 ? 214 : null;

  if (clipR !== null) {
    const defs = el('defs');
    const cp = el('clipPath', { id: 'map-clip' });
    cp.appendChild(el('circle', { cx: t.coords[0], cy: t.coords[1], r: clipR }));
    defs.appendChild(cp);
    svg.appendChild(defs);
  }

  // Clone the pre-built SVG map group
  const mapGroup = document.getElementById('tube-map-src').cloneNode(true);
  mapGroup.style.display = '';
  if (clipR !== null) mapGroup.setAttribute('clip-path', 'url(#map-clip)');
  if (guessCount < 4) mapGroup.style.filter = 'saturate(0)';
  svg.appendChild(mapGroup);

  drawTargetMarker(svg, target, false);
}
```

- [ ] **Step 2: Commit**

```bash
git add index.html
git commit -m "feat: rewrite drawPuzzleScene using SVG clone rendering"
```

---

## Task 7: Rewrite drawFullMapScene with SVG clone rendering

**Files:**
- Modify: `index.html` — `drawFullMapScene` function (currently lines ~1874–1973)

**Context:** The current drawFullMapScene calls drawThames, iterates TFL_LINE_PATHS, draws all station markers as circles, then draws the target marker. The new version clones the SVG group (unclipped, full colour) and draws only the target marker on top. Station markers are already in the SVG as interchange circles. The halo animation code that was in the old drawFullMapScene body is now in drawTargetMarker (as done in Task 8).

- [ ] **Step 1: Replace the entire drawFullMapScene function**

Find the function from `function drawFullMapScene(svg, target) {` through its closing `}`, and replace with:

```js
function drawFullMapScene(svg, target) {
  // Clone the pre-built SVG map group — full colour, no clip
  const mapGroup = document.getElementById('tube-map-src').cloneNode(true);
  mapGroup.style.display = '';
  svg.appendChild(mapGroup);

  drawTargetMarker(svg, target, true);
}
```

- [ ] **Step 2: Commit**

```bash
git add index.html
git commit -m "feat: rewrite drawFullMapScene using SVG clone rendering"
```

---

## Task 8: Simplify drawTargetMarker and update renderMap reveal thresholds

**Files:**
- Modify: `index.html` — `drawTargetMarker` function, `renderMap` function

**Context:** `drawTargetMarker` currently sizes the circle based on line count and draws compound shapes. The spec simplifies it to a fixed-radius white circle with a red pulse ring (radius 10). The SVG already shows the correct interchange shape beneath the marker.

`renderMap` needs updated chip reveal thresholds (zone at 1+, year at 2+, letter at 5+) and updated setView widths matching the new clip radii.

- [ ] **Step 1: Replace the entire drawTargetMarker function**

Find the function from `function drawTargetMarker(svg, targetName, showLabel) {` through its closing `}`, and replace with:

```js
function drawTargetMarker(svg, targetName, showLabel) {
  const t = STATIONS[targetName];
  const [cx, cy] = t.coords;
  const r = 10;
  const g = el('g', { class: 'target-marker' });

  const pulse = el('circle', { cx, cy, r: r + 2, fill: 'none', stroke: '#DC241F', 'stroke-width': 2 });
  pulse.animate(
    [{ r: r + 2, opacity: 0.7 }, { r: r + 30, opacity: 0 }],
    { duration: 1800, iterations: 1, easing: 'cubic-bezier(.2,.7,.2,1)' }
  );
  g.appendChild(pulse);

  g.appendChild(el('circle', { cx, cy, r, fill: '#fff', stroke: '#0a0a0a', 'stroke-width': 3 }));

  if (showLabel) {
    g.appendChild(el('text', {
      x: cx, y: cy + r + 20,
      'text-anchor': 'middle',
      'font-family': 'Hammersmith One, sans-serif',
      'font-size': 18,
      fill: '#0a0a0a',
      'paint-order': 'stroke',
      stroke: '#FAF7F0',
      'stroke-width': 5
    }, targetName));
  }

  svg.appendChild(g);
}
```

- [ ] **Step 2: Update chip reveal thresholds in renderMap**

Find (around line 1776–1787):
```js
  // Reveal chips (DOM, outside SVG)
  if (guessCount >= 3 || ended) {
    $('#chip-zone-text').textContent = `Zone ${t.zone} · ${t.river === 'close' ? 'By the river' : t.river === 'medium' ? 'A walk from the river' : 'Inland'}`;
    $('#chip-zone').classList.add('show');
  } else {
    $('#chip-zone').classList.remove('show');
  }
  if (guessCount >= 5 || ended) {
    $('#chip-letter-text').textContent = `Starts with "${target[0]}"`;
    $('#chip-letter').classList.add('show');
  } else {
    $('#chip-letter').classList.remove('show');
  }
```

Replace with:
```js
  // Reveal chips (DOM, outside SVG)
  if (guessCount >= 1 || ended) {
    $('#chip-zone-text').textContent = `Zone ${t.zone} · ${t.river === 'close' ? 'By the river' : t.river === 'medium' ? 'A walk from the river' : 'Inland'}`;
    $('#chip-zone').classList.add('show');
  } else {
    $('#chip-zone').classList.remove('show');
  }
  if (guessCount >= 2 || ended) {
    $('#chip-year-text').textContent = `Opened ${t.year || '—'}`;
    $('#chip-year').classList.add('show');
  } else {
    $('#chip-year').classList.remove('show');
  }
  if (guessCount >= 5 || ended) {
    $('#chip-letter-text').textContent = `Starts with "${target[0]}"`;
    $('#chip-letter').classList.add('show');
  } else {
    $('#chip-letter').classList.remove('show');
  }
```

- [ ] **Step 3: Update setView widths in renderMap**

Find (around line 1766–1769):
```js
    drawPuzzleScene(svg, target, guessCount);
    const zoomLevel = guessCount < 2 ? 0 : (guessCount < 4 ? 1 : 2);
    setView(t.coords, [340, 620, 1100][zoomLevel]);
```

Replace with:
```js
    drawPuzzleScene(svg, target, guessCount);
    // View widths match clip radii: 54→300, 214→700, none→1100
    const viewW = guessCount < 3 ? 300 : guessCount < 5 ? 700 : 1100;
    setView(t.coords, viewW);
```

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: simplify drawTargetMarker, update reveal thresholds and view widths"
```

---

## Task 9: Remove dead code, delete obsolete scripts, update CLAUDE.md

**Files:**
- Modify: `index.html` — remove dead functions and constants
- Delete: `extract_thames_from_pdf.py`
- Delete: `tests/test_station_extraction.py`
- Delete: `fetch_station_years.py`, `apply_years.py`, `inline_svg.py`, `station_years.json` (one-use scripts now done)
- Modify: `CLAUDE.md`

**Context:** With drawPuzzleScene and drawFullMapScene rewritten, many functions and constants are now unreferenced dead code. Remove them to keep the codebase clean.

**Remove these functions from index.html:**
- `drawThames(svg, finalOpacity)` — no longer called
- `drawTargetExits(svg, targetName, guessCount, finalReveal)` — no longer called
- `getTargetExits(target)` — no longer called (used only by drawTargetExits)
- `drawNeighbourGraph(svg, targetName, guessCount, finalReveal)` — no longer called

**Remove these constants from index.html:**
- `const TFL_LINE_PATHS = { ... }` — large block, no longer referenced
- `const THAMES_PATH = "..."` — no longer referenced

**Note:** `const ADJ = ...` and `neighborsOf()` and `distance()` are still used by `renderHistory` / guess scoring — do NOT remove them.

- [ ] **Step 1: Remove TFL_LINE_PATHS constant**

Find `const TFL_LINE_PATHS = {` and delete the entire block (from that line through the closing `};`). This is a large multi-hundred-line block with path data for each line.

After deletion, verify no remaining references:
```bash
grep -n 'TFL_LINE_PATHS' index.html
```
Expected: no output.

- [ ] **Step 2: Remove THAMES_PATH constant**

Find `const THAMES_PATH =` (a single very long line) and delete it. After deletion:
```bash
grep -n 'THAMES_PATH' index.html
```
Expected: no output.

- [ ] **Step 3: Remove dead functions**

Delete each of these function bodies entirely:
- `function drawThames(svg, finalOpacity=0.95) { ... }`
- `function drawTargetExits(svg, targetName, guessCount, finalReveal) { ... }`
- `function getTargetExits(target) { ... }`
- `function drawNeighbourGraph(svg, targetName, guessCount, finalReveal) { ... }`

After deletion, verify no remaining calls:
```bash
grep -n 'drawThames\|drawTargetExits\|getTargetExits\|drawNeighbourGraph' index.html
```
Expected: no output.

- [ ] **Step 4: Delete obsolete files**

```bash
rm extract_thames_from_pdf.py
rm tests/test_station_extraction.py
rm fetch_station_years.py apply_years.py inline_svg.py station_years.json
```

- [ ] **Step 5: Update CLAUDE.md**

Replace the "Architecture: build_map_from_tfl_pdf.py" section and Key Files to reflect the new state. The pipeline no longer extracts Thames, interchange markers, or line paths — it's used only for station coordinate extraction. The SVG (`london-tube-net.svg`) is now the map source.

Update CLAUDE.md to:

```markdown
# Tube-le Codebase

## Overview
A Wordle-like game using the London Underground map. Players guess tube stations.

## Key Files
- `build_map_from_tfl_pdf.py` — extracts station positions from the TfL PDF and patches STATIONS[*].coords in index.html. Used solely for coordinate extraction; no longer generates line paths, Thames, or interchange markers.
- `index.html` — the game front-end. Contains STATIONS, LINES, ALL_EDGES JS constants. Lines and Thames are rendered via the inlined london-tube-net.svg group.
- `london-tube-net.svg` — the pre-built Beck-style tube map SVG (1359×850 coordinate space). Inlined into index.html as `<g id="tube-map-src" style="display:none">` and cloned on each render.
- `tube_map_tfl.pdf` — source TfL standard tube map PDF (not committed, must be present locally for pipeline runs).

## Architecture: build_map_from_tfl_pdf.py

### Coordinate system
- MAP_W=1359, MAP_H=850, MARGIN=40 — matches london-tube-net.svg coordinate space exactly.

### Station extraction pipeline
1. `_extract_text_labels(page)` — scans text spans at station-label point size (~4.2pt), builds a name→(cx,cy) dict using greedy chain matching.
2. `_find_graphical_markers(drawings)` — scans `page.get_drawings()` for white station circles and step-free access markers.
3. `extract_station_positions(page, drawings)` — snaps each text-label to nearest graphical marker within `SNAP_RADIUS=90` PDF units. `normalise()` expands fi/fl ligatures before matching.

### What the pipeline no longer does
- Does NOT generate TFL_LINE_PATHS (lines come from london-tube-net.svg)
- Does NOT generate THAMES_PATH (Thames is in london-tube-net.svg)
- Does NOT generate TFL_INTERCHANGE_MARKERS (interchange circles are in london-tube-net.svg)

## Rendering Architecture

### Map layer (london-tube-net.svg)
The SVG is inlined in index.html as `<g id="tube-map-src" style="display:none">`. On each render:
- `drawPuzzleScene`: clones the group, applies clipPath (r=54/214/none) and filter:saturate(0) per guess count
- `drawFullMapScene`: clones the group with no clip/filter

### Progressive reveal sequence (6 guesses total)
| After wrong guess | Clue |
|---|---|
| 1 | Zone shown in chip |
| 2 | Opening year shown in chip |
| 3 | Clip expands (r=54 → r=214) |
| 4 | Colour revealed (saturate(0) removed) |
| 5 | Full map (clip removed) |
| 6 | First letter of station name |

### Game data
- Elizabeth line and DLR are removed from the game entirely.
- Each STATIONS entry has a `year:` field (opening year on Underground network).
- No display_only stations exist for Elizabeth or DLR.

## Tests
No automated tests (per spec: all verification is manual).

## Running
```bash
uv run --no-project --script build_map_from_tfl_pdf.py
```
Requires `tube_map_tfl.pdf` and `index.html` present in the working directory.

## Development Notes
- Use `uv run --no-project` for all Python execution.
- `pymupdf` import is deferred into `main()` so the module can be imported in tests without pymupdf installed.
- SNAP_RADIUS=90, STATION_NEAR_RADIUS=40 PDF units (widened to handle stations with labels far from graphical circles and DLR coordinate shift).
```

- [ ] **Step 6: Commit**

```bash
git add index.html CLAUDE.md
git rm extract_thames_from_pdf.py tests/test_station_extraction.py
git rm fetch_station_years.py apply_years.py inline_svg.py station_years.json
git commit -m "chore: remove dead code, delete one-use scripts, update CLAUDE.md"
```

---

## Manual Verification Checklist

After all tasks are committed, open `index.html` in a browser and verify:

**1. Coordinate alignment**

Set 5–6 major interchange stations as the puzzle target in turn (by manually setting `puzzleOffset` in the browser console to target each). For each: confirm the white target marker dot sits on the correct line intersection in the SVG, not offset beside it.

Stations to check: King's Cross St. Pancras, Waterloo, Bank, Paddington, Victoria, Liverpool Street.

If misaligned: re-run the pipeline with adjusted `SNAP_RADIUS` or apply a uniform scale correction to all station coords.

**2. Reveal sequence**

Make 6 wrong guesses on a single puzzle. Confirm:
- After wrong guess 1: zone chip appears
- After wrong guess 2: year chip appears, map still desaturated, small clip
- After wrong guess 3: clip expands (more map visible), still desaturated
- After wrong guess 4: colour revealed (map becomes full colour)
- After wrong guess 5: full map visible (no clip), first letter chip appears
- On wrong guess 6: game over (lost)

**3. Data integrity**

- Confirm no Elizabeth or DLR stations appear in the autocomplete dropdown
- Confirm Canning Town autocompletes and its modal shows only Jubilee
- Confirm Bank's modal shows Central, Northern, Waterloo & City (no DLR)
- Confirm every non-display_only station shown has a non-zero year in its chip at guess 2

**4. Regression**

- Win flow: guess the correct station → modal shows Station Found, share grid works
- Lose flow: 6 wrong guesses → modal shows Out of Stops, full map shown
- Share grid: emojis match the station's remaining lines (no DLR/Elizabeth emojis)
- Compass bearings in guess history still show correct directions
