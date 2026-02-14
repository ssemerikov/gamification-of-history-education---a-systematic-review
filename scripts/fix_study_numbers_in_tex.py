#!/usr/bin/env python3
"""
Fix study number references in paper.tex to match renumbered IDs.
Old IDs 60-81 -> New IDs 59-80 (decrement by 1).
Also flags references to excluded studies for manual review.

Excluded studies (new IDs): 7, 26, 27, 33, 57, 68
"""

import re
import csv
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
TEX_FILE = BASE / "review_draft" / "paper.tex"

# Build old->new mapping from id_mapping.csv
OLD_TO_NEW = {}
with open(BASE / "data" / "aggregated" / "id_mapping.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        old_id = int(row["old_id"])
        new_id = int(row["new_id"])
        if old_id != new_id:
            OLD_TO_NEW[old_id] = new_id

# Excluded study new IDs
EXCLUDED = {7, 26, 27, 33, 57, 68}


def replace_study_number(match):
    """Replace a single study number, handling old->new mapping."""
    num = int(match.group(0))
    if num in OLD_TO_NEW:
        return str(OLD_TO_NEW[num])
    return str(num)


def fix_study_references(content):
    """Fix all study number references in the text."""
    changes = 0

    # Pattern 1: "Study N" or "Paper N" (singular)
    def fix_singular(m):
        nonlocal changes
        prefix = m.group(1)
        num = int(m.group(2))
        if num in OLD_TO_NEW:
            changes += 1
            return f"{prefix}{OLD_TO_NEW[num]}"
        return m.group(0)

    content = re.sub(r'((?:Study|Paper|study|paper)\s+)(\d+)', fix_singular, content)

    # Pattern 2: "Studies N, M, ..." or "Papers N, M, ..." - fix individual numbers within lists
    def fix_list(m):
        nonlocal changes
        prefix = m.group(1)  # "Studies " or "Papers "
        rest = m.group(2)    # "1, 2, 3, ..."

        def replace_num(nm):
            nonlocal changes
            num = int(nm.group(0))
            if num in OLD_TO_NEW:
                changes += 1
                return str(OLD_TO_NEW[num])
            return nm.group(0)

        new_rest = re.sub(r'\b(\d+)\b', replace_num, rest)
        return prefix + new_rest

    content = re.sub(
        r'((?:Studies|Papers|studies|papers)\s+)((?:\d+(?:\s*,\s*\d+)*(?:\s*,?\s*and\s+\d+)?))',
        fix_list, content
    )

    # Pattern 3: RoB table rows "N & ..." at start of line (in tabular)
    def fix_table_row(m):
        nonlocal changes
        num = int(m.group(1))
        rest = m.group(2)
        if num in OLD_TO_NEW:
            changes += 1
            return f"{OLD_TO_NEW[num]}{rest}"
        return m.group(0)

    content = re.sub(r'^(\d+)( & )', fix_table_row, content, flags=re.MULTILINE)

    return content, changes


def main():
    with open(TEX_FILE) as f:
        content = f.read()

    content, changes = fix_study_references(content)

    with open(TEX_FILE, "w") as f:
        f.write(content)

    print(f"Fixed {changes} study number references")

    # Check for references to excluded studies
    for sid in sorted(EXCLUDED):
        count = len(re.findall(rf'\bStudy {sid}\b|\bPaper {sid}\b', content))
        list_count = len(re.findall(rf'(?:Studies|Papers)\s+(?:\d+\s*,\s*)*{sid}\b', content))
        if count > 0 or list_count > 0:
            print(f"  WARNING: Excluded Study {sid} still referenced ({count} singular, ~{list_count} in lists)")


if __name__ == "__main__":
    main()
