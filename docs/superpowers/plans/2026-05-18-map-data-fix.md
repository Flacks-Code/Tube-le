# Map Data Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix missing line branches, Thames misalignment, and station-dot offsets by extending the PDF extraction pipeline with ~70 display-only stations and running the three-script pipeline.

**Architecture:** Extend `build_map_from_tfl_pdf.py` with new station targets so the validator accepts previously-rejected branch strokes; add matching STATIONS entries and LINES sequences to `index.html`; filter display-only stations from puzzle selection; run `build → extract_thames → snap` pipeline to produce consistent coordinates.

**Tech Stack:** Python 3.11+ via `uv run --script`, PyMuPDF (`pymupdf`), plain JavaScript (no build step), single `index.html`.

---

## Files

| File | Change |
|------|--------|
| `build_map_from_tfl_pdf.py` | Extend TARGETS + LINE_STATIONS with ~70 new stations |
| `index.html` | Add ~70 STATIONS entries; update LINES sequences; filter display_only in game logic |

The three pipeline scripts (`extract_thames_from_pdf.py`, `snap_stations_to_lines.py`) run unchanged.

---

## Task 1: Extend `build_map_from_tfl_pdf.py` — TARGETS

**Files:**
- Modify: `build_map_from_tfl_pdf.py`

- [ ] **Step 1: Add new stations to TARGETS**

