#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["lxml"]
# ///
"""
Parse the Wikimedia Commons CC BY-SA tube map SVG and emit a JSON mapping
station name -> (x, y) in source SVG coordinates.

The SVG file (London_Underground_Overground_DLR_Crossrail_map.svg by Sameboat,
CC BY-SA 4.0) is structured by Wikipedia mappers with semantic groups
(routes / station_nodes / interactivity), but station labels are scattered
as <text>/<tspan> elements that we have to filter heuristically.

Heuristic:
  - Walk every <text> in the document.
  - Concatenate <tspan> children to assemble multi-line names.
  - Reject text whose content matches map-legend / fare-zone / footnote noise.
  - Apply the element's nearest transform stack so coordinates are in the
    root viewBox.
  - Match against the curated Tube-le station list. Take the closest match
    by name (Jaro-style isn't needed; case-insensitive substring is plenty).
"""
from __future__ import annotations
import re, json, math, sys
from pathlib import Path
from lxml import etree

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
N = {"svg": SVG_NS, "xlink": XLINK_NS}
TAG = lambda local: f"{{{SVG_NS}}}{local}"

# Tube-le's 96 station names (must match index.html exactly).
TARGETS = [
    "Stanmore","Edgware","Harrow & Wealdstone","Wembley Park","High Barnet",
    "Cockfosters","Uxbridge","Rayners Lane","Wembley Central","Hampstead",
    "Walthamstow Central","Tottenham Hale","Seven Sisters","Willesden Junction",
    "Queen's Park","Finsbury Park","Highbury & Islington","Camden Town",
    "Finchley Road","Swiss Cottage","St John's Wood","Euston Square",
    "King's Cross St. Pancras","Euston","Angel","Old Street","Baker Street",
    "Farringdon","Warren Street","Paddington","Edgware Road","Notting Hill Gate",
    "Marble Arch","Bond Street","Oxford Circus","Tottenham Court Road","Holborn",
    "Chancery Lane","St. Paul's","Bank","Liverpool Street","Aldgate",
    "Aldgate East","Moorgate","Covent Garden","Leicester Square",
    "Piccadilly Circus","Charing Cross","Embankment","Blackfriars","Monument",
    "Tower Hill","High Street Kensington","Gloucester Road","South Kensington",
    "Sloane Square","Green Park","Victoria","Westminster","Waterloo",
    "London Bridge","Borough","Earl's Court","Barons Court","Hammersmith",
    "Turnham Green","Acton Town","Ealing Common","Ealing Broadway","White City",
    "Shepherd's Bush","Vauxhall","Battersea Power Station","Kennington",
    "Elephant & Castle","Stockwell","Brixton","Morden","Bethnal Green",
    "Mile End","West Ham","Canning Town","North Greenwich","Canary Wharf",
    "Whitechapel","Stratford","Leyton","Leytonstone","Epping","Lewisham",
    "Woolwich","Abbey Wood","Barking",
    "Heathrow Terminals 2 & 3","Heathrow Terminal 4","Heathrow Terminal 5",
]

# Variants the SVG uses vs. our canonical form.
ALIASES = {
    "Heathrow Terminals 2 & 3": [
        "Heathrow Terminals 2 & 3", "Heathrow Terminals 2&3",
        "Heathrow Central Terminals 2 & 3", "Heathrow Central",
        "Heathrow 2 & 3", "Heathrow Terminal 2", "Heathrow Terminal 3",
    ],
    "Heathrow Terminal 4": ["Heathrow T4", "Heathrow Terminal 4"],
    "Heathrow Terminal 5": ["Heathrow T5", "Heathrow Terminal 5"],
    "King's Cross St. Pancras": [
        "King's Cross St. Pancras", "King's Cross St Pancras",
        "King's Cross", "St. Pancras", "St Pancras International",
    ],
    "Shepherd's Bush": ["Shepherd's Bush"],
    "St. Paul's": ["St. Paul's", "St Paul's"],
    "St John's Wood": ["St John's Wood", "St. John's Wood"],
    "Hammersmith": ["Hammersmith"],
    "Edgware Road": ["Edgware Road"],   # there are two stations called this; we
                                        # accept either label.
    "Heathrow Terminals 2 & 3": ["Heathrow Terminals 2 & 3","Heathrow Terminals 2&3"],
}

def aliases_for(name: str) -> list[str]:
    return ALIASES.get(name, [name])

# ---------------------------------------------------------------- transforms

TRANSFORM_RE = re.compile(r'(\w+)\s*\(([^)]*)\)')
def parse_transform(s: str) -> tuple[float,float,float,float,float,float]:
    """Return a 2x3 affine matrix [[a,c,e],[b,d,f]] flattened (a,b,c,d,e,f)."""
    a,b,c,d,e,f = 1.0, 0.0, 0.0, 1.0, 0.0, 0.0
    if not s: return (a,b,c,d,e,f)
    for op, args in TRANSFORM_RE.findall(s):
        nums = [float(x) for x in re.split(r'[ ,]+', args.strip()) if x]
        if op == 'translate':
            tx = nums[0]; ty = nums[1] if len(nums)>1 else 0
            a,b,c,d,e,f = compose((a,b,c,d,e,f), (1,0,0,1,tx,ty))
        elif op == 'scale':
            sx = nums[0]; sy = nums[1] if len(nums)>1 else sx
            a,b,c,d,e,f = compose((a,b,c,d,e,f), (sx,0,0,sy,0,0))
        elif op == 'rotate':
            ang = math.radians(nums[0])
            cs, sn = math.cos(ang), math.sin(ang)
            if len(nums) == 3:
                cx, cy = nums[1], nums[2]
                a,b,c,d,e,f = compose((a,b,c,d,e,f), (1,0,0,1,cx,cy))
                a,b,c,d,e,f = compose((a,b,c,d,e,f), (cs,sn,-sn,cs,0,0))
                a,b,c,d,e,f = compose((a,b,c,d,e,f), (1,0,0,1,-cx,-cy))
            else:
                a,b,c,d,e,f = compose((a,b,c,d,e,f), (cs,sn,-sn,cs,0,0))
        elif op == 'matrix':
            m = nums
            a,b,c,d,e,f = compose((a,b,c,d,e,f), tuple(m))
    return (a,b,c,d,e,f)

