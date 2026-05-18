#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["lxml"]
# ///
"""
Pull the Thames stripe path out of the Wikimedia tube map SVG and rescale
it using the same source-envelope transform we apply to station coords, so
the river lines up with the rescaled stations. Replaces the THAMES_PATH
string literal in index.html.

Supports the absolute/relative command pairs that appear in the source
path: M m L l H h V v Q q T t C c S s A a Z z.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
from lxml import etree

HTML = Path('index.html')
COORDS = Path('extracted_coords.json')
SVG_PATH = Path('tube_map.svg')

MAP_W, MAP_H = 1400, 900
MARGIN = 30

def compute_transform() -> tuple[float, float, float, float, float]:
    """Return (scale, off_x, off_y, src_min_x, src_min_y) matching apply_coords.py."""
    coords = json.loads(COORDS.read_text())
    xs = [c[0] for c in coords.values()]
    ys = [c[1] for c in coords.values()]
    src_w = max(xs) - min(xs)
    src_h = max(ys) - min(ys)
    scale = min((MAP_W - 2*MARGIN) / src_w, (MAP_H - 2*MARGIN) / src_h)
    new_w = src_w * scale
    new_h = src_h * scale
    off_x = MARGIN + (MAP_W - 2*MARGIN - new_w) / 2
    off_y = MARGIN + (MAP_H - 2*MARGIN - new_h) / 2
    return scale, off_x, off_y, min(xs), min(ys)

TOKEN_RE = re.compile(r'([MmLlHhVvCcSsQqTtAaZz])|(-?\d*\.?\d+(?:[eE][-+]?\d+)?)')

def tokenize(d: str) -> list[str]:
    return [tok[0] or tok[1] for tok in TOKEN_RE.findall(d)]

# How many numbers each command consumes per coordinate group.
ARITY = {
    'M':2, 'L':2, 'T':2,
    'H':1, 'V':1,
    'Q':4, 'S':4,
    'C':6,
    'A':7,
    'Z':0,
}

def fmt(v: float) -> str:
    s = f'{v:.2f}'
    s = s.rstrip('0').rstrip('.')
    return s if s else '0'

def rescale_path(d: str, scale: float, off_x: float, off_y: float,
                 src_min_x: float, src_min_y: float) -> str:
    tokens = tokenize(d)
    out: list[str] = []
    i = 0
    current_cmd = None
    while i < len(tokens):
        t = tokens[i]
        if t.isalpha():
            current_cmd = t
            absolute = t.isupper()
            arity = ARITY[t.upper()]
            out.append(t)
            i += 1
            if arity == 0:
                continue
        else:
            # Implicit repeat: same command as before. M's repeat is L; m's is l.
            if current_cmd is None:
                raise ValueError('numbers before command')
            if current_cmd == 'M': current_cmd = 'L'
            elif current_cmd == 'm': current_cmd = 'l'
            absolute = current_cmd.isupper()
            arity = ARITY[current_cmd.upper()]
        # Pull `arity` numbers off the stream
        nums = [float(tokens[i + k]) for k in range(arity)]
        i += arity
        cmd_upper = current_cmd.upper()
        transformed = transform_args(cmd_upper, absolute, nums,
                                     scale, off_x, off_y,
                                     src_min_x, src_min_y)
        out.append(' '.join(fmt(v) for v in transformed))
    return ' '.join(out)

def transform_args(cmd: str, absolute: bool, nums: list[float],
                   scale: float, off_x: float, off_y: float,
                   src_min_x: float, src_min_y: float) -> list[float]:
    """Apply uniform-scale-plus-translate (for absolute) or scale-only (for
    relative) to the command's argument list. Arc command has shape params
    (rx, ry, x-axis-rotation, large-arc, sweep, x, y) — only the radii and
    the endpoint are dimensional."""
    if cmd in ('M', 'L', 'T'):
        x, y = nums
        if absolute:
            return [(x - src_min_x) * scale + off_x,
                    (y - src_min_y) * scale + off_y]
        return [x * scale, y * scale]
    if cmd == 'H':
        x = nums[0]
        return [(x - src_min_x) * scale + off_x] if absolute else [x * scale]
    if cmd == 'V':
        y = nums[0]
        return [(y - src_min_y) * scale + off_y] if absolute else [y * scale]
    if cmd == 'Q':
        x1, y1, x, y = nums
        if absolute:
            return [(x1 - src_min_x)*scale + off_x,
                    (y1 - src_min_y)*scale + off_y,
                    (x  - src_min_x)*scale + off_x,
                    (y  - src_min_y)*scale + off_y]
        return [x1*scale, y1*scale, x*scale, y*scale]
    if cmd == 'S':
        x2, y2, x, y = nums
        if absolute:
            return [(x2 - src_min_x)*scale + off_x,
                    (y2 - src_min_y)*scale + off_y,
                    (x  - src_min_x)*scale + off_x,
                    (y  - src_min_y)*scale + off_y]
        return [x2*scale, y2*scale, x*scale, y*scale]
    if cmd == 'C':
        x1, y1, x2, y2, x, y = nums
        if absolute:
            return [(x1 - src_min_x)*scale + off_x,
                    (y1 - src_min_y)*scale + off_y,
                    (x2 - src_min_x)*scale + off_x,
                    (y2 - src_min_y)*scale + off_y,
                    (x  - src_min_x)*scale + off_x,
                    (y  - src_min_y)*scale + off_y]
        return [x1*scale, y1*scale, x2*scale, y2*scale, x*scale, y*scale]
    if cmd == 'A':
        rx, ry, rot, large, sweep, x, y = nums
        # Radii are dimensional and scale. Flags and rotation pass through.
        if absolute:
            return [rx*scale, ry*scale, rot, large, sweep,
                    (x - src_min_x)*scale + off_x,
                    (y - src_min_y)*scale + off_y]
        return [rx*scale, ry*scale, rot, large, sweep, x*scale, y*scale]
    raise ValueError(f'Unhandled cmd {cmd}')

def find_thames_d() -> str:
    tree = etree.parse(str(SVG_PATH))
    root = tree.getroot()
    thames = root.find('.//*[@id="Thames_stripe"]')
    if thames is None:
        raise SystemExit('Thames_stripe group not found')
    SVG_NS = '{http://www.w3.org/2000/svg}'
    for child in thames:
        if child.tag != SVG_NS + 'path': continue
        style = child.get('style', '')
        if 'stroke-width' not in style: continue
        return child.get('d', '').strip()
    raise SystemExit('No stroked path inside Thames_stripe')

def main() -> int:
    scale, off_x, off_y, mn_x, mn_y = compute_transform()
    raw = find_thames_d()
    new_d = rescale_path(raw, scale, off_x, off_y, mn_x, mn_y)

    html = HTML.read_text()
    # Replace whatever string literal currently sits in THAMES_PATH = "...";
    # We accept either a single string or a "+ "..." concatenation.
    pattern = re.compile(r'const THAMES_PATH\s*=\s*(?:"[^"]*"\s*\+?\s*)+;', re.S)
    if not pattern.search(html):
        print('THAMES_PATH literal not found in expected form', file=sys.stderr)
        return 1
    replacement = f'const THAMES_PATH =\n  "{new_d}";'
    html2 = pattern.sub(replacement, html, count=1)
    HTML.write_text(html2)
    print(f'Rewrote THAMES_PATH ({len(new_d)} chars).')
    return 0

if __name__ == '__main__':
    sys.exit(main())