Replace the existing `TARGETS` list (lines 35–57) with the extended version:

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add build_map_from_tfl_pdf.py
git commit -m "extend PDF pipeline TARGETS with ~70 display-only stations"
```

---

## Task 2: Extend `build_map_from_tfl_pdf.py` — LINE_STATIONS

**Files:**
- Modify: `build_map_from_tfl_pdf.py`

Adding new stations to `LINE_STATIONS` is what makes the validator accept the previously-rejected branch strokes. Each station added here becomes a proximity anchor that a stroke can "hit" during validation.

- [ ] **Step 1: Replace `LINE_STATIONS` dict** (lines 109–158) with the extended version:

```python
LINE_STATIONS: dict[str, list[str]] = {
    "Bakerloo": [
        "Harrow & Wealdstone","Wembley Central","Willesden Junction",
        "Queen's Park","Paddington","Baker Street","Oxford Circus",
        "Piccadilly Circus","Charing Cross","Embankment","Waterloo",
        "Elephant & Castle",
    ],
    "Central": [
        # Western branches
        "West Ruislip","Ruislip Gardens","South Ruislip","Northolt","Greenford",
        "Perivale","Hanger Lane","North Acton","East Acton",
        "Ealing Broadway","West Acton","White City","Shepherd's Bush",
        # Main line
        "Notting Hill Gate","Marble Arch","Bond Street","Oxford Circus",
        "Tottenham Court Road","Holborn","Chancery Lane","St. Paul's",
        "Bank","Liverpool Street","Bethnal Green","Mile End",
        # Eastern branches
        "Stratford","Leyton","Leytonstone",
        "Snaresbrook","South Woodford","Woodford",
        "Buckhurst Hill","Loughton","Debden","Theydon Bois","Epping",
        # Hainault loop
        "Wanstead","Redbridge","Gants Hill","Newbury Park",
        "Barkingside","Fairlop","Hainault","Grange Hill","Chigwell","Roding Valley",
    ],
    "Circle": [
        "Hammersmith","Paddington","Edgware Road","Baker Street","Euston Square",
        "King's Cross St. Pancras","Farringdon","Moorgate","Liverpool Street",
        "Aldgate","Tower Hill","Monument","Blackfriars","Embankment","Westminster",
        "Victoria","Sloane Square","South Kensington","Gloucester Road",
        "High Street Kensington","Notting Hill Gate",
    ],
    "District": [
        # Ealing / main
        "Ealing Broadway","Ealing Common","Acton Town","Turnham Green",
        # Richmond branch
        "Gunnersbury","Kew Gardens","Richmond",
        # Wimbledon branch
        "Fulham Broadway","Parsons Green","Putney Bridge","East Putney",
        "Southfields","Wimbledon Park","Wimbledon",
        # Main east
        "Hammersmith","Barons Court","Earl's Court","Gloucester Road",
        "South Kensington","Sloane Square","Victoria","Westminster",
        "Embankment","Blackfriars","Monument","Tower Hill",
        "Aldgate East","Whitechapel","Mile End","West Ham","Barking",
        "High Street Kensington","Notting Hill Gate","Paddington","Edgware Road",
    ],
    "Hammersmith & City": [
        "Hammersmith","Paddington","Edgware Road","Baker Street","Euston Square",
        "King's Cross St. Pancras","Farringdon","Moorgate","Liverpool Street",
        "Aldgate East","Whitechapel","Mile End","West Ham","Barking",
    ],
    "Jubilee": [
        "Stanmore","Wembley Park","Finchley Road","Swiss Cottage","St John's Wood",
        "Baker Street","Bond Street","Green Park","Westminster","Waterloo",
        "London Bridge","Canary Wharf","North Greenwich","Canning Town",
        "West Ham","Stratford",
    ],
    "Metropolitan": [
        "Uxbridge","Rayners Lane","Wembley Park","Finchley Road","Baker Street",
        "Euston Square","King's Cross St. Pancras","Farringdon","Moorgate","Aldgate",
        # NW extension
        "Preston Road","Northwick Park","Harrow-on-the-Hill",
        "North Harrow","Pinner","Northwood Hills","Northwood",
        "Moor Park","Croxley","Watford",
        "Rickmansworth","Chorleywood","Chalfont & Latimer","Amersham","Chesham",
    ],
    "Northern": [
        "Edgware","Hampstead","Camden Town","Euston","Warren Street",
        "Tottenham Court Road","Leicester Square","Charing Cross","Embankment",
        "Waterloo","King's Cross St. Pancras","Angel","Old Street","Moorgate",
        "Bank","London Bridge","Borough","Elephant & Castle","Kennington",
        "Stockwell","Morden","Battersea Power Station","High Barnet",
    ],
    "Piccadilly": [
        "Cockfosters","Finsbury Park","King's Cross St. Pancras","Holborn",
        "Covent Garden","Leicester Square","Piccadilly Circus","Green Park",
        "South Kensington","Gloucester Road","Earl's Court","Barons Court",
        "Hammersmith","Turnham Green","Acton Town","Ealing Common",
        "Rayners Lane","Uxbridge",
        "Heathrow Terminals 2 & 3","Heathrow Terminal 4","Heathrow Terminal 5",
    ],
    "Victoria": [
        "Brixton","Stockwell","Vauxhall","Victoria","Green Park","Oxford Circus",
        "Warren Street","Euston","King's Cross St. Pancras","Highbury & Islington",
        "Finsbury Park","Seven Sisters","Tottenham Hale","Walthamstow Central",
    ],
    "DLR": [
        # All DLR stations
        "Bank","Tower Gateway","Shadwell","Limehouse","Westferry","Poplar",
        "West India Quay","Canary Wharf","Heron Quays","South Quay",
        "Crossharbour","Mudchute","Island Gardens","Cutty Sark","Greenwich",
        "Deptford Bridge","Elverson Road","Lewisham",
        "Stratford","Stratford High Street","Abbey Road","West Ham",
        "Canning Town","Royal Victoria","Custom House","Prince Regent",
        "Royal Albert","Beckton Park","Cyprus","Gallions Reach","Beckton",
        "Pudding Mill Lane","Devons Road","Bow Church","Langdon Park","All Saints",
        "Silvertown","London City Airport","King George V","Woolwich Arsenal",
    ],
    "Elizabeth": [
        "Heathrow Terminal 5","Heathrow Terminals 2 & 3","Heathrow Terminal 4",
        "Paddington","Acton Main Line","Ealing Broadway",
        "West Ealing","Hanwell","Southall","Hayes & Harlington",
        "West Drayton","Iver","Langley","Slough","Burnham","Taplow",
        "Maidenhead","Twyford","Reading",
        "Bond Street","Tottenham Court Road","Farringdon","Liverpool Street",
        "Whitechapel","Canary Wharf","Woolwich","Abbey Wood",
        "Stratford","Maryland","Manor Park","Forest Gate","Ilford","Seven Kings",
        "Goodmayes","Chadwell Heath","Romford","Gidea Park",
        "Harold Wood","Brentwood","Shenfield",
    ],
}
```

- [ ] **Step 2: Add ALIASES for tricky station names**

Add these entries to the existing `ALIASES` dict (after the existing entries):

```python
    "Chalfont & Latimer": ["Chalfont & Latimer", "Chalfont and Latimer"],
    "Harrow-on-the-Hill": ["Harrow-on-the-Hill", "Harrow on the Hill"],
    "Acton Main Line":    ["Acton Main Line"],
    "Woolwich Arsenal":   ["Woolwich Arsenal"],
    "Stratford High Street": ["Stratford High Street"],
    "Heron Quays":        ["Heron Quays"],
    "West India Quay":    ["West India Quay"],
    "Cutty Sark":         ["Cutty Sark", "Cutty Sark for Maritime Greenwich"],
    "King George V":      ["King George V"],