def compose(M, N):
    a1,b1,c1,d1,e1,f1 = M
    a2,b2,c2,d2,e2,f2 = N
    return (
        a1*a2 + c1*b2,
        b1*a2 + d1*b2,
        a1*c2 + c1*d2,
        b1*c2 + d1*d2,
        a1*e2 + c1*f2 + e1,
        b1*e2 + d1*f2 + f1,
    )

def apply(M, x, y):
    a,b,c,d,e,f = M
    return (a*x + c*y + e, b*x + d*y + f)

def absolute_transform(element) -> tuple[float,...]:
    """Compose every ancestor's transform plus the element's own transform."""
    chain = []
    el = element
    while el is not None and el.tag != TAG('svg'):
        t = el.get('transform') or ''
        if t: chain.append(t)
        el = el.getparent()
    M = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    # outermost first
    for t in reversed(chain):
        M = compose(M, parse_transform(t))
    return M

# ---------------------------------------------------------------- text walker

def text_content(text_el) -> tuple[str, float, float]:
    """Concatenate the textual content of a <text> element, recursively
    descending into nested <tspan>s (Wikipedia's map nests them for
    multi-word labels) but skipping <title> annotations and their subtrees."""
    x = float(text_el.get('x', 0) or 0)
    y = float(text_el.get('y', 0) or 0)
    parts: list[str] = []
    def walk(node):
        if node.tag == TAG('title'):
            return
        if node is not text_el and node.text:
            parts.append(node.text)
        elif node is text_el and node.text:
            parts.append(node.text)
        for child in node:
            walk(child)
            if child.tail:
                parts.append(child.tail)
    walk(text_el)
    content = ' '.join(p.strip() for p in parts if p and p.strip())
    content = re.sub(r'\s+', ' ', content)
    return content, x, y

def is_legendy(text: str) -> bool:
    if not text: return True
    blacklist = (
        'Zone ', 'zone ', 'Fare ', 'Tube', 'Rail', 'River', 'Bus', 'OUT',
        'Open ', 'Off-peak', '24 ', 'HS1', 'LUL', 'National', 'Step-free',
        'Note:', 'Note ', 'Network ', 'For ', 'Information', 'Stations',
        '£', '£', 'Closed', 'No Sunday',
    )
    if any(text.startswith(b) for b in blacklist):
        return True
    if len(text) > 60: return True
    # Mostly digits / punctuation
    letters = sum(ch.isalpha() for ch in text)
    return letters < 2

def find_canonical(label: str, target_list: list[str]) -> str | None:
    """Two-pass match: exact first (case-insensitive), then longest-alias
    substring fallback. Prevents 'Edgware' from swallowing 'Edgware Road'
    labels because the exact match for 'Edgware Road' wins first."""
    L = label.lower().strip()
    if not L: return None
    # Pass 1: exact equality on any alias
    for canonical in target_list:
        for alias in aliases_for(canonical):
            if alias.lower().strip() == L:
                return canonical
    # Pass 2: pick the longest alias that is a substring of the label
    # (label is an expansion of the alias). Reject if length delta > 14.
    best, best_len = None, 0
    for canonical in target_list:
        for alias in aliases_for(canonical):
            a = alias.lower().strip()
            if a in L and abs(len(a) - len(L)) <= 14 and len(a) > best_len:
                best, best_len = canonical, len(a)
    return best

# ---------------------------------------------------------------- main

def main() -> int:
    svg_path = Path('tube_map.svg')
    if not svg_path.exists():
        print('tube_map.svg not found', file=sys.stderr); return 1
    tree = etree.parse(str(svg_path))
    root = tree.getroot()

    # Map each canonical name to a list of candidate (x, y, label) triples
    found: dict[str, list[tuple[float, float, str]]] = {n: [] for n in TARGETS}

    for text_el in root.iter(TAG('text')):
        label, lx, ly = text_content(text_el)
        if is_legendy(label): continue
        M = absolute_transform(text_el)
        wx, wy = apply(M, lx, ly)
        canonical = find_canonical(label, TARGETS)
        if canonical is not None:
            found[canonical].append((wx, wy, label))

    # Pick a single coordinate per station. If multiple candidates (e.g.
    # "Heathrow Terminal 2" and "Heathrow Terminal 3" both labelled), average.
    out: dict[str, list[float]] = {}
    missing: list[str] = []
    for name, candidates in found.items():
        if not candidates:
            missing.append(name); continue
        ax = sum(c[0] for c in candidates) / len(candidates)
        ay = sum(c[1] for c in candidates) / len(candidates)
        out[name] = [round(ax, 1), round(ay, 1)]

    coords_path = Path('extracted_coords.json')
    coords_path.write_text(json.dumps(out, indent=2, sort_keys=True))
    print(f'Wrote {coords_path}: {len(out)} stations ({len(missing)} missing)')
    if missing:
        print('Missing:')
        for m in missing: print('  -', m)
    # quick sanity
    xs = [v[0] for v in out.values()]; ys = [v[1] for v in out.values()]
    if xs: print(f'X range: {min(xs):.0f} .. {max(xs):.0f}')
    if ys: print(f'Y range: {min(ys):.0f} .. {max(ys):.0f}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
