#!/usr/bin/env python3
"""
Replace 'Study N' and 'Studies N, M, ...' references with \citet{} / \cite{} commands.

Patterns handled:
1. 'Study N \cite{key}'  → '\citet{key}'
2. '(Study N) \cite{key}' → '\citep{key}'
3. '(Study N \cite{key})' → '\citep{key}'
4. 'Studies N, M, ... \cite{key1, key2}' → '\cite{key1, key2}'
5. '(Studies N, M, ... \cite{key1, key2})' → '\cite{key1, key2}'
6. 'Study N' (no \cite follows) → '\citet{mapping[N]}'
7. Table rows starting with 'N &' → '\cite{key} &'
"""

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
TEX_FILE = BASE / "review_draft" / "paper.tex"
MAPPING_FILE = BASE / "data" / "study_pdf_mapping.json"

# Build study_id -> bibtex_key mapping
with open(MAPPING_FILE) as f:
    mapping = json.load(f)
ID_TO_KEY = {entry["study_id"]: entry["bibtex_key"] for entry in mapping}

# Excluded study IDs (new numbering)
EXCLUDED = {7, 26, 27, 33, 57, 68}


def replace_study_refs(content):
    changes = 0
    warnings = []

    # --- Pattern 1: 'Study N \cite{key}' → '\citet{key}' ---
    # Also handles '(Study N) \cite{key}' and '(Study N \cite{key})'
    def fix_study_cite(m):
        nonlocal changes
        paren_before = m.group(1) or ""
        # group 2 = the study number (not used, we trust the cite key)
        cite_cmd = m.group(3)
        cite_key = m.group(4)
        paren_after = m.group(5) or ""

        changes += 1

        if paren_before == "(" and paren_after == ")":
            return f"\\citep{{{cite_key}}}"
        elif paren_before == "(":
            return f"(\\citet{{{cite_key}}}"
        elif paren_after == ")":
            return f"\\citet{{{cite_key}}})"
        else:
            return f"\\citet{{{cite_key}}}"

    # Match: optional ( + "Study N" + optional ) + spaces + \cite{key} + optional )
    content = re.sub(
        r'(\()?[Ss]tudy\s+(\d+)\)?\s*\\(cite\w*)\{([^}]+)\}(\))?',
        fix_study_cite, content
    )

    # --- Pattern 2: 'Studies N, M, ... \cite{keys}' → '\cite{keys}' ---
    def fix_studies_cite(m):
        nonlocal changes
        paren_before = m.group(1) or ""
        cite_cmd = m.group(2)
        cite_keys = m.group(3)
        paren_after = m.group(4) or ""

        changes += 1

        if paren_before == "(" and paren_after == ")":
            return f"\\cite{{{cite_keys}}}"
        elif paren_before == "(":
            return f"(\\cite{{{cite_keys}}}"
        elif paren_after == ")":
            return f"\\cite{{{cite_keys}}})"
        else:
            return f"\\cite{{{cite_keys}}}"

    # Match: optional ( + "Studies N, M, ..." + spaces + \cite{keys} + optional )
    content = re.sub(
        r'(\()?[Ss]tudies\s+(?:\d+(?:\s*,\s*\d+)*(?:\s*,?\s*and\s+\d+)?)\s*\\(cite\w*)\{([^}]+)\}(\))?',
        fix_studies_cite, content
    )

    # --- Pattern 3: Remaining 'Study N' without \cite → '\citet{key}' ---
    def fix_study_alone(m):
        nonlocal changes
        full = m.group(0)
        num = int(m.group(1))

        if num in ID_TO_KEY:
            key = ID_TO_KEY[num]
            changes += 1
            return f"\\citet{{{key}}}"
        else:
            warnings.append(f"  WARNING: Study {num} has no bibtex key mapping")
            return full

    # Match 'Study N' NOT followed by \cite (negative lookahead)
    content = re.sub(
        r'(?<![\\])[Ss]tudy\s+(\d+)(?!\s*\\cite)',
        fix_study_alone, content
    )

    # --- Pattern 4: RoB table rows 'N & ...' → '\cite{key} & ...' ---
    def fix_table_row(m):
        nonlocal changes
        num = int(m.group(1))
        rest = m.group(2)

        if num in ID_TO_KEY and num not in EXCLUDED:
            key = ID_TO_KEY[num]
            changes += 1
            return f"\\cite{{{key}}}{rest}"
        elif num in EXCLUDED:
            return m.group(0)
        else:
            return m.group(0)

    content = re.sub(r'^(\d+)( & )', fix_table_row, content, flags=re.MULTILINE)

    return content, changes, warnings


def main():
    with open(TEX_FILE) as f:
        content = f.read()

    content, changes, warnings = replace_study_refs(content)

    with open(TEX_FILE, "w") as f:
        f.write(content)

    print(f"Replaced {changes} study references with \\citet/\\cite commands")
    for w in warnings:
        print(w)

    # Verify no remaining "Study N" refs
    remaining = re.findall(r'[Ss]tudy\s+(\d+)', content)
    if remaining:
        print(f"\nRemaining 'Study N' references ({len(remaining)}):")
        for num in sorted(set(int(n) for n in remaining)):
            count = sum(1 for n in remaining if int(n) == num)
            print(f"  Study {num}: {count} occurrence(s)")


if __name__ == "__main__":
    main()