```

- [ ] **Step 3: Commit**

```bash
git add build_map_from_tfl_pdf.py
git commit -m "extend PDF pipeline LINE_STATIONS and ALIASES for branch coverage"
```

---

## Task 3: Add Central and District display-only STATIONS to `index.html`

**Files:**
- Modify: `index.html`

Add these entries inside the `STATIONS = {` block. Place them after the existing entries, before the closing `};`. Coords start as `[0,0]` — the pipeline overwrites them.

- [ ] **Step 1: Add Central West Ruislip branch + Epping intermediates + Hainault loop**

```js
  // Central — West Ruislip branch (display_only)
  "East Acton":        { coords:[0,0], zone:2, lines:["Central"], river:"far", display_only:true },
  "North Acton":       { coords:[0,0], zone:3, lines:["Central"], river:"far", display_only:true },
  "West Acton":        { coords:[0,0], zone:3, lines:["Central"], river:"far", display_only:true },
  "Hanger Lane":       { coords:[0,0], zone:3, lines:["Central"], river:"far", display_only:true },
  "Perivale":          { coords:[0,0], zone:4, lines:["Central"], river:"far", display_only:true },
  "Greenford":         { coords:[0,0], zone:4, lines:["Central"], river:"far", display_only:true },
  "Northolt":          { coords:[0,0], zone:5, lines:["Central"], river:"far", display_only:true },
  "South Ruislip":     { coords:[0,0], zone:5, lines:["Central"], river:"far", display_only:true },
  "Ruislip Gardens":   { coords:[0,0], zone:6, lines:["Central"], river:"far", display_only:true },
  "West Ruislip":      { coords:[0,0], zone:6, lines:["Central"], river:"far", display_only:true },
  // Central — Epping main-line intermediates (display_only)
  "Snaresbrook":       { coords:[0,0], zone:4, lines:["Central"], river:"far", display_only:true },
  "South Woodford":    { coords:[0,0], zone:4, lines:["Central"], river:"far", display_only:true },
  "Woodford":          { coords:[0,0], zone:4, lines:["Central"], river:"far", display_only:true },
  "Buckhurst Hill":    { coords:[0,0], zone:4, lines:["Central"], river:"far", display_only:true },
  "Loughton":          { coords:[0,0], zone:6, lines:["Central"], river:"far", display_only:true },
  "Debden":            { coords:[0,0], zone:6, lines:["Central"], river:"far", display_only:true },
  "Theydon Bois":      { coords:[0,0], zone:6, lines:["Central"], river:"far", display_only:true },
  // Central — Hainault / Fairlop loop (display_only)
  "Wanstead":          { coords:[0,0], zone:4, lines:["Central"], river:"far", display_only:true },
  "Redbridge":         { coords:[0,0], zone:4, lines:["Central"], river:"far", display_only:true },
  "Gants Hill":        { coords:[0,0], zone:4, lines:["Central"], river:"far", display_only:true },
  "Newbury Park":      { coords:[0,0], zone:4, lines:["Central"], river:"far", display_only:true },
  "Barkingside":       { coords:[0,0], zone:4, lines:["Central"], river:"far", display_only:true },
  "Fairlop":           { coords:[0,0], zone:4, lines:["Central"], river:"far", display_only:true },
  "Hainault":          { coords:[0,0], zone:4, lines:["Central"], river:"far", display_only:true },
  "Grange Hill":       { coords:[0,0], zone:4, lines:["Central"], river:"far", display_only:true },
  "Chigwell":          { coords:[0,0], zone:6, lines:["Central"], river:"far", display_only:true },
  "Roding Valley":     { coords:[0,0], zone:4, lines:["Central"], river:"far", display_only:true },
  // District — Richmond branch (display_only)
  "Gunnersbury":       { coords:[0,0], zone:3, lines:["District"], river:"far", display_only:true },
  "Kew Gardens":       { coords:[0,0], zone:3, lines:["District"], river:"far", display_only:true },
  "Richmond":          { coords:[0,0], zone:4, lines:["District"], river:"far", display_only:true },
  // District — Wimbledon branch (display_only)
  "Fulham Broadway":   { coords:[0,0], zone:2, lines:["District"], river:"medium", display_only:true },
  "Parsons Green":     { coords:[0,0], zone:2, lines:["District"], river:"medium", display_only:true },
  "Putney Bridge":     { coords:[0,0], zone:2, lines:["District"], river:"close", display_only:true },
  "East Putney":       { coords:[0,0], zone:3, lines:["District"], river:"far", display_only:true },
  "Southfields":       { coords:[0,0], zone:3, lines:["District"], river:"far", display_only:true },
  "Wimbledon Park":    { coords:[0,0], zone:3, lines:["District"], river:"far", display_only:true },
  "Wimbledon":         { coords:[0,0], zone:3, lines:["District"], river:"far", display_only:true },
