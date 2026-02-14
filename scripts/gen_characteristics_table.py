#!/usr/bin/env python3
"""Generate study characteristics longtable rows for eligible studies."""

import csv
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CHAR_CSV = BASE / "data" / "aggregated" / "characteristics_table.csv"
ROB_CSV = BASE / "data" / "aggregated" / "risk_of_bias_table.csv"
MAPPING = BASE / "data" / "study_pdf_mapping.json"

with open(MAPPING) as f:
    mapping = json.load(f)
id_to_key = {e["study_id"]: e["bibtex_key"] for e in mapping}

# Load RoB for overall judgment
rob_map = {}
with open(ROB_CSV) as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["meets_criteria"] == "True":
            rob_map[int(row["study_id"])] = row["overall"]

def abbreviate_edu(edu):
    if not edu:
        return "--"
    e = edu.lower()
    if "primary" in e and "secondary" in e:
        return "K-12"
    if "primary" in e or "elementary" in e:
        return "Primary"
    if "higher" in e or "university" in e or "undergraduate" in e or "college" in e or "graduate" in e:
        return "Higher ed."
    if "secondary" in e or "high school" in e or "middle" in e or "junior" in e:
        return "Secondary"
    if "not" in e and "specified" in e:
        return "--"
    if "informal" in e or "museum" in e:
        return "Informal"
    if "young adult" in e:
        return "Young adults"
    return edu[:20]

def abbreviate_design(design):
    if not design:
        return "--"
    d = design.lower()
    if "quasi" in d:
        return "Quasi-exp."
    if "experimental" in d or "pre_post" in d or "pre-post" in d or "pre_experimental" in d:
        return "Experimental"
    if "mixed" in d:
        return "Mixed methods"
    if "design" in d and "based" in d:
        return "Design-based"
    if "case" in d and "study" in d:
        return "Case study"
    if "qualitative" in d:
        return "Qualitative"
    if "descriptive" in d:
        return "Descriptive"
    if "survey" in d:
        return "Survey"
    if "longitudinal" in d:
        return "Longitudinal"
    return design[:20]

def abbreviate_game(game):
    if not game:
        return "--"
    g = game.lower()
    if "vr" in g or "virtual reality" in g or "augmented reality" in g or "ar" in g:
        return "VR/AR"
    if "board" in g:
        return "Board game"
    if "card" in g:
        return "Card game"
    if "mobile" in g:
        return "Mobile"
    if "commercial" in g or "cots" in g:
        return "Commercial"
    if "role-playing" in g or "rpg" in g:
        return "RPG"
    if "web" in g or "online" in g or "browser" in g:
        return "Web-based"
    if "serious" in g:
        return "Serious game"
    if "simulation" in g or "strategy" in g:
        return "Simulation"
    if "digital" in g:
        return "Digital"
    if "multiple" in g or "mixed" in g:
        return "Mixed"
    return game[:20]

def extract_first_author(authors):
    if not authors:
        return "--"
    # Get first author surname
    parts = authors.split(";")
    if len(parts) == 1:
        parts = authors.split(",")
    first = parts[0].strip()
    # Get surname (last word or first word if "Last, First")
    words = first.split()
    if len(words) >= 2:
        surname = words[0].rstrip(",")
    else:
        surname = first
    et_al = " et al." if len(parts) > 1 or ";" in authors else ""
    return surname + et_al

def extract_sample(sample):
    if not sample:
        return "--"
    s = str(sample)
    # Try to extract number
    m = re.search(r'(\d+)', s)
    if m:
        return m.group(1)
    return "--"

# Load and process
rows = []
with open(CHAR_CSV) as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["meets_criteria"] == "True":
            sid = int(row["study_id"])
            key = id_to_key.get(sid, str(sid))
            year = row.get("year", "")
            country = row.get("country", "--")
            # Shorten long country strings
            if "," in country:
                countries = [c.strip() for c in country.split(",")]
                country = countries[0] + " +" + str(len(countries)-1)

            rows.append({
                "sid": sid,
                "key": key,
                "author_year": extract_first_author(row.get("authors", "")) + f" ({year})",
                "country": country[:15],
                "edu": abbreviate_edu(row.get("education_level", "")),
                "n": extract_sample(row.get("sample_size", "")),
                "design": abbreviate_design(row.get("study_design", "")),
                "game": abbreviate_game(row.get("game_type", "")),
                "rob": rob_map.get(sid, "--"),
            })

rows.sort(key=lambda r: r["sid"])

for r in rows:
    print(f"\\cite{{{r['key']}}} & {r['author_year']} & {r['country']} & {r['edu']} & {r['n']} & {r['design']} & {r['game']} & {r['rob']} \\\\")
