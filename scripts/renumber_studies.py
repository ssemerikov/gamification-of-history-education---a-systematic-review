#!/usr/bin/env python3
"""
Renumber all study extraction JSONs to sequential IDs 1-80.
Current IDs: 1-58, 59, 61-81 (gap at 60).
New IDs: 1-80 (sequential).

Also updates:
  - study_id inside each JSON
  - data/study_pdf_mapping.json
  - Creates data/aggregated/id_mapping.csv for reference
"""

import json
import os
import csv
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
EXTRACTIONS_DIR = BASE / "data" / "extractions"
MAPPING_FILE = BASE / "data" / "study_pdf_mapping.json"
OUTPUT_DIR = BASE / "data" / "aggregated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    # Load all current studies and sort by current study_id
    studies = []
    for f in sorted(EXTRACTIONS_DIR.glob("study_*.json")):
        with open(f) as fh:
            data = json.load(fh)
        studies.append((data["study_id"], f, data))

    studies.sort(key=lambda x: x[0])

    if len(studies) != 80:
        print(f"WARNING: Expected 80 studies, found {len(studies)}")

    # Create old->new ID mapping
    id_map = {}
    for new_id, (old_id, filepath, data) in enumerate(studies, 1):
        id_map[old_id] = new_id

    # Write ID mapping for reference
    with open(OUTPUT_DIR / "id_mapping.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["old_id", "new_id", "title", "bibtex_key"])
        for old_id, new_id in sorted(id_map.items()):
            study_data = next(d for oid, _, d in studies if oid == old_id)
            w.writerow([
                old_id, new_id,
                study_data.get("bibliographic", {}).get("title", ""),
                study_data.get("bibtex_key", "")
            ])

    # Print changes
    changes = [(old, new) for old, new in id_map.items() if old != new]
    if changes:
        print(f"ID changes needed: {len(changes)}")
        for old, new in sorted(changes):
            print(f"  Study {old} -> Study {new}")
    else:
        print("No changes needed.")
        return

    # Step 1: Rename files to temporary names (avoid collisions)
    temp_files = {}
    for old_id, filepath, data in studies:
        new_id = id_map[old_id]
        if old_id != new_id:
            temp_path = EXTRACTIONS_DIR / f"study_{old_id}_temp.json"
            os.rename(filepath, temp_path)
            temp_files[new_id] = (temp_path, data)
        else:
            temp_files[new_id] = (filepath, data)

    # Step 2: Write files with new names and updated study_id
    for new_id, (temp_path, data) in sorted(temp_files.items()):
        data["study_id"] = new_id
        new_path = EXTRACTIONS_DIR / f"study_{new_id}.json"
        with open(new_path, "w") as f:
            json.dump(data, f, indent=2)
        # Remove temp file if it still exists and is different from new path
        if temp_path != new_path and temp_path.exists():
            os.remove(temp_path)

    # Step 3: Update mapping file
    with open(MAPPING_FILE) as f:
        mapping = json.load(f)

    for entry in mapping:
        old_id = entry["study_id"]
        if old_id in id_map:
            entry["study_id"] = id_map[old_id]

    # Sort by new study_id
    mapping.sort(key=lambda x: x["study_id"])

    with open(MAPPING_FILE, "w") as f:
        json.dump(mapping, f, indent=2)

    print(f"\nAll {len(studies)} files renumbered successfully.")
    print(f"ID mapping saved to {OUTPUT_DIR / 'id_mapping.csv'}")


if __name__ == "__main__":
    main()
