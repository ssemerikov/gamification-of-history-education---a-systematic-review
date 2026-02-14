#!/usr/bin/env python3
"""
Update bibtex keys to match renumbered study IDs.
Updates: extraction JSONs, study_pdf_mapping.json, references.bib, paper.tex
"""

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
EXTRACTIONS_DIR = BASE / "data" / "extractions"
MAPPING_FILE = BASE / "data" / "study_pdf_mapping.json"
BIB_FILE = BASE / "review_draft" / "references.bib"
TEX_FILE = BASE / "review_draft" / "paper.tex"


def compute_key_mapping():
    """Compute old_key -> new_key mapping from extraction files."""
    key_map = {}
    for f in sorted(EXTRACTIONS_DIR.glob("study_*.json")):
        with open(f) as fh:
            d = json.load(fh)
        sid = d["study_id"]
        old_key = d.get("bibtex_key", "")
        if not old_key:
            continue
        m = re.match(r"^(\d+)", old_key)
        if m and int(m.group(1)) != sid:
            new_key = str(sid) + old_key[len(m.group(1)):]
            key_map[old_key] = new_key

    # Also handle Study 59 in references.bib: 60Kee2014270 -> 59Kee2014270
    # (extraction already has 59Kee2014270, but bib may still have 60Kee2014270)
    key_map["60Kee2014270"] = "59Kee2014270"

    return key_map


def update_extractions(key_map):
    """Update bibtex_key in extraction JSONs."""
    count = 0
    for f in sorted(EXTRACTIONS_DIR.glob("study_*.json")):
        with open(f) as fh:
            d = json.load(fh)
        old_key = d.get("bibtex_key", "")
        if old_key in key_map:
            d["bibtex_key"] = key_map[old_key]
            with open(f, "w") as fh:
                json.dump(d, fh, indent=2)
            count += 1
    print(f"Updated {count} extraction JSONs")


def update_mapping(key_map):
    """Update bibtex_key in study_pdf_mapping.json."""
    with open(MAPPING_FILE) as f:
        mapping = json.load(f)
    count = 0
    for entry in mapping:
        old_key = entry.get("bibtex_key", "")
        if old_key in key_map:
            entry["bibtex_key"] = key_map[old_key]
            count += 1
    with open(MAPPING_FILE, "w") as f:
        json.dump(mapping, f, indent=2)
    print(f"Updated {count} mapping entries")


def update_bib(key_map):
    """Update bibtex keys in references.bib."""
    with open(BIB_FILE, "r") as f:
        content = f.read()

    count = 0
    for old_key, new_key in key_map.items():
        # Match @type{old_key, pattern
        pattern = re.compile(r"(@\w+\{)" + re.escape(old_key) + r"(\s*,)")
        if pattern.search(content):
            content = pattern.sub(r"\g<1>" + new_key + r"\2", content)
            count += 1

    with open(BIB_FILE, "w") as f:
        f.write(content)
    print(f"Updated {count} bib entries")


def update_tex(key_map):
    """Update citation keys in paper.tex."""
    with open(TEX_FILE, "r") as f:
        content = f.read()

    count = 0
    for old_key, new_key in key_map.items():
        # Replace in \cite{...} commands and any other reference
        old_count = content.count(old_key)
        if old_count > 0:
            content = content.replace(old_key, new_key)
            count += old_count

    with open(TEX_FILE, "w") as f:
        f.write(content)
    print(f"Updated {count} citation references in paper.tex")


def main():
    key_map = compute_key_mapping()
    print(f"Key mapping ({len(key_map)} changes):")
    for old, new in sorted(key_map.items()):
        print(f"  {old} -> {new}")
    print()

    update_extractions(key_map)
    update_mapping(key_map)
    update_bib(key_map)
    update_tex(key_map)
    print("\nDone!")


if __name__ == "__main__":
    main()
