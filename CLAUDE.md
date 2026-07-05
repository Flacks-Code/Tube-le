# Tube-le Codebase

## Overview
A Wordle-like game using the London Underground map. Players guess tube stations.

## Key Files
- `index.html` — the game front-end. Contains `STATIONS`, `LINES`, `ALL_EDGES` JS constants. Lines and Thames are rendered via the inlined `london-tube-net.svg` group.
- `london-tube-net.svg` — the pre-built Beck-style tube map SVG (1359×850 coordinate space). Inlined into `index.html` as `<g id="tube-map-src" style="display:none">` and cloned on each render.
- `build_map_from_tfl_pdf.py` — legacy pipeline; extracts station positions from the TfL PDF. No longer used: `STATIONS[*].coords` are retained in the data but not used by any rendering code.
- `tube_map_tfl.pdf` — source TfL standard tube map PDF (not committed).

## Rendering Architecture

### Map layer (london-tube-net.svg)
Two SVG files exist:
- **Inlined (stripped)**: `<g id="tube-map-src" style="display:none">` in `index.html` — ~28KB, no text labels, used for the puzzle phase.
- **Full file**: `london-tube-net.svg` — 741KB, all station text labels as vector glyphs, used for the post-game reveal via `<image href="london-tube-net.svg">`.

On each render:
- `drawPuzzleScene(svg, guessCount, target)`: clones the inlined group.
  - Guesses 0–3: single greyscale clone (`filter:saturate(0)`).
  - Guess 4+: two clones stacked — greyscale base + colour overlay with only the target station's line groups visible (`colourFilterGroup` hides non-target lines).
- `drawFullMapScene(svg, target)`: uses `<image>` pointing to the full labeled SVG; two `<rect fill="#eee">` overlays mask the logo (bottom-right) and legend key (bottom-left).

### Selective colour reveal (guess 4+)
`LINE_SVG_CLASS` maps each line name to its SVG class letter (`l`=District, `m`=Circle, `n`=H&C, `q`=Metropolitan, `r`=Piccadilly, `s`=Northern, `t`=Central, `u`=Jubilee, `v`=Bakerloo). Victoria uses `stroke="#14a2e2"`, W&C uses `stroke="#67c6bc"`. `colourFilterGroup` recursively hides groups/paths whose class letters are not in the target's line set.

### Station markers (post-game only)
`SVG_CIRCLE_COORDS` maps 32 major interchange stations to their SVG circle positions. After the game ends:
- If the target has an entry in `SVG_CIRCLE_COORDS`, `drawTargetMarker` adds a red ring + pulse animation + name label at that position.
- Non-interchange stations: no marker drawn on the map. The result modal names the station.

`STATIONS[*].coords` values are present in the data but **not used** by any rendering function.

### Progressive reveal sequence (6 guesses total)
| After wrong guess | Clue |
|---|---|
| 1 | Opening year chip |
| 2 | North or south of the river chip (`SOUTH_STATIONS` set encodes Thames-side) |
| 3 | Zone chip |
| 4 | Lines chip + colour revealed simultaneously (target lines in colour on greyscale base) |
| 5 | First letter chip |
| 6 | Game over if still wrong |

### Game data
- Elizabeth line and DLR removed from the game entirely.
- Waterloo & City line removed from `LINES` (so it builds no BFS edges) because the Bank↔Waterloo 1-stop shortcut made distances feel counterintuitively short. W&C remains in `STATIONS.lines` for Bank and Waterloo for display accuracy (lines chip, colour reveal).
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