```

- [ ] **Step 2: Commit**

```bash
git add index.html
git commit -m "add Central and District display-only stations to STATIONS"
```

---

## Task 4: Add Metropolitan, Elizabeth, and DLR display-only STATIONS to `index.html`

**Files:**
- Modify: `index.html`

Continue adding to the STATIONS block after the entries from Task 3.

- [ ] **Step 1: Add Metropolitan NW branches**

```js
  // Metropolitan — NW branches (display_only)
  "Preston Road":        { coords:[0,0], zone:4, lines:["Metropolitan"], river:"far", display_only:true },
  "Northwick Park":      { coords:[0,0], zone:4, lines:["Metropolitan"], river:"far", display_only:true },
  "Harrow-on-the-Hill":  { coords:[0,0], zone:5, lines:["Metropolitan"], river:"far", display_only:true },
  "North Harrow":        { coords:[0,0], zone:5, lines:["Metropolitan"], river:"far", display_only:true },
  "Pinner":              { coords:[0,0], zone:5, lines:["Metropolitan"], river:"far", display_only:true },
  "Northwood Hills":     { coords:[0,0], zone:6, lines:["Metropolitan"], river:"far", display_only:true },
  "Northwood":           { coords:[0,0], zone:6, lines:["Metropolitan"], river:"far", display_only:true },
  "Moor Park":           { coords:[0,0], zone:6, lines:["Metropolitan"], river:"far", display_only:true },
  "Croxley":             { coords:[0,0], zone:7, lines:["Metropolitan"], river:"far", display_only:true },
  "Watford":             { coords:[0,0], zone:7, lines:["Metropolitan"], river:"far", display_only:true },
  "Rickmansworth":       { coords:[0,0], zone:7, lines:["Metropolitan"], river:"far", display_only:true },
  "Chorleywood":         { coords:[0,0], zone:7, lines:["Metropolitan"], river:"far", display_only:true },
  "Chalfont & Latimer":  { coords:[0,0], zone:7, lines:["Metropolitan"], river:"far", display_only:true },
  "Amersham":            { coords:[0,0], zone:9, lines:["Metropolitan"], river:"far", display_only:true },
  "Chesham":             { coords:[0,0], zone:9, lines:["Metropolitan"], river:"far", display_only:true },
```

- [ ] **Step 2: Add Elizabeth Shenfield and Reading branches**

```js
  // Elizabeth — Shenfield branch (display_only)
  "Maryland":            { coords:[0,0], zone:3, lines:["Elizabeth"], river:"far", display_only:true },
  "Manor Park":          { coords:[0,0], zone:3, lines:["Elizabeth"], river:"far", display_only:true },
  "Forest Gate":         { coords:[0,0], zone:3, lines:["Elizabeth"], river:"far", display_only:true },
  "Ilford":              { coords:[0,0], zone:4, lines:["Elizabeth"], river:"far", display_only:true },
  "Seven Kings":         { coords:[0,0], zone:4, lines:["Elizabeth"], river:"far", display_only:true },
  "Goodmayes":           { coords:[0,0], zone:4, lines:["Elizabeth"], river:"far", display_only:true },
  "Chadwell Heath":      { coords:[0,0], zone:4, lines:["Elizabeth"], river:"far", display_only:true },
  "Romford":             { coords:[0,0], zone:6, lines:["Elizabeth"], river:"far", display_only:true },
  "Gidea Park":          { coords:[0,0], zone:6, lines:["Elizabeth"], river:"far", display_only:true },
  "Harold Wood":         { coords:[0,0], zone:6, lines:["Elizabeth"], river:"far", display_only:true },
  "Brentwood":           { coords:[0,0], zone:7, lines:["Elizabeth"], river:"far", display_only:true },
  "Shenfield":           { coords:[0,0], zone:7, lines:["Elizabeth"], river:"far", display_only:true },
  // Elizabeth — Reading branch (display_only)
  "Acton Main Line":     { coords:[0,0], zone:3, lines:["Elizabeth"], river:"far", display_only:true },
  "West Ealing":         { coords:[0,0], zone:3, lines:["Elizabeth"], river:"far", display_only:true },
  "Hanwell":             { coords:[0,0], zone:4, lines:["Elizabeth"], river:"far", display_only:true },
  "Southall":            { coords:[0,0], zone:4, lines:["Elizabeth"], river:"far", display_only:true },
  "Hayes & Harlington":  { coords:[0,0], zone:5, lines:["Elizabeth"], river:"far", display_only:true },
  "West Drayton":        { coords:[0,0], zone:6, lines:["Elizabeth"], river:"far", display_only:true },
  "Iver":                { coords:[0,0], zone:7, lines:["Elizabeth"], river:"far", display_only:true },
  "Langley":             { coords:[0,0], zone:7, lines:["Elizabeth"], river:"far", display_only:true },
  "Slough":              { coords:[0,0], zone:7, lines:["Elizabeth"], river:"far", display_only:true },
  "Burnham":             { coords:[0,0], zone:7, lines:["Elizabeth"], river:"far", display_only:true },
  "Taplow":              { coords:[0,0], zone:7, lines:["Elizabeth"], river:"far", display_only:true },
  "Maidenhead":          { coords:[0,0], zone:7, lines:["Elizabeth"], river:"far", display_only:true },
  "Twyford":             { coords:[0,0], zone:7, lines:["Elizabeth"], river:"far", display_only:true },
  "Reading":             { coords:[0,0], zone:7, lines:["Elizabeth"], river:"far", display_only:true },
