# Tube-le — Design Spec

**Date:** 2026-05-16
**Deliverable:** Single self-contained `index.html` file the user can open directly in a browser.
**Concept:** Wordle-style daily guessing game for London Underground stations, dressed in TFL Tube map aesthetics.

## Goals

- Visually unmistakable as a "TFL thing" — Johnston-alike type, paper cream background, official line colours, the roundel.
- Puzzle drawing reads as a fragment of the real map: lines exit a station at canonical 45° angles, in correct TFL colours, parallel lines stack like the printed diagram.
- Progressive reveal that genuinely guides the player without ever showing text labels until the last hint.
- Polished feedback per guess (Transit Tickets, stops-away, compass), winning celebration with a shareable emoji grid.
- All logic and assets in one HTML file. No build step.

## Non-goals

- Real-time TFL data, server persistence, accounts, multiplayer.
- Exhaustive station coverage including non-interchange stops and all Overground branches (scope: ~95 Underground/Elizabeth/DLR interchange stations).
- Geographic accuracy beyond what the stylized Beck-style diagram needs.

## Architecture

Single HTML file with three top-level concerns:

1. **`<style>` block** — design tokens, layout, components, animations.
2. **DOM skeleton** — split layout (`<aside class="panel">` left, `<section class="map">` right) plus a hidden `<dialog>`-style win modal.
3. **`<script>` IIFE** — data, graph helpers, renderer, input handlers, audio, game state.

No external JS or CSS frameworks. Two Google Fonts are loaded via `<link>` (`Hammersmith One` for display, `Public Sans` for body).

## Data Layer

### Stations

```
STATIONS = {
  "Oxford Circus": {
    coords: [600, 460],            // stylized TFL-grid pixels in a 1400×900 space
    zone: 1,
    lines: ["Bakerloo", "Central", "Victoria"],
    river: "medium"                // "close" | "medium" | "far"
  },
  ...
}
```

~95 entries. Names use canonical TFL forms ("King's Cross St. Pancras", "St. James's Park", "Shepherd's Bush"). Coordinates roughly preserve geographic position so the same map subgraph can be re-cropped at different zoom levels.

### Lines

```
LINES = {
  "Bakerloo":   { color: "#B36305", sequence: [ ... ] },
  "Central":    { color: "#E32017", sequence: [ ... ] },
  "Circle":     { color: "#FFD300", sequence: [ ... ], loop: true },
  "Northern":   { color: "#000000", sequences: [ branchA, branchB ] },
  ...
}
```

Adjacency is derived from `sequence` (or `sequences` for branched lines), not stored on the station. The Circle line is marked `loop:true` so wrap-around adjacency is computed correctly.

Official TFL line colours:

| Line | Hex |
|---|---|
| Bakerloo | `#B36305` |
| Central | `#E32017` |
| Circle | `#FFD300` |
| District | `#00782A` |
| Hammersmith & City | `#F3A9BB` |
| Jubilee | `#A0A5A9` |
| Metropolitan | `#9B0056` |
| Northern | `#000000` |
| Piccadilly | `#003688` |
| Victoria | `#0098D4` |
| Waterloo & City | `#95CDBA` |
| DLR | `#00A4A7` |
| Elizabeth | `#6950A1` |

### Thames

Single stylized SVG path string mirroring the TFL map's iconic curves through Westminster, Waterloo, Tower Bridge, and the Isle of Dogs loop.

## Graph Helpers

- `neighborsOnLine(station, line)` — locates `station` in the line's `sequence(s)`, returns up to two adjacent station names; handles loop.
- `allNeighbors(station)` — union across the station's lines.
- `bfsDistance(a, b)` — plain BFS for "stops away".
- `bearing(from, to)` — `atan2(dy, dx)` over stylized coords, snapped to N / NE / E / SE / S / SW / W / NW.

## Puzzle Rendering

The right panel is one `<svg id="map">` with a `viewBox` acting as the camera.

**Layers** (rendered top to bottom of z-order, bottom drawn first):

1. **Paper grid + grain** (`<defs>` filter feTurbulence noise, very low opacity).
2. **Thames** — hidden until guess 5.
3. **Adjacent line segments** — second-degree network around the target, hidden until guess 3.
4. **Target's own line stubs** — always visible.
5. **Adjacent station markers** — small dot interchange markers, no labels, hidden until guess 3.
6. **Target station marker** — TFL interchange style (white capsule/circle with black outline), always visible.
7. **Reveal badges** (zone chip, first-letter chip) — appear as the player progresses.

**Angle computation for target line stubs:**

For each line at the target station:

- For each existing neighbor `n` on that line: compute `θ = atan2(n.y - t.y, n.x - t.x)`, snap to nearest `π/4`.
- Group all stubs by snapped angle. If multiple lines exit in the same direction, lay them out parallel: perpendicular offset `i * (lineWidth + gap)` centred on the original direction.
- Draw each stub as an SVG `<line>` with `stroke-width: 8`, `stroke-linecap: round`. Length: full distance to the neighbor when the camera shows the neighbor, otherwise a fixed short stub length (so the close-in view looks deliberate, not truncated).

**Camera (viewBox) per guess count:**

- Guesses 0–2: tight crop, ~280 units wide centred on target.
- Guesses 3–4: medium crop, ~600 units wide. Neighbors visible.
- Guesses 5+: wide crop, ~1100 units. Thames visible.

