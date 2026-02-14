#!/usr/bin/env python3
"""
Convert remaining 'Studies N, M, ...' references (without \cite) to \cite{key1, key2, ...}.
"""

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
TEX_FILE = BASE / "review_draft" / "paper.tex"
MAPPING_FILE = BASE / "data" / "study_pdf_mapping.json"

with open(MAPPING_FILE) as f:
    mapping = json.load(f)
ID_TO_KEY = {entry["study_id"]: entry["bibtex_key"] for entry in mapping}


def fix_studies_list(content):
    changes = 0
    warnings = []

    def replace_studies_list(m):
        nonlocal changes
        full = m.group(0)
        nums_str = m.group(1)

        # Parse numbers from "N, M, and K" or "N, M, K"
        nums_str_clean = nums_str.replace(" and ", ", ")
        nums = [int(n.strip()) for n in nums_str_clean.split(",") if n.strip().isdigit()]

        keys = []
        for n in nums:
            if n in ID_TO_KEY:
                keys.append(ID_TO_KEY[n])
            else:
                warnings.append(f"  WARNING: Study {n} has no bibtex key")
                return full

        changes += 1
        return f"\\cite{{{', '.join(keys)}}}"

    # Match 'Studies N, M, ..., and K' NOT followed by \cite
    content = re.sub(
        r'[Ss]tudies\s+((?:\d+(?:\s*,\s*\d+)*(?:\s*,?\s*and\s+\d+)?))\s*(?!\\cite)',
        replace_studies_list, content
    )

    return content, changes, warnings


def main():
    with open(TEX_FILE) as f:
        content = f.read()

    content, changes, warnings = fix_studies_list(content)

    with open(TEX_FILE, "w") as f:
        f.write(content)

    print(f"Converted {changes} 'Studies N, M, ...' references to \\cite commands")
    for w in warnings:
        print(w)

    # Check remaining
    remaining = re.findall(r'[Ss]tudies\s+\d+', content)
    if remaining:
        print(f"\nRemaining 'Studies N' references: {len(remaining)}")
        for m in re.finditer(r'[Ss]tudies\s+\d+[^\\]*', content):
            line = content[:m.start()].count('\n') + 1
            snippet = m.group()[:80]
            print(f"  Line {line}: {snippet}")


if __name__ == "__main__":
    main()
