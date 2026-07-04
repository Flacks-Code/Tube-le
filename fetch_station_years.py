#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["requests", "beautifulsoup4"]
# ///

import json
import re
import requests
from bs4 import BeautifulSoup

url = "https://en.wikipedia.org/wiki/List_of_London_Underground_stations"
resp = requests.get(url, headers={"User-Agent": "Tube-le/1.0"})
resp.raise_for_status()
soup = BeautifulSoup(resp.text, "html.parser")

table = soup.find("table", {"class": "wikitable"})
headers = [th.get_text(strip=True).lower() for th in table.find_all("tr")[0].find_all(["th", "td"])]
print("Headers:", headers)

year_col = next((i for i, h in enumerate(headers) if "open" in h or "year" in h), None)
if year_col is None:
    raise ValueError(f"Could not find year column. Headers: {headers}")
print(f"Year column index: {year_col}")

years = {}
for row in table.find_all("tr")[1:]:
    cells = row.find_all(["td", "th"])
    if len(cells) <= year_col:
        continue
    name = re.sub(r"\[.*?\]", "", cells[0].get_text(strip=True)).strip()
    year_text = cells[year_col].get_text(strip=True)
    m = re.search(r"\b(\d{4})\b", year_text)
    if m and name:
        years[name] = int(m.group(1))

with open("station_years.json", "w") as f:
    json.dump(years, f, indent=2, sort_keys=True)

print(f"Fetched {len(years)} station years → station_years.json")