```

- [ ] **Step 3: Add DLR stations**

```js
  // DLR — full network (display_only)
  "Tower Gateway":       { coords:[0,0], zone:1, lines:["DLR"], river:"medium", display_only:true },
  "Shadwell":            { coords:[0,0], zone:2, lines:["DLR"], river:"medium", display_only:true },
  "Limehouse":           { coords:[0,0], zone:2, lines:["DLR"], river:"medium", display_only:true },
  "Westferry":           { coords:[0,0], zone:2, lines:["DLR"], river:"medium", display_only:true },
  "Poplar":              { coords:[0,0], zone:2, lines:["DLR"], river:"medium", display_only:true },
  "West India Quay":     { coords:[0,0], zone:2, lines:["DLR"], river:"close", display_only:true },
  "Heron Quays":         { coords:[0,0], zone:2, lines:["DLR"], river:"close", display_only:true },
  "South Quay":          { coords:[0,0], zone:2, lines:["DLR"], river:"close", display_only:true },
  "Crossharbour":        { coords:[0,0], zone:2, lines:["DLR"], river:"close", display_only:true },
  "Mudchute":            { coords:[0,0], zone:2, lines:["DLR"], river:"close", display_only:true },
  "Island Gardens":      { coords:[0,0], zone:2, lines:["DLR"], river:"close", display_only:true },
  "Cutty Sark":          { coords:[0,0], zone:2, lines:["DLR"], river:"close", display_only:true },
  "Greenwich":           { coords:[0,0], zone:2, lines:["DLR"], river:"close", display_only:true },
  "Deptford Bridge":     { coords:[0,0], zone:2, lines:["DLR"], river:"far", display_only:true },
  "Elverson Road":       { coords:[0,0], zone:2, lines:["DLR"], river:"far", display_only:true },
  "Stratford High Street":{ coords:[0,0], zone:3, lines:["DLR"], river:"far", display_only:true },
  "Abbey Road":          { coords:[0,0], zone:3, lines:["DLR"], river:"far", display_only:true },
  "Royal Victoria":      { coords:[0,0], zone:3, lines:["DLR"], river:"close", display_only:true },
  "Custom House":        { coords:[0,0], zone:3, lines:["DLR"], river:"close", display_only:true },
  "Prince Regent":       { coords:[0,0], zone:3, lines:["DLR"], river:"close", display_only:true },
  "Royal Albert":        { coords:[0,0], zone:3, lines:["DLR"], river:"close", display_only:true },
  "Beckton Park":        { coords:[0,0], zone:3, lines:["DLR"], river:"far", display_only:true },
  "Cyprus":              { coords:[0,0], zone:3, lines:["DLR"], river:"far", display_only:true },
  "Gallions Reach":      { coords:[0,0], zone:3, lines:["DLR"], river:"far", display_only:true },
  "Beckton":             { coords:[0,0], zone:3, lines:["DLR"], river:"far", display_only:true },
  "Pudding Mill Lane":   { coords:[0,0], zone:3, lines:["DLR"], river:"far", display_only:true },
  "Devons Road":         { coords:[0,0], zone:2, lines:["DLR"], river:"far", display_only:true },
  "Bow Church":          { coords:[0,0], zone:2, lines:["DLR"], river:"far", display_only:true },
  "Langdon Park":        { coords:[0,0], zone:2, lines:["DLR"], river:"far", display_only:true },
  "All Saints":          { coords:[0,0], zone:2, lines:["DLR"], river:"far", display_only:true },
  "Silvertown":          { coords:[0,0], zone:3, lines:["DLR"], river:"close", display_only:true },
  "London City Airport": { coords:[0,0], zone:3, lines:["DLR"], river:"close", display_only:true },
  "King George V":       { coords:[0,0], zone:3, lines:["DLR"], river:"close", display_only:true },
  "Woolwich Arsenal":    { coords:[0,0], zone:4, lines:["DLR"], river:"close", display_only:true },
