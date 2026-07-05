# Tube-le Codebase

## Overview
A Wordle-like game using the London Underground map. Players guess tube stations.

## Key Files
- `index.html` — the game front-end. Contains `STATIONS`, `LINES`, `ALL_EDGES` JS constants. Lines and Thames are rendered via the inlined `london-tube-net.svg` group.
- `london-tube-net.svg` — the pre-built Beck-style tube map SVG (1359×850 coordinate space). Inlined into `index.html` as `<g id="tube-map-src" style="display:none">` and cloned on each render.

## Rendering Architecture

### Map layer (london-tube-net.svg)
Two SVG files exist:
- **Inlined (stripped)**: `<g id="tube-map-src" style="display:none">` in `index.html` — ~28KB, no text labels, used for the puzzle phase.
- **Full file**: `london-tube-net.svg` — 737KB, all station text labels as vector glyphs, used for the post-game reveal via `<image href="london-tube-net.svg">`. The Networkle logo watermark has been stripped from this file (was previously masked at render time; now removed at the source).

On each render:
- `drawPuzzleScene(svg, guessCount, target)`: clones the inlined group.
  - Guesses 0–3: single greyscale clone (`filter:saturate(0)`).
  - Guess 4+: two clones stacked — greyscale base + colour overlay with only the target station's line groups visible (`colourFilterGroup` hides non-target lines).
- `drawFullMapScene(svg, target)`: uses `<image>` pointing to the full labeled SVG; a `<rect fill="#eee">` overlay masks the legend key (bottom-left).

### Selective colour reveal (guess 4+)
`LINE_SVG_CLASS` maps each line name to its SVG class letter (`l`=District, `m`=Circle, `n`=H&C, `q`=Metropolitan, `r`=Piccadilly, `s`=Northern, `t`=Central, `u`=Jubilee, `v`=Bakerloo). Victoria uses `stroke="#14a2e2"`, W&C uses `stroke="#67c6bc"`. `colourFilterGroup` recursively hides groups/paths whose class letters are not in the target's line set.

### Station markers (post-game only)
`SVG_CIRCLE_COORDS` maps 32 major interchange stations to their SVG circle positions. After the game ends:
- If the target has an entry in `SVG_CIRCLE_COORDS`, `drawTargetMarker` adds a red ring + pulse animation + name label at that position.
- Non-interchange stations: no marker drawn on the map. The result modal names the station.

`STATIONS[*].coords` are derived from `london-tube-net.svg` tick-mark positions (32 interchanges use confirmed SVG circle positions; the rest are matched to the nearest line tick-mark). There is no build script for this — coords were patched into `index.html` directly. The old PDF-extraction pipeline (`build_map_from_tfl_pdf.py` and friends) has been removed; it produced inaccurate, sometimes-duplicate coordinates.

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
- Waterloo & City line is included in `LINES` and in the BFS graph. Bank↔Waterloo is 1 stop, which is factually correct.
- Each STATIONS entry has a `year:` field (opening year on Underground network).
- No `display_only` stations exist for Elizabeth or DLR.

## Tests
No automated tests (all verification is manual per spec).

## Running
No build step — `index.html` is a static file, open it directly or serve the directory.

## Development Notes
- Use `uv run --no-project` for all Python execution (there are currently no Python scripts in this repo; add this note back if a pipeline script is reintroduced).
