# Map Data Fix — Design Spec

**Date:** 2026-05-18
**Scope:** Fix three visual problems with the game map: missing line branches, misaligned Thames, and station dots offset from their lines. All fixes are data/pipeline changes; no game logic changes beyond one filter line.

---

## Problem statement

Three issues affect the map rendering:

1. **Missing branches** — large portions of the network are absent: Central West Ruislip and Hainault/Fairlop loop, District Richmond and Wimbledon branches, Metropolitan Amersham/Chesham/Watford branches, Elizabeth Shenfield and Reading branches, most of the DLR network.
2. **River misalignment** — `THAMES_PATH` was extracted from the Wikimedia Commons SVG using a different coordinate transform than the station coords and line paths (which come from the TFL PDF). The river is visually offset.
3. **Station dots off lines** — station label positions in the PDF sit beside the line marker, not on it. The pipeline extracted label centres, so dots appear offset from the strokes they should sit on.

### Root cause

`build_map_from_tfl_pdf.py` validates each stroke by checking proximity to known stations (`STATION_HITS_MIN = 2`). Branch strokes are filtered out because there are no STATIONS entries for intermediate or terminal stations on the missing branches — no hooks, no validation hits, so the strokes are discarded.

---

## What does NOT change

- Puzzle mechanics, scoring, BFS distance, bearing, win/lose logic.
- The 96 existing playable stations — they remain selectable as daily targets.
- The rendering architecture (TFL_LINE_PATHS SVG paths, viewBox camera, reveal layers).
- The single-file HTML deliverable with no build step.

---

## Solution

### Fix 1 — Missing branches (Option C: improve PDF pipeline)

Extend `build_map_from_tfl_pdf.py` with ~70 new stations added to both `TARGETS` (so their coords are extracted and written to `tfl_stations.json`) and `LINE_STATIONS` (so they act as validation anchors, enabling the pipeline to accept the branch strokes).

New stations are marked `display_only: true` in `STATIONS`. They appear on the map and participate in the adjacency graph (BFS, line-exit angles for neighbours), but are never selected as puzzle targets.

### Fix 2 — River misalignment

Run `extract_thames_from_pdf.py` (already written). It derives the Thames outline from the TFL PDF using the same coordinate transform as the station/line data, replacing `THAMES_PATH` in index.html.

### Fix 3 — Station dots off lines

Run `snap_stations_to_lines.py` (already written). It samples `TFL_LINE_PATHS` densely and snaps each station's coords to the nearest point on its own line paths.

---

## New stations (display-only)

### Central line

**West Ruislip branch** — branches at North Acton (new junction station):
`West Acton`, `North Acton`, `Hanger Lane`, `Perivale`, `Greenford`, `Northolt`, `South Ruislip`, `Ruislip Gardens`, `West Ruislip`

LINES sequence addition:
```
["North Acton", "Hanger Lane", "Perivale", "Greenford", "Northolt", "South Ruislip", "Ruislip Gardens", "West Ruislip"]
```
Also insert `West Acton` and `North Acton` into the existing Ealing Broadway sequence between `Ealing Broadway` and `East Acton`.

**Hainault / Fairlop loop** — loop from Leytonstone via Woodford:
`Wanstead`, `Redbridge`, `Gants Hill`, `Newbury Park`, `Barkingside`, `Fairlop`, `Hainault`, `Grange Hill`, `Chigwell`, `Roding Valley`, `Woodford`, `South Woodford`, `Snaresbrook`

LINES sequence additions (two sequences to represent the loop):
```
["Leytonstone", "Wanstead", "Redbridge", "Gants Hill", "Newbury Park", "Barkingside", "Fairlop", "Hainault", "Grange Hill", "Chigwell", "Roding Valley", "Woodford"]
["Woodford", "South Woodford", "Snaresbrook", "Leytonstone"]
```
Also insert `Snaresbrook`, `South Woodford`, `Woodford` into the Epping main-line sequence between `Leytonstone` and `Epping`.

### District line

