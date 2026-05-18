#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""
Pull station markers off their label positions and onto the actual line
geometry. For each station, look at the line paths it belongs to (from
TFL_LINE_PATHS), sample those paths densely, and pick the sampled point
closest to the station's current (label-derived) position.

Reads TFL_LINE_PATHS and STATIONS out of index.html, rewrites STATIONS
coords in place. The lines stay where they are; only the dots move.

If a snap would move a station more than 60 units, we treat it as a
mismatch (the wrong line was in the station's `lines:` list, the station
is at a quirky position the source map doesn't visit linearly, etc.) and
leave that station alone.
"""
from __future__ import annotations
import re, json, math
from pathlib import Path

HTML = Path('index.html')

MAX_SNAP_TIGHT = 85.0   # primary cutoff — clean snap to nearest line point
MAX_SNAP_LOOSE = 220.0  # fallback for terminus stations whose label sits
                        # well below/beside the line terminus
MIN_PAIR_DISTANCE = 10.0  # if two snapped stations end up closer than this,
                          # push them apart along the line direction

def extract_tfl_line_paths(html: str) -> dict[str, list[str]]:
    m = re.search(r'const TFL_LINE_PATHS = (\{[\s\S]*?\});', html)
    if not m:
        raise SystemExit('TFL_LINE_PATHS not found in index.html')
    return json.loads(m.group(1))

def extract_stations(html: str) -> dict[str, dict]:
    """Parse each STATIONS entry. We need `coords` and `lines` so we know
    which paths to snap each station to."""
    out: dict[str, dict] = {}
    # Match entries like:  "Name": { coords:[x,y], zone:N, lines:["a","b"], ... }
    entry_re = re.compile(
        r'"([^"\\]+)":\s*\{\s*coords:\s*\[\s*(-?\d+(?:\.\d+)?)\s*,'
        r'\s*(-?\d+(?:\.\d+)?)\s*\][^}]*?lines:\s*\[([^\]]*)\]',
        re.S,
    )
    for m in entry_re.finditer(html):
        name = m.group(1)
        x = float(m.group(2)); y = float(m.group(3))
        lines = [s.strip().strip('"') for s in m.group(4).split(',')]
        lines = [l for l in lines if l]
        out[name] = { 'coords':(x, y), 'lines': lines }
    return out

# -------------------- SVG path sampling --------------------

NUM_RE = re.compile(r'-?\d*\.?\d+(?:[eE][-+]?\d+)?')
def numbers(s: str) -> list[float]:
    return [float(x) for x in NUM_RE.findall(s)]

def sample_path(d: str, step: float = 4.0) -> list[tuple[float, float]]:
    """Return points sampled along the path at roughly `step` world units
    apart. Only handles M / L / C (and their lowercase variants); that's
    everything `items_to_d` from build_map_from_tfl_pdf.py emits."""
    pts: list[tuple[float, float]] = []
    cur = (0.0, 0.0)
    start = (0.0, 0.0)
    i = 0
    cmd_re = re.compile(r'([MmLlCcZz])')
    tokens = cmd_re.split(d)
    # tokens is alternating ('', cmd, numsstr, cmd, numsstr, ...)
    cmd = None
    pending: list[float] = []
    def flush():
        nonlocal cur, start, pts
        if cmd is None: return
        c = cmd
        nums = pending[:]
        absolute = c.isupper()
        cu = c.upper()
        idx = 0
        while idx < len(nums):
            if cu == 'M':
                x, y = nums[idx], nums[idx+1]; idx += 2
                if not absolute:
                    x += cur[0]; y += cur[1]
                cur = (x, y); start = (x, y)
                pts.append(cur)
                # Implicit subsequent pairs become L
                while idx + 1 < len(nums):
                    nx, ny = nums[idx], nums[idx+1]; idx += 2
                    if not absolute:
                        nx += cur[0]; ny += cur[1]
                    pts.extend(sample_line(cur, (nx, ny), step))
                    cur = (nx, ny)
            elif cu == 'L':
                while idx + 1 < len(nums):
                    nx, ny = nums[idx], nums[idx+1]; idx += 2
                    if not absolute:
                        nx += cur[0]; ny += cur[1]
                    pts.extend(sample_line(cur, (nx, ny), step))
                    cur = (nx, ny)
            elif cu == 'C':
                while idx + 5 < len(nums):
                    x1, y1, x2, y2, x, y = nums[idx:idx+6]; idx += 6
                    if not absolute:
                        x1 += cur[0]; y1 += cur[1]
                        x2 += cur[0]; y2 += cur[1]
                        x  += cur[0]; y  += cur[1]
                    pts.extend(sample_cubic(cur, (x1,y1), (x2,y2), (x,y), step))
                    cur = (x, y)
            elif cu == 'Z':
                if cur != start:
                    pts.extend(sample_line(cur, start, step))
                    cur = start
                break
            else:
                idx = len(nums)
    for tok in tokens:
        if not tok: continue
        if tok in 'MmLlCcZz':
            flush()
            cmd = tok
            pending = []
        else:
            pending = numbers(tok)
    flush()
    return pts

def sample_line(a, b, step):
    dx, dy = b[0]-a[0], b[1]-a[1]
    L = math.hypot(dx, dy)
    n = max(1, int(L / step))
    return [(a[0] + dx*(i+1)/n, a[1] + dy*(i+1)/n) for i in range(n)]

def sample_cubic(p0, p1, p2, p3, step):
    # Rough length: chord + control polygon midpoint
    chord = math.hypot(p3[0]-p0[0], p3[1]-p0[1])
    poly = (math.hypot(p1[0]-p0[0], p1[1]-p0[1]) +
            math.hypot(p2[0]-p1[0], p2[1]-p1[1]) +
            math.hypot(p3[0]-p2[0], p3[1]-p2[1]))
    L = (chord + poly) / 2
    n = max(4, int(L / step))
    out = []
    for k in range(1, n+1):
        t = k / n
        u = 1 - t
        x = u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0]
        y = u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1]
        out.append((x, y))
    return out

# -------------------- snap --------------------

def path_endpoints(d: str) -> list[tuple[float, float]]:
    """Just the actual termini of each subpath (first M and the last
    point of the path). These mark places where a line physically ends —
    which is exactly where terminus stations should sit."""
    points = sample_path(d, step=1.0)
    if not points:
        return []
    return [points[0], points[-1]]

def main() -> int:
    html = HTML.read_text()
    paths_by_line = extract_tfl_line_paths(html)
    stations = extract_stations(html)
    if not stations:
        raise SystemExit('No STATIONS parsed from index.html')

    # Pre-sample each line's paths once; collect path endpoints separately.
    samples_by_line: dict[str, list[tuple[float, float]]] = {}
    endpoints_by_line: dict[str, list[tuple[float, float]]] = {}
    for ln, paths in paths_by_line.items():
        pts: list[tuple[float, float]] = []
        ends: list[tuple[float, float]] = []
        for d in paths:
            pts.extend(sample_path(d, step=3.0))
            ends.extend(path_endpoints(d))
        samples_by_line[ln] = pts
        endpoints_by_line[ln] = ends

    new_coords: dict[str, tuple[float, float]] = {}
    pass1_snapped: list[str] = []
    pass2_snapped: list[str] = []
    still_unsnapped: list[tuple[str, float]] = []

    # ----- Pass 1: tight snap -----
    pending: list[str] = []
    for name, info in stations.items():
        sx, sy = info['coords']
        best = None
        best_d2 = float('inf')
        for ln in info['lines']:
            for px, py in samples_by_line.get(ln, []):
                d2 = (px - sx) ** 2 + (py - sy) ** 2
                if d2 < best_d2:
                    best_d2 = d2
                    best = (px, py)
        if best is None:
            still_unsnapped.append((name, -1)); continue
        if math.sqrt(best_d2) > MAX_SNAP_TIGHT:
            pending.append(name); continue
        new_coords[name] = (round(best[0], 1), round(best[1], 1))
        pass1_snapped.append(name)

    print(f'Pass 1 (tight, ≤{MAX_SNAP_TIGHT:.0f}): {len(pass1_snapped)} stations snapped')

    # ----- Pass 2: snap remaining to nearest endpoint of their lines -----
    # Terminus stations cluster at line ends, which is correct — multiple
    # stations sharing an endpoint is fine for the visual.
    for name in pending:
        info = stations[name]
        sx, sy = info['coords']
        best = None
        best_d2 = float('inf')
        for ln in info['lines']:
            for px, py in endpoints_by_line.get(ln, []):
                d2 = (px - sx) ** 2 + (py - sy) ** 2
                if d2 < best_d2:
                    best_d2 = d2
                    best = (px, py)
        if best is None or math.sqrt(best_d2) > MAX_SNAP_LOOSE:
            still_unsnapped.append((name, math.sqrt(best_d2) if best else -1))
            continue
        new_coords[name] = (round(best[0], 1), round(best[1], 1))
        pass2_snapped.append(name)

    print(f'Pass 2 (endpoint, ≤{MAX_SNAP_LOOSE:.0f}): {len(pass2_snapped)} stations '
          f'snapped to line termini: {pass2_snapped}')
    if still_unsnapped:
        print('Still off-line — original label kept:')
        for name, d in still_unsnapped:
            print(f'  - {name}: nearest endpoint {d:.1f} away')

    # Now patch index.html.
    entry_re = re.compile(
        r'("([^"\\]+)":\s*{\s*coords:)\s*\[\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*\]'
    )
    patched: list[str] = []
    def _repl(m):
        head, name = m.group(1), m.group(2)
        if name in new_coords:
            x, y = new_coords[name]
            patched.append(name)
            return f"{head}[{x},{y}]"
        return m.group(0)
    html2, _ = entry_re.subn(_repl, html)
    HTML.write_text(html2)
    print(f'Patched {len(patched)} STATIONS entries in {HTML}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
