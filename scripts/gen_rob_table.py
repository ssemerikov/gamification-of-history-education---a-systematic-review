#!/usr/bin/env python3
"""Generate correct RoB table rows from extracted data (only eligible studies)."""

import csv
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ROB_CSV = BASE / "data" / "aggregated" / "risk_of_bias_table.csv"
MAPPING = BASE / "data" / "study_pdf_mapping.json"

# Load mapping for bibtex keys
with open(MAPPING) as f:
    mapping = json.load(f)
id_to_key = {e["study_id"]: e["bibtex_key"] for e in mapping}

# Load RoB data
rows = []
with open(ROB_CSV) as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["meets_criteria"] == "True":
            sid = int(row["study_id"])
            key = row.get("bibtex_key") or id_to_key.get(sid, str(sid))
            rows.append({
                "study_id": sid,
                "key": key,
                "d1": row["domain1_judgment"],
                "d2": row["domain2_judgment"],
                "d3": row["domain3_judgment"],
                "overall": row["overall"],
            })

# Sort by study_id numerically
rows.sort(key=lambda r: r["study_id"])

print(f"% {len(rows)} eligible studies")
for r in rows:
    print(f"\\cite{{{r['key']}}} & {r['d1']} & {r['d2']} & {r['d3']} & {r['overall']} \\\\")