CSS transitions on `viewBox` give a smooth zoom-out motion (using a small RAF tween since `viewBox` doesn't natively animate via CSS).

**Reveal layer schedule:**

| After guess | New reveal |
|---|---|
| 1 (wrong) | Lines light up with real TFL colours (replacing greyscale stubs) |
| 2 (wrong) | Zoom out to medium; neighbour markers + their outbound lines fade in |
| 3 (wrong) | Zone badge appears below the target |
| 4 (wrong) | Zoom out to wide; Thames fades in |
| 5 (wrong) | First-letter badge appears |

Before any guess, the player sees: greyscale line stubs in correct angles + a generic interchange marker. The aesthetic from frame one already feels like a Tube map.

## Input & Autocomplete

- Single text `<input>` on the left panel.
- On every `input` event, filter `Object.keys(STATIONS)` by:
  1. Case-insensitive prefix on any word in the station name (highest priority).
  2. Case-insensitive substring (lower priority).
- Render up to 8 results in a dropdown below the input. Highlight first by default.
- Keyboard: ArrowDown / ArrowUp moves highlight (wrapping). Enter behavior depends on dropdown state — when the dropdown is open with a highlighted suggestion, Enter selects that suggestion AND submits the guess in one keystroke (no double-Enter friction). Tab fills the input from the highlighted suggestion without submitting. Escape closes the dropdown.
- Submit button next to input; disabled until input value is an exact station name. Useful for mouse users.
- Subtle "click" tick on each keystroke and each highlight change.

## Guess Feedback

On submit:

1. **If correct** — see Win Sequence.
2. **If wrong** — append a Transit Ticket to the history list, advance reveal layer, play thud.

**Transit Ticket** card:

- Cream paper background, rounded corners, faint dotted ticket-edge border, a brown "magnetic strip" bar along the bottom edge.
- Top row: station name in Hammersmith One.
- Middle row: small colored squares (one per line at the guessed station) using line colours — like a mini palette.
- Bottom row: two badges — "X stops" (BFS distance), and an 8-direction arrow rendered as an SVG glyph oriented to the bearing toward the target.
- New tickets slide in from the right; history scrolls.

## Win Sequence

- Locks input, plays chime arpeggio.
- Full-bleed celebration: confetti-style burst of small coloured discs (line palette) emitted from the target on the map.
- Modal: roundel header, "STATION FOUND", target name + lines, stats (guesses used, today's date), an emoji grid, and a Copy button.

**Emoji grid format:**

```
TUBE-LE 2026-05-16  3/6

⬜🟧⬛
🟩🟦🟥
🟧🟨🎯
```

Each row = one guess. Squares per row = lines at that guessed station, mapped to closest emoji colour from the TFL palette:

| Line | Emoji |
|---|---|
| Bakerloo, Overground | 🟧 |
| Central | 🟥 |
| Circle, W&C | 🟨 |
| District | 🟩 |
| H&C | 🟪 (fallback) |
| Jubilee | ⬜ |
| Metropolitan | 🟪 |
| Northern, DLR | ⬛ |
| Piccadilly | 🟦 |
| Victoria | 🟦 |
| Elizabeth | 🟪 |

Winning guess row appends a 🎯.

Copy button uses `navigator.clipboard.writeText`.

## Audio

Single shared `AudioContext` lazily created and `resume()`d on first user gesture.

- **Click** — `triangle` osc at 1200Hz; gain 0.05 → 0.001 over 40ms.
- **Thud** — `sine` osc, freq glide 80 → 40Hz over 300ms; gain 0.4 → 0.001 over 400ms; followed by a second darker `sine` at 55Hz for low-end body.
- **Win chime** — four triangle notes (C5 523, E5 659, G5 784, C6 1047), 120ms apart, each 0.1 → 0.001 over 350ms.

Audio is **off-by-default-friendly**: a small mute toggle in the panel header. State persists in `localStorage`.

## Game State & Daily Seed

```
state = {
  date: "YYYY-MM-DD",
  puzzleOffset: 0,        // "Next puzzle" advances this in memory
  targetName: "...",
  guesses: [{ name, distance, bearing }, ...],
  status: "playing" | "won" | "lost",
  muted: false,
}
```

Target selection: `hash(date + ":" + puzzleOffset) % stationNames.length`. Same date + offset always picks the same station; "Next puzzle" button in the header bumps `puzzleOffset` and resets state (without changing `date`). No persistence of guesses across reloads (intentional: keeps scope tight).

## Aesthetic Decisions

- **Background**: Paper cream `#FAF7F0` everywhere with a subtle SVG noise overlay at 4% opacity for that printed-on-paper texture.
- **Ink**: `#0A0A0A` for type and borders. No pure black on cream — the slight warm shift reads as printed.
- **Accents**: TFL roundel red `#DC241F` and roundel blue `#0019A8` used sparingly for the brand chip and the submit button only.
- **Type**:
  - Display: `Hammersmith One` — headings, ticket station names, modal title.
  - Body: `Public Sans` — input, buttons, badges.
- **Roundel**: pure SVG (red circle, blue horizontal bar, "UNDERGROUND" knockout in white) sized into the header.
- **Layout**: 420px fixed left panel, flexible right map. Below 900px viewport width, stack vertically with the map on top.

## Testing Approach

This is a single-file UI app; no test runner. Verification is manual:

- Open the file in Chrome. Confirm the puzzle renders, the lines exit at correct angles with parallel offsets, the marker is correct.
- Play a full game: try a near-guess, a far-guess, a same-line guess. Verify "stops away" and bearing match expectations.
- Confirm reveal layers fire on guesses 2, 3, 4, 5.
- Win, verify modal, verify Copy button writes to clipboard.
- Exhaust guesses, verify lose state shows station.
- "Next puzzle" advances to a different target.
- Audio: click sounds, thud on wrong, chime on win, mute toggle persists.
- Keyboard: arrow keys + Enter cleanly select from autocomplete.

## File Layout

```
/home/violet/source/Tube-le/
├── docs/superpowers/specs/2026-05-16-tube-le-design.md   (this file)
└── index.html                                            (the deliverable)
```
