#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import re

with open("london-tube-net.svg", "r", encoding="utf-8") as f:
    svg = f.read()

# Strip the outer <svg ...> opening tag and </svg> closing tag
inner = re.sub(r"^<svg[^>]*>\s*", "", svg.strip(), flags=re.DOTALL)
inner = re.sub(r"\s*</svg>\s*$", "", inner, flags=re.DOTALL)

group = f'<g id="tube-map-src" style="display:none">\n{inner}\n</g>'

with open("index.html", "r", encoding="utf-8") as f:
    html = f.read()

if 'id="tube-map-src"' in html:
    print("ERROR: tube-map-src already present in index.html — aborting")
    raise SystemExit(1)

html = html.replace("</body>", f"{group}\n</body>")

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"Done — tube-map-src group ({len(group):,} chars) injected before </body>")
