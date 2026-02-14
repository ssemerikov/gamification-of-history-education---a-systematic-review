#!/usr/bin/env python3
"""
Cleanup pass after replace_study_refs_with_citet.py.
Fixes:
1. Unmatched '(\citet{key}' → '\citep{key}' (where ) was eaten)
2. Duplicate citations: '\citet{key} ... \cite{key}' → remove trailing \cite
3. Bare numbers before \cite{}: '2 \cite{key}' → '\cite{key}'
4. Remaining '(Studies N, ...) \cite{keys}' patterns
"""

import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
TEX_FILE = BASE / "review_draft" / "paper.tex"


def cleanup(content):
    changes = 0

    # Fix 1: '(\citet{key}.' or '(\citet{key}\n' at end of line/sentence
    # These are cases where (Study N) \cite{key} lost its closing paren
    # Pattern: '(\citet{key}' NOT followed by ')' → '\citep{key}'
    def fix_orphan_paren_citet(m):
        nonlocal changes
        key = m.group(1)
        after = m.group(2)
        changes += 1
        return f"\\citep{{{key}}}{after}"

    # Match (\citet{key} followed by period, comma, newline, or space (no closing paren)
    content = re.sub(
        r'\(\\citet\{([^}]+)\}([.,\s\n])',
        fix_orphan_paren_citet, content
    )

    # Fix 1b: '(\citet{key}:' - technology list items where (Study N \cite{key}): became (\citet{key}:
    def fix_orphan_paren_colon(m):
        nonlocal changes
        key = m.group(1)
        changes += 1
        return f"\\cite{{{key}}}:"

    content = re.sub(
        r'\(\\citet\{([^}]+)\}:',
        fix_orphan_paren_colon, content
    )

    # Fix 2: Duplicate citations '\citet{key} ... \cite{key}' on same line
    # Remove trailing \cite{key} when \citet{key} already provides the citation
    def fix_dup_cite(m):
        nonlocal changes
        key = m.group(1)
        between = m.group(2)
        changes += 1
        return f"\\citet{{{key}}}{between}"

    # Match \citet{key} ... \cite{key} (same key, trailing cite is redundant)
    content = re.sub(
        r'\\citet\{([^}]+)\}([^\\]*?)\\cite\{\1\}',
        fix_dup_cite, content
    )

    # Fix 3: Bare numbers before \cite{}: '2 \cite{key}' → '\cite{key}'
    # These are leftover study numbers from lists
    def fix_bare_number(m):
        nonlocal changes
        key = m.group(2)
        changes += 1
        return f" \\cite{{{key}}}"

    content = re.sub(
        r';\s*(\d+)\s*\\cite\{([^}]+)\}',
        lambda m: f"; \\cite{{{m.group(2)}}}",
        content
    )

    # Fix 4: Remaining '(Studies N, ...) \cite{keys}' or 'Studies N, ...) \cite{keys}'
    content = re.sub(
        r'\(?[Ss]tudies\s+(?:\d+(?:\s*,\s*\d+)*(?:\s*,?\s*and\s+\d+)?)\)?\s*\\cite',
        lambda m: "\\cite",
        content
    )

    # Fix 5: '\citet{key1}, \citet{key1, key2}' → '\citet{key1, key2}'
    # (broken pattern from Study 12, Study 71 \cite{12..., 71...})
    def fix_double_citet(m):
        nonlocal changes
        keys = m.group(2)
        changes += 1
        return f"\\citet{{{keys}}}"

    content = re.sub(
        r'\\citet\{([^}]+)\},\s*\\citet\{(\1[^}]*)\}',
        fix_double_citet, content
    )

    return content, changes


def main():
    with open(TEX_FILE) as f:
        content = f.read()

    content, changes = cleanup(content)

    with open(TEX_FILE, "w") as f:
        f.write(content)

    print(f"Cleanup: {changes} fixes applied")

    # Check for remaining issues
    orphan = len(re.findall(r'\(\\citet\{', content))
    if orphan:
        print(f"  Remaining orphan '(\\citet{{': {orphan}")
        for m in re.finditer(r'\(\\citet\{[^}]+\}', content):
            # Find line number
            line = content[:m.start()].count('\n') + 1
            print(f"    Line {line}: {m.group()}")

    dup = re.findall(r'\\citet\{([^}]+)\}[^\\]*\\cite\{\1\}', content)
    if dup:
        print(f"  Remaining duplicate cites: {len(dup)}")

    bare = re.findall(r';\s*\d+\s*\\cite\{', content)
    if bare:
        print(f"  Remaining bare numbers: {len(bare)}")


if __name__ == "__main__":
    main()
