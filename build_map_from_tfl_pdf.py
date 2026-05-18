#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pymupdf"]
# ///
"""
Unified pipeline. From the TFL standard tube map PDF:

  1. Extract every stroked path, grouped by the TFL line whose colour matches.
  2. Extract station label positions by walking <text> spans.
  3. Compute a uniform-scale transform from PDF page coordinates into the
     game's 1400×900 viewBox, with a 40-unit margin.
  4. Patch index.html:
       - STATIONS[*].coords  ← rescaled PDF label centres
       - inject a TFL_LINE_PATHS const containing one SVG `d` per line, in
         game coordinates, so the renderer can draw the actual diagram
         rather than naive Euclidean segments.

The line geometry is what gives us the iconic 45° angles and corners. The
station positions land where TFL's own typesetter placed the labels, which
is right next to each station marker on the diagram.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
import pymupdf

PDF = Path('tube_map_tfl.pdf')
HTML = Path('index.html')

MAP_W, MAP_H = 1400, 900
MARGIN = 40

# Canonical Tube-le station list (must match index.html).
TARGETS = [
    # --- existing playable stations (unchanged) ---
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
    # --- Central: West Ruislip branch ---
    "West Acton","North Acton","East Acton",
    "Hanger Lane","Perivale","Greenford","Northolt",
    "South Ruislip","Ruislip Gardens","West Ruislip",
    # --- Central: Epping main line (intermediate) ---
    "Snaresbrook","South Woodford","Woodford",
    "Buckhurst Hill","Loughton","Debden","Theydon Bois",
    # --- Central: Hainault/Fairlop loop ---
    "Wanstead","Redbridge","Gants Hill","Newbury Park",
    "Barkingside","Fairlop","Hainault","Grange Hill","Chigwell","Roding Valley",
    # --- District: Richmond branch ---
    "Gunnersbury","Kew Gardens","Richmond",
    # --- District: Wimbledon branch ---
    "Fulham Broadway","Parsons Green","Putney Bridge","East Putney",
    "Southfields","Wimbledon Park","Wimbledon",
    # --- Metropolitan: NW branches ---
    "Preston Road","Northwick Park","Harrow-on-the-Hill",
    "North Harrow","Pinner","Northwood Hills","Northwood",
    "Moor Park","Croxley","Watford",
    "Rickmansworth","Chorleywood","Chalfont & Latimer","Amersham","Chesham",
    # --- Elizabeth: Shenfield branch ---
    "Maryland","Manor Park","Forest Gate","Ilford","Seven Kings","Goodmayes",
    "Chadwell Heath","Romford","Gidea Park","Harold Wood","Brentwood","Shenfield",
    # --- Elizabeth: Reading branch ---
    "Acton Main Line","West Ealing","Hanwell","Southall","Hayes & Harlington",
    "West Drayton","Iver","Langley","Slough","Burnham","Taplow",
    "Maidenhead","Twyford","Reading",
    # --- DLR ---
    "Tower Gateway","Shadwell","Limehouse","Westferry","Poplar",
    "West India Quay","Heron Quays","South Quay","Crossharbour","Mudchute",
    "Island Gardens","Cutty Sark","Greenwich","Deptford Bridge","Elverson Road",
    "Stratford High Street","Abbey Road",
    "Royal Victoria","Custom House","Prince Regent","Royal Albert",
    "Beckton Park","Cyprus","Gallions Reach","Beckton",
    "Pudding Mill Lane","Devons Road","Bow Church","Langdon Park","All Saints",
    "Silvertown","London City Airport","King George V","Woolwich Arsenal",
]

# Aliases the PDF typesetter uses. Where multiple aliases exist we'll take
# whichever spatial cluster matches first; for the Heathrows we accept the
# legacy 'Heathrow Central' too.
ALIASES = {
    "King's Cross St. Pancras": [
        "King's Cross St. Pancras", "King's Cross St Pancras",
        "King's Cross & St Pancras Int'l", "King's Cross & St Pancras",
        "King's Cross", "St Pancras International", "St Pancras",
    ],
    "Heathrow Terminals 2 & 3": [
        "Heathrow Terminals 2 & 3", "Heathrow Terminals 2&3",
        "Heathrow Central Terminals 2 & 3", "Heathrow Central",
    ],
    "Heathrow Terminal 4": ["Heathrow Terminal 4", "Heathrow T4"],
    "Heathrow Terminal 5": ["Heathrow Terminal 5", "Heathrow T5"],
    "St. Paul's": ["St. Paul's", "St Paul's"],
    "St John's Wood": ["St John's Wood", "St. John's Wood"],
    "Shepherd's Bush": ["Shepherd's Bush"],
    "Edgware Road": ["Edgware Road"],
    "Battersea Power Station": ["Battersea Power Station", "Battersea Power"],
    "Highbury & Islington": ["Highbury & Islington", "Highbury &"],
}
def aliases_for(name: str) -> list[str]:
    return ALIASES.get(name, [name])

# Canonical TFL brand colours per line. We use RGB-distance matching plus
# station-proximity validation rather than exact hex equality, because the
# PDF's CMYK→RGB conversion produces slightly off shades AND because some
# of the new TfL Overground line colours (Mildmay blue, Windrush red,
# Weaver pink, Suffragette green, Liberty grey, Lioness yellow) sit very
# close to canonical Underground colours and would otherwise be conflated.
TARGET_LINE_COLOURS = {
    "Bakerloo":           (179, 99, 5),
    "Central":            (227, 32, 23),
    "Circle":             (255, 211, 0),
    "District":           (0, 120, 42),
    "Hammersmith & City": (243, 169, 187),
    "Jubilee":            (160, 165, 169),
    "Metropolitan":       (155, 0, 86),
    "Northern":           (35, 31, 32),     # PDF uses #231F20 not pure black
    "Piccadilly":         (0, 54, 136),
    "Victoria":           (0, 152, 212),
    "DLR":                (0, 164, 167),
    "Elizabeth":          (105, 80, 161),
}

# Canonical station sequences per line (mirroring index.html's LINES).
# Used to validate that a stroke really belongs to the line whose colour
# it sits closest to — a stroke close in colour but passing through none
# of the line's stations is Overground/Thameslink contamination.
LINE_STATIONS: dict[str, list[str]] = {
    "Bakerloo":           ["Harrow & Wealdstone","Wembley Central","Willesden Junction",
                           "Queen's Park","Paddington","Baker Street","Oxford Circus",
                           "Piccadilly Circus","Charing Cross","Embankment","Waterloo",
                           "Elephant & Castle"],
    "Central":            ["Ealing Broadway","White City","Shepherd's Bush","Notting Hill Gate",
                           "Marble Arch","Bond Street","Oxford Circus","Tottenham Court Road",
                           "Holborn","Chancery Lane","St. Paul's","Bank","Liverpool Street",
                           "Bethnal Green","Mile End","Stratford","Leyton","Leytonstone","Epping"],
    "Circle":             ["Hammersmith","Paddington","Edgware Road","Baker Street","Euston Square",
                           "King's Cross St. Pancras","Farringdon","Moorgate","Liverpool Street",
                           "Aldgate","Tower Hill","Monument","Blackfriars","Embankment","Westminster",
                           "Victoria","Sloane Square","South Kensington","Gloucester Road",
                           "High Street Kensington","Notting Hill Gate"],
    "District":           ["Ealing Broadway","Ealing Common","Acton Town","Turnham Green",
                           "Hammersmith","Barons Court","Earl's Court","Gloucester Road",
                           "South Kensington","Sloane Square","Victoria","Westminster",
                           "Embankment","Blackfriars","Monument","Tower Hill","Aldgate East",
                           "Whitechapel","Mile End","West Ham","Barking",
                           "High Street Kensington","Notting Hill Gate","Paddington","Edgware Road"],
    "Hammersmith & City": ["Hammersmith","Paddington","Edgware Road","Baker Street","Euston Square",
                           "King's Cross St. Pancras","Farringdon","Moorgate","Liverpool Street",
                           "Aldgate East","Whitechapel","Mile End","West Ham","Barking"],
    "Jubilee":            ["Stanmore","Wembley Park","Finchley Road","Swiss Cottage","St John's Wood",
                           "Baker Street","Bond Street","Green Park","Westminster","Waterloo",
                           "London Bridge","Canary Wharf","North Greenwich","Canning Town",
                           "West Ham","Stratford"],
    "Metropolitan":       ["Uxbridge","Rayners Lane","Wembley Park","Finchley Road","Baker Street",
                           "Euston Square","King's Cross St. Pancras","Farringdon","Moorgate",
                           "Aldgate"],
    "Northern":           ["Edgware","Hampstead","Camden Town","Euston","Warren Street",
                           "Tottenham Court Road","Leicester Square","Charing Cross","Embankment",
                           "Waterloo","King's Cross St. Pancras","Angel","Old Street","Moorgate",
                           "Bank","London Bridge","Borough","Elephant & Castle","Kennington",
                           "Stockwell","Morden","Battersea Power Station","High Barnet"],
    "Piccadilly":         ["Cockfosters","Finsbury Park","King's Cross St. Pancras","Holborn",
                           "Covent Garden","Leicester Square","Piccadilly Circus","Green Park",
                           "South Kensington","Gloucester Road","Earl's Court","Barons Court",
                           "Hammersmith","Turnham Green","Acton Town","Ealing Common",
                           "Rayners Lane","Uxbridge","Heathrow Terminals 2 & 3",
                           "Heathrow Terminal 4","Heathrow Terminal 5"],
    "Victoria":           ["Brixton","Stockwell","Vauxhall","Victoria","Green Park","Oxford Circus",
                           "Warren Street","Euston","King's Cross St. Pancras","Highbury & Islington",
                           "Finsbury Park","Seven Sisters","Tottenham Hale","Walthamstow Central"],
    "DLR":                ["Bank","Canary Wharf","Lewisham","Stratford","Canning Town","West Ham"],
    "Elizabeth":          ["Heathrow Terminal 5","Heathrow Terminals 2 & 3","Paddington",
                           "Bond Street","Tottenham Court Road","Farringdon","Liverpool Street",
                           "Whitechapel","Canary Wharf","Woolwich","Abbey Wood",
                           "Heathrow Terminal 4","Stratford","Ealing Broadway"],
}

# Colour-distance threshold: candidate line is considered if its canonical
# colour sits within this RGB distance. Loose enough to allow Mildmay-blue
# strokes to be CONSIDERED Victoria candidates (so they can be rejected by
# station validation), tight enough to avoid mixing District green into
# something completely unrelated.
COLOUR_DIST_MAX = 80
# Station proximity radius (in PDF coords).
STATION_NEAR_RADIUS = 25
# Strokes pass validation if (a) they hit at least STATION_HITS_MIN of
# the candidate line's canonical stations, AND (b) the candidate-line
# hit count exceeds the highest hit count for any OTHER target line.
# Together these reject Thameslink (which shares 2 stations with H&C
# but covers more Circle/District stations than H&C).
STATION_HITS_MIN = 2

# ----------------------------------------------------- line path extraction --

def fmt(v: float) -> str:
    s = f"{v:.2f}".rstrip('0').rstrip('.')
    return s if s else '0'

def items_to_d(items, tx, ty, scale) -> str:
    """Convert pymupdf items to an SVG `d` string, applying scale+translate
    so we land in game coordinates. Relative transformation: every point is
    (x - tx)*scale, (y - ty)*scale."""
    parts: list[str] = []
    cur = None
    def tr(p):
        return ((p[0] - tx) * scale, (p[1] - ty) * scale)
    for it in items:
        kind = it[0]
        if kind == 'l':
            (x1, y1), (x2, y2) = it[1], it[2]
            a = tr((x1, y1)); b = tr((x2, y2))
            if cur != a:
                parts.append(f"M{fmt(a[0])},{fmt(a[1])}")
            parts.append(f"L{fmt(b[0])},{fmt(b[1])}")
            cur = b
        elif kind == 'c':
            p0, p1, p2, p3 = it[1], it[2], it[3], it[4]
            a = tr((p0.x, p0.y)); b = tr((p1.x, p1.y))
            c = tr((p2.x, p2.y)); d = tr((p3.x, p3.y))
            if cur != a:
                parts.append(f"M{fmt(a[0])},{fmt(a[1])}")
            parts.append(f"C{fmt(b[0])},{fmt(b[1])} {fmt(c[0])},{fmt(c[1])} {fmt(d[0])},{fmt(d[1])}")
            cur = d
        elif kind == 'qu':
            p0, p1, p2 = it[1], it[2], it[3]
            a = tr((p0.x, p0.y)); m = tr((p1.x, p1.y)); b = tr((p2.x, p2.y))
            if cur != a:
                parts.append(f"M{fmt(a[0])},{fmt(a[1])}")
            c1 = (a[0] + (2/3)*(m[0]-a[0]), a[1] + (2/3)*(m[1]-a[1]))
            c2 = (b[0] + (2/3)*(m[0]-b[0]), b[1] + (2/3)*(m[1]-b[1]))
            parts.append(f"C{fmt(c1[0])},{fmt(c1[1])} {fmt(c2[0])},{fmt(c2[1])} {fmt(b[0])},{fmt(b[1])}")
            cur = b
    return ' '.join(parts)

def line_path_bounds(drawings) -> tuple[float, float, float, float]:
    """Return (min_x, min_y, max_x, max_y) over every stroked path whose
    colour sits within COLOUR_DIST_MAX of some target line colour. Used to
    compute the rescale transform so the diagram fits the game viewBox."""
    xs: list[float] = []
    ys: list[float] = []
    for d in drawings:
        sc = d.get('color')
        if not sc or d.get('type') not in ('s', 'sf'):
            continue
        rgb = tuple(round(c*255) for c in sc)
        # Only consider strokes whose colour matches one of our target lines.
        if closest_target_line(rgb)[1] > COLOUR_DIST_MAX:
            continue
        for it in d.get('items', []):
            if it[0] == 'l':
                for pt in (it[1], it[2]):
                    xs.append(pt[0]); ys.append(pt[1])
            elif it[0] == 'c':
                for p in (it[1], it[2], it[3], it[4]):
                    xs.append(p.x); ys.append(p.y)
            elif it[0] == 'qu':
                for p in it[1:]:
                    if hasattr(p, 'x'):
                        xs.append(p.x); ys.append(p.y)
    if not xs:
        raise SystemExit('No coloured strokes found')
    return min(xs), min(ys), max(xs), max(ys)

def closest_target_line(rgb: tuple[int, int, int]) -> tuple[str, float]:
    """Return (line_name, RGB-distance) for the canonical line colour
    closest to `rgb`."""
    import math
    best, best_d = None, 1e9
    for name, target in TARGET_LINE_COLOURS.items():
        d = math.sqrt(sum((a-b)**2 for a, b in zip(rgb, target)))
        if d < best_d:
            best_d = d; best = name
    return best, best_d

def collect_stroke_points(items) -> list[tuple[float, float]]:
    """Sample points along a pymupdf items list. Coarse enough to be fast
    but dense enough that any path passing within STATION_NEAR_RADIUS of
    a station label position will have a sample point near that label."""
    pts: list[tuple[float, float]] = []
    step = 6.0  # PDF units between samples
    def sample_seg(a, b):
        import math
        dx, dy = b[0]-a[0], b[1]-a[1]
        L = math.hypot(dx, dy)
        n = max(1, int(L / step))
        for i in range(n+1):
            t = i/n
            pts.append((a[0]+dx*t, a[1]+dy*t))
    def sample_cubic(p0, p1, p2, p3):
        n = 12
        for i in range(n+1):
            t = i/n; u = 1-t
            x = u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0]
            y = u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1]
            pts.append((x, y))
    for it in items:
        if it[0] == 'l':
            sample_seg(it[1], it[2])
        elif it[0] == 'c':
            p0, p1, p2, p3 = it[1], it[2], it[3], it[4]
            sample_cubic((p0.x,p0.y),(p1.x,p1.y),(p2.x,p2.y),(p3.x,p3.y))
        elif it[0] == 'qu' and len(it) >= 4:
            p0, p1, p2 = it[1], it[2], it[3]
            c1 = (p0.x + (2/3)*(p1.x-p0.x), p0.y + (2/3)*(p1.y-p0.y))
            c2 = (p2.x + (2/3)*(p1.x-p2.x), p2.y + (2/3)*(p1.y-p2.y))
            sample_cubic((p0.x,p0.y), c1, c2, (p2.x,p2.y))
    return pts

# ----------------------------------------------------- station extraction --

def normalise(s: str) -> str:
    s = s.replace("’", "'").replace(" ", " ")
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def match_station(label: str) -> str | None:
    L = normalise(label).lower()
    if not L:
        return None
    for canonical in TARGETS:
        for alias in aliases_for(canonical):
            if normalise(alias).lower() == L:
                return canonical
    best, best_len = None, 0
    for canonical in TARGETS:
        for alias in aliases_for(canonical):
            a = normalise(alias).lower()
            if a in L and abs(len(a) - len(L)) <= 14 and len(a) > best_len:
                best, best_len = canonical, len(a)
    return best

def extract_station_positions(page) -> dict[str, tuple[float, float]]:
    """Spatial line-by-line word matcher.

    pymupdf's block grouping is unreliable — it crams unrelated stations
    into one block when their labels happen to be near each other on the
    page (e.g. Stamford Brook + Ravenscourt Park + Turnham Green all share
    one block).  Instead:

      1. Collect every span at the station-label point size (≈ 4.2pt).
      2. Treat each span as one "word" with a centre position.
      3. For each canonical station name, search greedily for a chain of
         spans whose joined text equals the name and whose positions form
         a tight cluster (vertical or horizontal stack with small gaps).
    """
    td = page.get_text("dict")

    spans: list[tuple[str, float, float, float]] = []  # (text, cx, cy, size)
    for block in td.get('blocks', []):
        if block.get('type') != 0:
            continue
        for ln in block.get('lines', []):
            for sp in ln.get('spans', []):
                txt = normalise(sp.get('text', ''))
                size = sp.get('size', 0)
                if not txt:
                    continue
                # Station labels in the PDF are ~4.2pt; allow a small window
                if not (3.5 <= size <= 5.5):
                    continue
                bb = sp['bbox']
                cx = (bb[0] + bb[2]) / 2
                cy = (bb[1] + bb[3]) / 2
                spans.append((txt, cx, cy, size))

    def squash(s: str) -> str:
        """Lowercase + strip punctuation except & — what we compare on."""
        return re.sub(r'[^\w&]+', ' ', s.lower()).strip()

    def chain_bbox_max(idxs: list[int]) -> float:
        """Largest dimension (width or height) of the bounding box of the
        chain's spans. A small value means the chain corresponds to a real
        label, not a mash-up of unrelated nearby station words."""
        xs = [spans[i][1] for i in idxs]
        ys = [spans[i][2] for i in idxs]
        return max(max(xs) - min(xs), max(ys) - min(ys))

    def find_chain(alias: str, used: set[int]) -> list[int] | None:
        """Find every chain of spans whose joined text equals the alias
        (after punctuation squash) and whose adjacent spans are close.
        Return the chain with the smallest bounding box — that's the one
        whose words sit on top of each other like a real station label,
        not stretched across two unrelated nearby labels."""
        target = squash(alias)
        if not target:
            return None
        candidates: list[list[int]] = []
        for i, (t, cx, cy, _) in enumerate(spans):
            if i in used:
                continue
            head = squash(t)
            if not head:
                continue
            if head == target:
                candidates.append([i])
                continue
            if not target.startswith(head + ' '):
                continue
            # Try every greedy extension from here. Track multiple branches
            # by depth-first search up to a reasonable depth.
            stack: list[tuple[list[int], str, float, float]] = [([i], head, cx, cy)]
            while stack:
                chain, consumed, pcx, pcy = stack.pop()
                if consumed == target:
                    candidates.append(chain)
                    continue
                want = target[len(consumed) + 1:]
                for j, (t2, x2, y2, _) in enumerate(spans):
                    if j in used or j in chain:
                        continue
                    ext = squash(t2)
                    if not ext:
                        continue
                    if ext != want and not want.startswith(ext + ' '):
                        continue
                    if abs(x2 - pcx) > 60 or abs(y2 - pcy) > 25:
                        continue
                    stack.append((chain + [j], consumed + ' ' + ext, x2, y2))
        if not candidates:
            return None
        candidates.sort(key=chain_bbox_max)
        return candidates[0]

    out: dict[str, tuple[float, float]] = {}
    used: set[int] = set()

    # Iterate stations by descending alias-word-count so multi-word names
    # claim their spans first ("King's Cross St. Pancras" before "King's
    # Cross" — though we don't have both in TARGETS, this helps with e.g.
    # "Heathrow Terminal 4" claiming its tokens before "Heathrow" alone).
    def alias_word_count(name: str) -> int:
        return max(len(a.split()) for a in aliases_for(name))

    for name in sorted(TARGETS, key=alias_word_count, reverse=True):
        found = False
        for alias in aliases_for(name):
            chain = find_chain(alias, used)
            if chain:
                xs = [spans[i][1] for i in chain]
                ys = [spans[i][2] for i in chain]
                out[name] = (sum(xs)/len(xs), sum(ys)/len(ys))
                used.update(chain)
                found = True
                break
        if not found:
            print(f'  ?: {name}')
    return out

# ----------------------------------------------------- main --

def compute_transform(min_x, min_y, max_x, max_y) -> tuple[float, float, float]:
    src_w = max_x - min_x
    src_h = max_y - min_y
    avail_w = MAP_W - 2*MARGIN
    avail_h = MAP_H - 2*MARGIN
    scale = min(avail_w / src_w, avail_h / src_h)
    new_w = src_w * scale
    new_h = src_h * scale
    off_x = MARGIN + (avail_w - new_w) / 2
    off_y = MARGIN + (avail_h - new_h) / 2
    return scale, min_x, min_y, off_x, off_y  # type: ignore[return-value]

def main() -> int:
    doc = pymupdf.open(str(PDF))
    page = doc[0]
    drawings = page.get_drawings()

    # Extract stations first — their positions bound the diagram area
    # (excluding the legend/key boxes on the right of the page).
    raw_stations = extract_station_positions(page)
    if not raw_stations:
        raise SystemExit('No stations extracted')
    sxs = [p[0] for p in raw_stations.values()]
    sys_ = [p[1] for p in raw_stations.values()]
    pad = 25
    mn_x = min(sxs) - pad; mx_x = max(sxs) + pad
    mn_y = min(sys_) - pad; mx_y = max(sys_) + pad
    print(f'Diagram bounds (from stations): '
          f'X {mn_x:.1f}..{mx_x:.1f}, Y {mn_y:.1f}..{mx_y:.1f}')

    src_w, src_h = mx_x - mn_x, mx_y - mn_y
    avail_w, avail_h = MAP_W - 2*MARGIN, MAP_H - 2*MARGIN
    scale = min(avail_w / src_w, avail_h / src_h)
    off_x = MARGIN + (avail_w - src_w*scale) / 2
    off_y = MARGIN + (avail_h - src_h*scale) / 2

    def to_game(x, y):
        return ((x - mn_x) * scale + off_x, (y - mn_y) * scale + off_y)

    # ----- stations: just rescale into game space (already extracted above) -----
    new_coords: dict[str, list[float]] = {}
    for name, (sx, sy) in raw_stations.items():
        gx, gy = to_game(sx, sy)
        new_coords[name] = [round(gx, 1), round(gy, 1)]

    # ----- lines, with station-proximity validation -----
    # A stroke survives if (a) its colour is closest to one of the 12
    # target underground/DLR/Elizabeth line colours, and (b) the stroke
    # passes within STATION_NEAR_RADIUS PDF units of at least
    # STATION_HITS_MIN canonical stations on that line. This filters out
    # Mildmay/Windrush/Weaver/Suffragette/Liberty/Lioness Overground and
    # Thameslink strokes, which sit close to underground colours but pass
    # through different stations.
    tx = mn_x - off_x / scale
    ty = mn_y - off_y / scale

    by_line: dict[str, list[str]] = {name: [] for name in TARGET_LINE_COLOURS}
    skipped_colour = 0
    skipped_validation = 0
    for d in drawings:
        sc = d.get('color')
        if not sc or d.get('type') not in ('s', 'sf'):
            continue
        items = d.get('items', [])
        if not items:
            continue
        # Filter out hairlines (fare-zone outlines, grid, ruled background
        # markings). Real tube lines are ≥ ~2pt wide in this PDF.
        width = d.get('width') or 0
        if width < 1.5:
            continue
        rgb = tuple(round(c*255) for c in sc)
        candidate, colour_dist = closest_target_line(rgb)
        if colour_dist > COLOUR_DIST_MAX:
            skipped_colour += 1
            continue
        # Sample the path and, for every target line, count how many of
        # its canonical stations sit near any sample point. We then keep
        # the stroke only if (a) it hits at least STATION_HITS_MIN of the
        # CANDIDATE line's stations, and (b) the candidate's hit count is
        # the unambiguous winner — any other line tying or exceeding it
        # means the stroke really belongs to that other line.
        samples = collect_stroke_points(items)
        if not samples:
            continue
        hits_by_line: dict[str, int] = {}
        for ln_name, stns in LINE_STATIONS.items():
            h = 0
            for stn in stns:
                sx_sy = raw_stations.get(stn)
                if sx_sy is None: continue
                sx, sy = sx_sy
                for px, py in samples:
                    if (px - sx) ** 2 + (py - sy) ** 2 <= STATION_NEAR_RADIUS ** 2:
                        h += 1
                        break
            hits_by_line[ln_name] = h
        cand_hits = hits_by_line.get(candidate, 0)
        if cand_hits < STATION_HITS_MIN:
            skipped_validation += 1
            continue
        # Pick the line with the most hits as the true owner of this stroke.
        # If the candidate (closest colour) isn't the winner, fall back to
        # whichever line is — provided its colour is also within range.
        sorted_lines = sorted(hits_by_line.items(), key=lambda kv: -kv[1])
        winner_line, winner_hits = sorted_lines[0]
        if winner_hits < STATION_HITS_MIN:
            skipped_validation += 1
            continue
        # Confirm the winner's canonical colour is close enough; otherwise
        # this stroke colour doesn't match any plausible target line.
        winner_target = TARGET_LINE_COLOURS[winner_line]
        import math as _m
        winner_dist = _m.sqrt(sum((a-b)**2 for a,b in zip(rgb, winner_target)))
        if winner_dist > COLOUR_DIST_MAX:
            skipped_validation += 1
            continue
        # Disambiguate ties between two equally-hit lines by preferring
        # the closer colour. (Rare, but happens for shared track segments
        # like Paddington–Edgware Road on both Circle and District.)
        ties = [name for name, h in sorted_lines if h == winner_hits]
        if len(ties) > 1:
            winner_line = min(ties, key=lambda n: _m.sqrt(
                sum((a-b)**2 for a,b in zip(rgb, TARGET_LINE_COLOURS[n]))
            ))
        candidate = winner_line
        d_attr = items_to_d(items, tx, ty, scale)
        if d_attr:
            by_line[candidate].append(d_attr)

    print(f'Strokes accepted: {sum(len(v) for v in by_line.values())}, '
          f'skipped (colour off-target): {skipped_colour}, '
          f'skipped (station validation): {skipped_validation}')

    # ----- write JSON for inspection -----
    Path('tfl_lines.json').write_text(json.dumps(by_line, indent=2))
    Path('tfl_stations.json').write_text(json.dumps(new_coords, indent=2, sort_keys=True))
    print(f'tfl_lines.json: {sum(len(v) for v in by_line.values())} path strings across {len(by_line)} lines')
    print(f'tfl_stations.json: {len(new_coords)} stations')

    # ----- patch index.html -----
    html = HTML.read_text()

    # 1) STATIONS coord patch (one entry per line)
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
    print(f'Patched {len(patched)} STATIONS entries.')
    missing_html = [n for n in new_coords if n not in patched]
    if missing_html:
        print('  Coords without an index.html entry:', missing_html)

    # 2) Inject (or replace) TFL_LINE_PATHS const right after ALL_EDGES block.
    line_paths_js = 'const TFL_LINE_PATHS = ' + json.dumps(by_line, indent=2) + ';\n'
    if 'const TFL_LINE_PATHS' in html2:
        html2 = re.sub(
            r'const TFL_LINE_PATHS = \{[\s\S]*?\};\n',
            line_paths_js,
            html2,
            count=1,
        )
    else:
        # Insert after the ALL_EDGES IIFE.
        marker = "})();\n"  # End of ALL_EDGES IIFE — first occurrence will do
        # find the marker after "ALL_EDGES" keyword
        idx_e = html2.find('const ALL_EDGES')
        if idx_e == -1:
            print('Could not find ALL_EDGES insertion point', file=sys.stderr)
            return 1
        end_iife = html2.find(marker, idx_e)
        if end_iife == -1:
            print('Could not find IIFE close for ALL_EDGES', file=sys.stderr)
            return 1
        insert_at = end_iife + len(marker)
        html2 = html2[:insert_at] + '\n' + line_paths_js + html2[insert_at:]
        print('Inserted TFL_LINE_PATHS after ALL_EDGES block.')

    HTML.write_text(html2)
    return 0

if __name__ == '__main__':
    sys.exit(main())
