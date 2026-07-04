#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import json
import re

with open("station_years.json") as f:
    year_data = json.load(f)

def norm(s):
    return s.lower().replace("'", "'").replace("'", "'").replace("&", "and").strip()

year_lookup = {norm(k): v for k, v in year_data.items()}

with open("index.html") as f:
    lines = f.readlines()

modified = 0
missing = []
for i, line in enumerate(lines):
    m = re.match(r'\s+"([^"]+)":\s*\{.*\bzone:\d+', line)
    if not m:
        continue
    station_name = m.group(1)
    if "year:" in line:
        continue  # already patched
    key = norm(station_name)
    if key in year_lookup:
        year = year_lookup[key]
        lines[i] = re.sub(r"(\bzone:(\d+))", rf"\1, year:{year}", line, count=1)
        modified += 1
    else:
        missing.append(station_name)

if missing:
    print(f"WARNING — no year data for {len(missing)} stations:")
    for s in sorted(missing):
        print(f"  {s}")

with open("index.html", "w") as f:
    f.writelines(lines)

print(f"\nApplied year to {modified} stations.")