```

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "add Metropolitan, Elizabeth, DLR display-only stations to STATIONS"
```

---

## Task 5: Update LINES sequences — Central and District

**Files:**
- Modify: `index.html`

- [ ] **Step 1: Replace Central LINES entry**

Find the `"Central"` entry in `const LINES` and replace it:

```js
  "Central": {
    color:"#E32017",
    sequences:[
      // Main east-west trunk (west end → east end)
      ["Ealing Broadway","West Acton","North Acton","East Acton","White City",
       "Shepherd's Bush","Notting Hill Gate","Marble Arch","Bond Street",
       "Oxford Circus","Tottenham Court Road","Holborn","Chancery Lane",
       "St. Paul's","Bank","Liverpool Street","Bethnal Green","Mile End",
       "Stratford","Leyton","Leytonstone",
       "Snaresbrook","South Woodford","Woodford",
       "Buckhurst Hill","Loughton","Debden","Theydon Bois","Epping"],
      // West Ruislip branch (from North Acton junction)
      ["North Acton","Hanger Lane","Perivale","Greenford","Northolt",
       "South Ruislip","Ruislip Gardens","West Ruislip"],
      // Hainault loop — clockwise from Woodford
      ["Woodford","Roding Valley","Chigwell","Grange Hill","Hainault",
       "Fairlop","Barkingside","Newbury Park","Gants Hill",
       "Redbridge","Wanstead","Leytonstone"]
    ]
  },
```

- [ ] **Step 2: Replace District LINES entry**

Find the `"District"` entry in `const LINES` and replace it:

```js
  "District": {
    color:"#00782A",
    sequences:[
      // Main east-west trunk
      ["Ealing Broadway","Ealing Common","Acton Town","Turnham Green",
       "Hammersmith","Barons Court","Earl's Court","Gloucester Road",
       "South Kensington","Sloane Square","Victoria","Westminster",
       "Embankment","Blackfriars","Monument","Tower Hill",
       "Aldgate East","Whitechapel","Mile End","West Ham","Barking"],
      // Earl's Court shuttle / inner loop
      ["Earl's Court","High Street Kensington","Notting Hill Gate",
       "Paddington","Edgware Road"],
      // Richmond branch
      ["Turnham Green","Gunnersbury","Kew Gardens","Richmond"],
      // Wimbledon branch
      ["Earl's Court","Fulham Broadway","Parsons Green","Putney Bridge",
       "East Putney","Southfields","Wimbledon Park","Wimbledon"]
    ]
  },
```

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "update Central and District LINES sequences with missing branches"
```

---

## Task 6: Update LINES sequences — Metropolitan, Elizabeth, DLR

**Files:**
- Modify: `index.html`

- [ ] **Step 1: Replace Metropolitan LINES entry**

```js
  "Metropolitan": {
    color:"#9B0056",
    sequences:[
      // Main trunk: Uxbridge → Aldgate
      // Preston Road and Northwick Park sit between Wembley Park and Harrow-on-the-Hill
      ["Uxbridge","Rayners Lane","Harrow-on-the-Hill","Northwick Park","Preston Road",
       "Wembley Park","Finchley Road","Baker Street","Euston Square",
       "King's Cross St. Pancras","Farringdon","Moorgate","Aldgate"],
      // Harrow-on-the-Hill northward to Moor Park junction
      ["Harrow-on-the-Hill","North Harrow","Pinner","Northwood Hills",
       "Northwood","Moor Park"],
      // Watford branch (from Moor Park)
      ["Moor Park","Croxley","Watford"],
      // Amersham branch (from Moor Park)
      ["Moor Park","Rickmansworth","Chorleywood","Chalfont & Latimer","Amersham"],
      // Chesham spur
      ["Chalfont & Latimer","Chesham"]
    ]
  },
