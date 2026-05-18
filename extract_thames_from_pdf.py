#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pymupdf"]
# ///
"""
Extract the Thames stripe path from the TFL PDF and patch THAMES_PATH in
index.html. The river in the PDF is filled with #E5F4F8 (very pale blue)
and stroked with the same colour. We find the longest such filled path
(it's a single closed polygon making up the river outline) and re-emit it
as an SVG path in game coordinates.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
import pymupdf

PDF = Path('tube_map_tfl.pdf')
HTML = Path('index.html')
MAP_W, MAP_H = 1400, 900
MARGIN = 40

PDF_HEX_TO_LINE = {
    "#B06010": "Bakerloo", "#DF2626": "Central", "#FFCF01": "Circle",
    "#007940": "District", "#D385A9": "Hammersmith & City",
    "#7B858C": "Jubilee", "#871B55": "Metropolitan", "#231F20": "Northern",
    "#2A338D": "Piccadilly", "#0087C7": "Victoria", "#00AFAA": "DLR",
    "#704C9E": "Elizabeth",
}

def fmt(v: float) -> str:
    s = f"{v:.2f}".rstrip('0').rstrip('.')
    return s if s else '0'

def items_to_d(items, tx, ty, scale) -> str:
    parts: list[str] = []
    cur = None
    def tr(p):
        return ((p[0] - tx) * scale, (p[1] - ty) * scale)
    for it in items:
        kind = it[0]
        if kind == 'l':
            (x1,y1),(x2,y2) = it[1], it[2]
            a, b = tr((x1,y1)), tr((x2,y2))
            if cur != a:
                parts.append(f"M{fmt(a[0])},{fmt(a[1])}")
            parts.append(f"L{fmt(b[0])},{fmt(b[1])}")
            cur = b
        elif kind == 'c':
            p0,p1,p2,p3 = it[1],it[2],it[3],it[4]
            a,b,c,d = tr((p0.x,p0.y)),tr((p1.x,p1.y)),tr((p2.x,p2.y)),tr((p3.x,p3.y))
            if cur != a:
                parts.append(f"M{fmt(a[0])},{fmt(a[1])}")
            parts.append(f"C{fmt(b[0])},{fmt(b[1])} {fmt(c[0])},{fmt(c[1])} {fmt(d[0])},{fmt(d[1])}")
            cur = d
        elif kind == 'qu':
            p0,p1,p2 = it[1],it[2],it[3]
            a,m,b = tr((p0.x,p0.y)),tr((p1.x,p1.y)),tr((p2.x,p2.y))
            if cur != a:
                parts.append(f"M{fmt(a[0])},{fmt(a[1])}")
            c1 = (a[0] + (2/3)*(m[0]-a[0]), a[1] + (2/3)*(m[1]-a[1]))
            c2 = (b[0] + (2/3)*(m[0]-b[0]), b[1] + (2/3)*(m[1]-b[1]))
            parts.append(f"C{fmt(c1[0])},{fmt(c1[1])} {fmt(c2[0])},{fmt(c2[1])} {fmt(b[0])},{fmt(b[1])}")
            cur = b
        elif kind == 're':
            # Skip rectangles
            pass
    return ' '.join(parts)

def line_path_bounds(_drawings):
    """Use the same station-based bounds as build_map_from_tfl_pdf.py so
    the Thames lines up with the rest of the geometry. Read them out of
    tfl_stations.json (which build_map writes during its first stage),
    plus the inverse of the rescale to recover PDF-space bounds."""
    import json as _json
    stations = _json.loads(Path('tfl_stations.json').read_text())
    # tfl_stations.json is in GAME coords. We need PDF-space bounds to
    # build the same transform. Recover them by undoing the build_map
    # rescale: read raw_stations directly from the PDF instead.
    import pymupdf as _pm
    page = _pm.open(str(PDF))[0]
    # Replicate build_map's station extraction for PDF coords. Rather
    # than duplicate the whole extractor here, we use a simpler bound:
    # walk every <text> span at typical station-label size and take its
    # position as a proxy.
    td = page.get_text("dict")
    xs, ys = [], []
    for block in td.get('blocks', []):
        if block.get('type') != 0: continue
        for ln in block.get('lines', []):
            for sp in ln.get('spans', []):
                size = sp.get('size', 0)
                if 3.5 <= size <= 5.5 and sp.get('text','').strip():
                    bb = sp['bbox']
                    xs.append((bb[0] + bb[2]) / 2)
                    ys.append((bb[1] + bb[3]) / 2)
    if not xs: raise SystemExit('Failed to derive bounds from labels')
    pad = 25
    return min(xs)-pad, min(ys)-pad, max(xs)+pad, max(ys)+pad

def main() -> int:
    doc = pymupdf.open(str(PDF))
    page = doc[0]
    drawings = page.get_drawings()
    mn_x, mn_y, mx_x, mx_y = line_path_bounds(drawings)
    src_w, src_h = mx_x - mn_x, mx_y - mn_y
    avail_w, avail_h = MAP_W - 2*MARGIN, MAP_H - 2*MARGIN
    scale = min(avail_w / src_w, avail_h / src_h)
    off_x = MARGIN + (avail_w - src_w*scale) / 2
    off_y = MARGIN + (avail_h - src_h*scale) / 2
    tx = mn_x - off_x / scale
    ty = mn_y - off_y / scale

    # Find filled drawings with the pale-cyan colour TFL uses for the
    # Thames body (#C7EAFB on the standard map; we accept a small band).
    candidates = []
    for d in drawings:
        if d.get('type') not in ('f', 'fs'): continue
        fc = d.get('fill')
        if not fc: continue
        rgb = tuple(round(c*255) for c in fc)
        if not (180 <= rgb[0] <= 215 and
                225 <= rgb[1] <= 245 and
                240 <= rgb[2] <= 255):
            continue
        items = d.get('items', [])
        if not items: continue
        # Compute bounding-box width — river is wide; small fills are
        # station symbols or other unrelated shapes.
        xs, ys = [], []
        for it in items:
            if it[0] == 'l':
                xs.extend([it[1][0], it[2][0]]); ys.extend([it[1][1], it[2][1]])
            elif it[0] == 'c':
                for p in (it[1], it[2], it[3], it[4]):
                    xs.append(p.x); ys.append(p.y)
            elif it[0] == 'qu':
                for p in (it[1], it[2], it[3]):
                    xs.append(p.x); ys.append(p.y)
            elif it[0] == 're':
                r = it[1]
                xs.extend([r.x0, r.x1]); ys.extend([r.y0, r.y1])
        if not xs: continue
        w = max(xs) - min(xs); h = max(ys) - min(ys)
        if w < 300: continue  # river spans most of the map width
        candidates.append((w*h, items, rgb))
    if not candidates:
        print('No Thames candidate found', file=sys.stderr); return 1
    candidates.sort(key=lambda x: -x[0])
    items = candidates[0][1]
    print(f'Picked Thames body, area={candidates[0][0]:.0f}, colour={candidates[0][2]}')
    d_attr = items_to_d(items, tx, ty, scale)

    html = HTML.read_text()
    pattern = re.compile(r'const THAMES_PATH\s*=\s*(?:"[^"]*"\s*\+?\s*)+;', re.S)
    if not pattern.search(html):
        print('THAMES_PATH literal not found', file=sys.stderr); return 1
    html2 = pattern.sub(f'const THAMES_PATH =\n  "{d_attr}";', html, count=1)
    HTML.write_text(html2)
    print(f'Rewrote THAMES_PATH ({len(d_attr)} chars)')
    return 0

if __name__ == '__main__':
    sys.exit(main())
