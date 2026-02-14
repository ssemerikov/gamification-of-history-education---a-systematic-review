#!/usr/bin/env python3
"""
Convert 'Paper N' and 'Papers N, M, ...' references to \citet/\cite commands.
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


def fix_paper_refs(content):
    changes = 0

    # Pattern 1: 'Paper N \cite{key}' → '\citet{key}'
    def fix_paper_cite(m):
        nonlocal changes
        key = m.group(2)
        changes += 1
        return f"\\citet{{{key}}}"

    content = re.sub(
        r'[Pp]aper\s+(\d+)\s*\\cite\w*\{([^}]+)\}',
        fix_paper_cite, content
    )

    # Pattern 2: 'Papers N, M, ... \cite{keys}' → '\cite{keys}'
    content = re.sub(
        r'[Pp]apers\s+(?:\d+(?:\s*,\s*\d+)*(?:\s*,?\s*and\s+\d+)?)\s*\\cite\w*\{([^}]+)\}',
        lambda m: f"\\cite{{{m.group(1)}}}",
        content
    )

    # Pattern 3: 'Paper N' alone → '\citet{key}'
    def fix_paper_alone(m):
        nonlocal changes
        num = int(m.group(1))
        if num in ID_TO_KEY:
            changes += 1
            return f"\\citet{{{ID_TO_KEY[num]}}}"
        return m.group(0)

    content = re.sub(
        r'[Pp]aper\s+(\d+)(?!\s*\\cite)',
        fix_paper_alone, content
    )

    # Pattern 4: 'Papers N, M, ...' alone → '\cite{key1, key2, ...}'
    def fix_papers_list(m):
        nonlocal changes
        nums_str = m.group(1).replace(" and ", ", ")
        nums = [int(n.strip()) for n in nums_str.split(",") if n.strip().isdigit()]
        keys = []
        for n in nums:
            if n in ID_TO_KEY:
                keys.append(ID_TO_KEY[n])
            else:
                return m.group(0)
        changes += 1
        return f"\\cite{{{', '.join(keys)}}}"

    content = re.sub(
        r'[Pp]apers\s+((?:\d+(?:\s*,\s*\d+)*(?:\s*,?\s*and\s+\d+)?))\s*(?!\\cite)',
        fix_papers_list, content
    )

    return content, changes


def main():
    with open(TEX_FILE) as f:
        content = f.read()

    content, changes = fix_paper_refs(content)

    with open(TEX_FILE, "w") as f:
        f.write(content)

    print(f"Converted {changes} 'Paper(s) N' references to \\citet/\\cite commands")

    remaining = re.findall(r'[Pp]apers?\s+\d+', content)
    if remaining:
        print(f"\nRemaining: {len(remaining)}")
        for r in remaining:
            print(f"  {r}")


if __name__ == "__main__":
    main()
