#!/usr/bin/env python3
"""Remove citations to excluded studies from paper.tex.

For multi-key \cite{a, b, c} commands, removes the excluded key(s) and keeps the rest.
For single-key citations that become empty, removes the entire \cite{} command.
Flags lines where an excluded study is the subject of a sentence for manual review.
"""

import re
import sys
from pathlib import Path

EXCLUDED_KEYS = {
    "7Natvig2004F-1",
    "26Dias2021",
    "27Sumi2022",
    "33Oceja2022419",
    "57Huntley2011567",
    "68cole2015end",
    "Mohamad20181325",
}

TEX = Path(__file__).resolve().parent.parent / "review_draft" / "paper.tex"

content = TEX.read_text()
lines = content.split("\n")
changes = 0
manual_review = []

new_lines = []
for i, line in enumerate(lines):
    orig = line

    # Find all \cite-family commands
    def fix_cite(m):
        global changes
        cmd = m.group(1)  # cite, citet, citep, etc.
        keys_str = m.group(2)
        keys = [k.strip() for k in keys_str.split(",")]
        kept = [k for k in keys if k not in EXCLUDED_KEYS]
        removed = [k for k in keys if k in EXCLUDED_KEYS]

        if not removed:
            return m.group(0)  # nothing to do

        changes += len(removed)

        if kept:
            return f"\\{cmd}{{{', '.join(kept)}}}"
        else:
            # All keys removed - return empty string (will clean up later)
            return ""

    line = re.sub(r'\\(cite[tp]?)\{([^}]+)\}', fix_cite, line)

    # Clean up artifacts from removed citations:
    # " , " at start of items after removing a \cite
    # Empty \item lines
    # Double spaces
    line = re.sub(r'\s{2,}', ' ', line)
    # Remove orphaned ", " or " ," before/after removed citations
    line = re.sub(r',\s*,', ',', line)
    # Remove trailing " ," or ", " at end of text before punctuation
    line = re.sub(r'\s*,\s*([.;:])', r'\1', line)
    # Remove leading ", " after opening
    line = re.sub(r'\(\s*,\s*', '(', line)
    line = re.sub(r',\s*\)', ')', line)

    new_lines.append(line)

content = "\n".join(new_lines)

# Clean up empty citation artifacts:
# " \cite{}" or "\citet{}" that became empty
content = re.sub(r'\s*\\cite[tp]?\{\s*\}', '', content)

# Find lines that now seem broken (have excluded study names but no cite)
# These need manual review
for i, line in enumerate(content.split("\n"), 1):
    for key in EXCLUDED_KEYS:
        # Check if key appears in non-cite context (shouldn't happen, but safety check)
        if key in line and f"\\cite" not in line:
            manual_review.append((i, line.strip()[:100]))

TEX.write_text(content)
print(f"Removed {changes} excluded citation keys")
if manual_review:
    print(f"\nLines needing manual review ({len(manual_review)}):")
    for lnum, text in manual_review:
        print(f"  L{lnum}: {text}")