```

> **Note:** The TfL Met line topology between Harrow-on-the-Hill, Wembley Park, and Rayners Lane is complex (Met and Jubilee share track; the Uxbridge branch splits). Verify the Harrow-on-the-Hill ↔ Wembley Park adjacency against the rendered map after running the pipeline — adjust if the exit stub angles look wrong at Wembley Park or Harrow-on-the-Hill.

- [ ] **Step 2: Replace Elizabeth LINES entry**

```js
  "Elizabeth": {
    color:"#6950A1",
    sequences:[
      // Main trunk: Reading → Abbey Wood
      ["Reading","Twyford","Maidenhead","Taplow","Burnham","Slough","Langley",
       "Iver","West Drayton","Hayes & Harlington","Southall","Hanwell",
       "West Ealing","Ealing Broadway","Acton Main Line","Paddington",
       "Bond Street","Tottenham Court Road","Farringdon","Liverpool Street",
       "Whitechapel","Canary Wharf","Woolwich","Abbey Wood"],
      // Heathrow T4 spur
      ["Heathrow Terminals 2 & 3","Heathrow Terminal 4"],
      // Heathrow T5 spur
      ["Heathrow Terminal 5","Heathrow Terminals 2 & 3"],
      // Shenfield branch (from Liverpool Street via Stratford)
      ["Liverpool Street","Stratford","Maryland","Manor Park","Forest Gate",
       "Ilford","Seven Kings","Goodmayes","Chadwell Heath","Romford",
       "Gidea Park","Harold Wood","Brentwood","Shenfield"]
    ]
  },
```

- [ ] **Step 3: Replace DLR LINES entry**

```js
  "DLR": {
    color:"#00A4A7",
    sequences:[
      // Bank → Lewisham (main trunk via Isle of Dogs)
      ["Bank","Shadwell","Limehouse","Westferry","Poplar","West India Quay",
       "Canary Wharf","Heron Quays","South Quay","Crossharbour","Mudchute",
       "Island Gardens","Cutty Sark","Greenwich","Deptford Bridge",
       "Elverson Road","Lewisham"],
      // Tower Gateway spur (branches from Shadwell)
      ["Tower Gateway","Shadwell"],
      // Stratford → West Ham (via Stratford High Street)
      ["Stratford","Stratford High Street","Abbey Road","West Ham"],
      // Stratford → Poplar (via Pudding Mill Lane / Bow Church)
      ["Stratford","Pudding Mill Lane","Devons Road","Bow Church",
       "Langdon Park","All Saints","Poplar"],
      // Canning Town → Beckton
      ["Canning Town","Royal Victoria","Custom House","Prince Regent",
       "Royal Albert","Beckton Park","Cyprus","Gallions Reach","Beckton"],
      // Canning Town → Woolwich Arsenal
      ["Canning Town","Silvertown","London City Airport","King George V",
       "Woolwich Arsenal"]
    ]
  },
```

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "update Metropolitan, Elizabeth, DLR LINES sequences with missing branches"
```

---

## Task 7: Update game logic to exclude display-only stations

**Files:**
- Modify: `index.html` (two one-line changes)

- [ ] **Step 1: Filter STATION_NAMES**

Find this line (around line 1107):
```js
const STATION_NAMES = Object.keys(STATIONS);
```

Replace with:
```js
const STATION_NAMES = Object.keys(STATIONS).filter(n => !STATIONS[n].display_only);
```

- [ ] **Step 2: Confirm autocomplete already uses `STATION_NAMES`**

`renderAC` at line 1201 already reads:
```js
const scored = STATION_NAMES
  .map(n => ({ n, s: scoreMatch(q, n) }))
```
No change needed — filtering `STATION_NAMES` in Step 1 automatically fixes autocomplete.

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "filter display_only stations from puzzle selection and autocomplete"
```

---

## Task 8: Run the pipeline

**Files:** (pipeline scripts run in-place, patching `index.html`)

All three scripts must be run from the repo root (`/home/kieran/source/Tube-le`).

- [ ] **Step 1: Run `build_map_from_tfl_pdf.py`**

```bash
uv run --no-project --script build_map_from_tfl_pdf.py
```

Expected output (approximate — numbers will vary):
```
Diagram bounds (from stations): X ...
Strokes accepted: NNN, skipped (colour off-target): NNN, skipped (station validation): NNN
tfl_lines.json: NNN path strings across 12 lines
tfl_stations.json: NNN stations
Patched NNN STATIONS entries.
```

Check for any `?: StationName` lines — these indicate stations in TARGETS that weren't found in the PDF. Common causes: slightly wrong canonical name (add an ALIAS), or the label is in a different font size range. For each missed station, either add an alias or accept that coords stay `[0,0]` (the snap script will handle it via endpoint fallback).

- [ ] **Step 2: Verify DLR and branch coverage in `tfl_lines.json`**

```bash
uv run --no-project python3 -c "
import json
d = json.load(open('tfl_lines.json'))
for line, paths in d.items():
    print(f'{line}: {len(paths)} paths')
