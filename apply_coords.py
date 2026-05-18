#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""
Read extracted_coords.json (SVG-space coords) and rewrite index.html's
STATIONS dictionary so each station's coords entry uses the rescaled values.

We preserve the game's existing 1400×900 viewBox by linearly mapping the
source-SVG coordinate envelope into that box with a small uniform margin.
Only the [x, y] inside `coords:[ ... ]` is touched; zone/lines/river are
left exactly as they were.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

HTML = Path('index.html')
COORDS = Path('extracted_coords.json')

MAP_W, MAP_H = 1400, 900
MARGIN = 30        # pixels of margin around the network in game-space

def rescale(coords: dict[str, list[float]]) -> dict[str, list[float]]:
    xs = [c[0] for c in coords.values()]
    ys = [c[1] for c in coords.values()]
    src_w = max(xs) - min(xs)
    src_h = max(ys) - min(ys)
    # Uniform scale to fit inside (MAP_W - 2*MARGIN) × (MAP_H - 2*MARGIN)
    avail_w = MAP_W - 2*MARGIN
    avail_h = MAP_H - 2*MARGIN
    scale = min(avail_w / src_w, avail_h / src_h)
    new_w = src_w * scale
    new_h = src_h * scale
    off_x = MARGIN + (avail_w - new_w) / 2
    off_y = MARGIN + (avail_h - new_h) / 2
    min_x, min_y = min(xs), min(ys)
    out: dict[str, list[float]] = {}
    for name, (x, y) in coords.items():
        nx = round((x - min_x) * scale + off_x, 1)
        ny = round((y - min_y) * scale + off_y, 1)
        out[name] = [nx, ny]
    return out

# Match a single STATIONS entry. The HTML uses canonical formatting
# (one entry per line) which lets us patch with a tight regex.
ENTRY_RE = re.compile(
    r'("([^"\\]+)":\s*{\s*coords:)\s*\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]'
)

def patch_html(html: str, coords: dict[str, list[float]]) -> tuple[str, list[str]]:
    replaced: list[str] = []
    unmatched_in_html: list[str] = []
    def repl(m: re.Match) -> str:
        head, name, _, _ = m.group(1), m.group(2), m.group(3), m.group(4)
        if name in coords:
            x, y = coords[name]
            replaced.append(name)
            return f'{head}[{x},{y}]'
        unmatched_in_html.append(name)
        return m.group(0)
    new_html, n = ENTRY_RE.subn(repl, html)
    return new_html, replaced

def main() -> int:
    coords_raw = json.loads(COORDS.read_text())
    coords = rescale(coords_raw)

    # Y range can be checked
    xs = [c[0] for c in coords.values()]
    ys = [c[1] for c in coords.values()]
    print(f'After rescale: X {min(xs):.0f}..{max(xs):.0f}, '
          f'Y {min(ys):.0f}..{max(ys):.0f}')

    html = HTML.read_text()
    new_html, replaced = patch_html(html, coords)
    if not replaced:
        print('No STATIONS entries matched. Aborting.', file=sys.stderr)
        return 1
    HTML.write_text(new_html)
    print(f'Patched {len(replaced)} STATIONS entries in {HTML}')
    missing_in_html = [n for n in coords if n not in replaced]
    if missing_in_html:
        print('Coords present but no HTML entry to patch:')
        for n in missing_in_html: print('  -', n)
    return 0

if __name__ == '__main__':
    sys.exit(main())