**Richmond branch** — branches at Turnham Green (existing):
`Gunnersbury`, `Kew Gardens`, `Richmond`

LINES sequence addition:
```
["Turnham Green", "Gunnersbury", "Kew Gardens", "Richmond"]
```

**Wimbledon branch** — branches at Earl's Court (existing):
`Fulham Broadway`, `Parsons Green`, `Putney Bridge`, `East Putney`, `Southfields`, `Wimbledon Park`, `Wimbledon`

LINES sequence addition:
```
["Earl's Court", "Fulham Broadway", "Parsons Green", "Putney Bridge", "East Putney", "Southfields", "Wimbledon Park", "Wimbledon"]
```

### Metropolitan line

`Preston Road`, `Northwick Park`, `Harrow-on-the-Hill`, `North Harrow`, `Pinner`, `Northwood Hills`, `Northwood`, `Moor Park`, `Croxley`, `Watford`, `Rickmansworth`, `Chorleywood`, `Chalfont & Latimer`, `Amersham`, `Chesham`

LINES sequence changes — extend existing Uxbridge sequence and add branches:
```
// Extend: Wembley Park → ... → Harrow-on-the-Hill → ... → Uxbridge (via Rayners Lane)
// Amersham/Chesham branch:
["Harrow-on-the-Hill", "Moor Park", "Rickmansworth", "Chorleywood", "Chalfont & Latimer", "Amersham"]
["Chalfont & Latimer", "Chesham"]
// Watford branch:
["Moor Park", "Croxley", "Watford"]
```
Exact Met line topology (junction points between Harrow-on-the-Hill, Uxbridge branch, and Amersham branch) to be confirmed against the PDF during implementation.

### Elizabeth line

**Shenfield branch** — extends Stratford (existing):
`Maryland`, `Manor Park`, `Forest Gate`, `Ilford`, `Seven Kings`, `Goodmayes`, `Chadwell Heath`, `Romford`, `Gidea Park`, `Harold Wood`, `Brentwood`, `Shenfield`

LINES sequence change — extend existing `["Liverpool Street", "Stratford"]` to:
```
["Liverpool Street", "Stratford", "Maryland", "Manor Park", "Forest Gate", "Ilford", "Seven Kings", "Goodmayes", "Chadwell Heath", "Romford", "Gidea Park", "Harold Wood", "Brentwood", "Shenfield"]
```

**Reading branch** — extends from Paddington (existing) via Ealing Broadway (existing):
`Acton Main Line`, `West Ealing`, `Hanwell`, `Southall`, `Hayes & Harlington`, `West Drayton`, `Iver`, `Langley`, `Slough`, `Burnham`, `Taplow`, `Maidenhead`, `Twyford`, `Reading`

LINES sequence change — extend existing `["Paddington", "Ealing Broadway"]` to:
```
["Paddington", "Acton Main Line", "Ealing Broadway", "West Ealing", "Hanwell", "Southall", "Hayes & Harlington", "West Drayton", "Iver", "Langley", "Slough", "Burnham", "Taplow", "Maidenhead", "Twyford", "Reading"]
```

### DLR

Replace the current 3 minimal stubs with complete sequences. New stations:
`Tower Gateway`, `Shadwell`, `Limehouse`, `Westferry`, `Poplar`, `West India Quay`, `Heron Quays`, `South Quay`, `Crossharbour`, `Mudchute`, `Island Gardens`, `Cutty Sark`, `Greenwich`, `Deptford Bridge`, `Elverson Road`, `Stratford High Street`, `Abbey Road`, `Royal Victoria`, `Custom House`, `Prince Regent`, `Royal Albert`, `Beckton Park`, `Cyprus`, `Gallions Reach`, `Beckton`, `Pudding Mill Lane`, `Devons Road`, `Bow Church`, `Langdon Park`, `All Saints`, `Silvertown`, `London City Airport`, `King George V`, `Woolwich Arsenal`

Note: `Woolwich Arsenal` (DLR) is a distinct station from `Woolwich` (Elizabeth line) — separate STATIONS entry.