"
```

Expected: DLR should now have 6+ paths (was 1), Elizabeth 4+ (was 2). If DLR still shows 1, the station validation is still filtering out branch strokes — check which new DLR stations weren't found (step 1 output) and add aliases.

- [ ] **Step 3: Run `extract_thames_from_pdf.py`**

```bash
uv run --no-project --script extract_thames_from_pdf.py
```

Expected output:
```
Picked Thames body, area=NNNNN, colour=(199, 234, 251)
Rewrote THAMES_PATH (NNNN chars)
```

If "No Thames candidate found": the colour band (lines 122–125) may need widening. The TFL PDF Thames fill is approximately `#C7EAFB` — if the script fails, widen the RGB bounds to `160 <= rgb[0] <= 220` and `220 <= rgb[1] <= 248` and `240 <= rgb[2] <= 255`.

- [ ] **Step 4: Run `snap_stations_to_lines.py`**

```bash
uv run --no-project --script snap_stations_to_lines.py
```

Expected output:
```
Pass 1 (tight, ≤85): NNN stations snapped
Pass 2 (endpoint, ≤220): NN stations snapped
Still unsnapped: ...
```

Any "Still unsnapped" entries for new stations indicate their line paths weren't extracted (DLR branch missing, etc.) — they keep `[0,0]` coords and won't render visually, but don't break the game.

- [ ] **Step 5: Commit pipeline output**

```bash
git add index.html tfl_lines.json tfl_stations.json
git commit -m "run PDF pipeline: updated coords, line paths, and Thames"
```

---

## Task 9: Verify in browser

**Files:** `index.html` (read-only verification)

Open `index.html` directly in Chrome (file:// URL — no server needed).

- [ ] **Step 1: Check full map (post-win state)**

Trigger the full map by opening the browser console and running:
```js
state.status = 'won'; renderMap();
```
Or play a game to completion. Confirm you can see:
- District line extends to Richmond (northwest of Turnham Green) and Wimbledon (south of Earl's Court)
- Central line extends northwest to West Ruislip and has the Hainault loop visible east of Leytonstone
- Metropolitan line extends northwest past Wembley Park to Amersham, Chesham, and Watford
- Elizabeth line extends west to Reading and east to Shenfield
- DLR shows a proper network across East London, Isle of Dogs, and into Greenwich/Lewisham

- [ ] **Step 2: Check Thames alignment**

In the full map view, the Thames stripe should pass beneath Westminster, Waterloo, London Bridge, Tower Hill, and curve around the Isle of Dogs. If it's visually offset from those stations, `extract_thames_from_pdf.py` may have picked a different filled path. Re-run the script with debug output: add `print(f'Candidate: area={c[0]:.0f}, colour={c[2]}')` before `candidates.sort(...)` to see all candidates, then adjust the colour bounds to pick the right one.

- [ ] **Step 3: Check station dots on lines**

Zoom in on a few stations in the full map. Dots should sit visibly on the coloured line strokes, not beside them.

- [ ] **Step 4: Check display-only stations excluded from autocomplete**

Type "Wimbledon" in the guess input. The autocomplete should show no results (Wimbledon is display-only). Type "Waterloo" — should appear normally.

- [ ] **Step 5: Check puzzle exits at branch junctions**

Use the console to force a specific puzzle target:
```js
state.target = "Turnham Green"; state.guesses = []; state.status = "playing"; renderMap();
```
The puzzle view should show District line stubs going in at least three directions: east (toward Hammersmith), west-northwest (toward Acton Town/Ealing), and northwest (toward Richmond). Earl's Court should similarly show a southern stub (toward Wimbledon branch).

- [ ] **Step 6: Final commit (if any fixes were needed)**

```bash
git add index.html
git commit -m "fix: post-pipeline visual corrections"
```