LINES DLR sequences (replacing current):
```
// Bank → Lewisham (main trunk)
["Bank", "Shadwell", "Limehouse", "Westferry", "Poplar", "West India Quay", "Canary Wharf", "Heron Quays", "South Quay", "Crossharbour", "Mudchute", "Island Gardens", "Cutty Sark", "Greenwich", "Deptford Bridge", "Elverson Road", "Lewisham"]
// Tower Gateway branch (separate terminus converging at Shadwell/Limehouse)
["Tower Gateway", "Shadwell"]
// Stratford → West Ham (via Stratford High Street / Abbey Road)
["Stratford", "Stratford High Street", "Abbey Road", "West Ham"]
// Stratford → Canary Wharf via Poplar
["Stratford", "Pudding Mill Lane", "Devons Road", "Bow Church", "Langdon Park", "All Saints", "Poplar"]
// Canning Town → Beckton
["Canning Town", "Royal Victoria", "Custom House", "Prince Regent", "Royal Albert", "Beckton Park", "Cyprus", "Gallions Reach", "Beckton"]
// Canning Town → Woolwich Arsenal
["Canning Town", "Silvertown", "London City Airport", "King George V", "Woolwich Arsenal"]
// Poplar ↔ Canning Town (connecting the two main trunks)
["Poplar", "All Saints", "Langdon Park", "Bow Church", "Devons Road", "Pudding Mill Lane", "Stratford"]
```

---

## Code changes

### `build_map_from_tfl_pdf.py`

1. Add all ~70 new stations to `TARGETS`.
2. Add them to `LINE_STATIONS` under their respective lines — this is what enables the validator to accept branch strokes.
3. Add `ALIASES` entries for any stations whose PDF label text differs from the canonical name (e.g., `"Chalfont & Latimer"` vs `"Chalfont and Latimer"`).

### `index.html` — STATIONS

Add ~70 new entries. Each entry has the standard shape plus `display_only: true`:
```js
"Richmond": { coords:[0,0], zone:4, lines:["District"], river:"far", display_only:true },
```
`coords` is written as `[0,0]` — the pipeline overwrites it with real values. `zone` and `river` are set to correct values (they're shown as info chips in the puzzle only if the station is the target, which display-only stations never are — but accurate data is preferable).

### `index.html` — LINES

Add/extend sequences as described above.

### `index.html` — game logic

Two one-line changes:

```js
// Before:
const STATION_NAMES = Object.keys(STATIONS);

// After:
const STATION_NAMES = Object.keys(STATIONS).filter(n => !STATIONS[n].display_only);
```

Autocomplete also filters: `Object.keys(STATIONS).filter(n => !STATIONS[n].display_only)` as the candidate list in `renderAC`.

---

## Pipeline run order

After all code changes are in place:

```bash
# 1. Extract station coords + line paths from PDF
uv run --no-project --script build_map_from_tfl_pdf.py

# 2. Replace Thames path with PDF-extracted version (same coordinate system)
uv run --no-project --script extract_thames_from_pdf.py

# 3. Snap station dots onto actual line geometry
uv run --no-project --script snap_stations_to_lines.py
```

Steps 2 and 3 are independent of each other but both depend on step 1 having established the coordinate transform.

---

## Verification

Open `index.html` in a browser and confirm:

- All named branches are visible on the full map (post-win reveal): District to Richmond and Wimbledon, Central to West Ruislip and Hainault loop, Met to Amersham/Chesham/Watford, Elizabeth to Reading and Shenfield, full DLR network.
- Station dots sit on their lines (not offset beside them).
- The Thames runs through the correct stations (beneath Westminster, Waterloo, London Bridge area).
- Display-only stations do not appear in the autocomplete dropdown.
- Picking a station adjacent to a new branch (e.g. Turnham Green, Earl's Court) shows the correct exit stubs in the puzzle view.
- Existing gameplay is unaffected: BFS distances, compass bearings, reveal layers, win/lose, share grid.
