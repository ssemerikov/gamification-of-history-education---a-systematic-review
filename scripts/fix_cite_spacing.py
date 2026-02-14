#!/usr/bin/env python3
"""Add missing spaces after \cite{} commands followed by lowercase letters."""

import re
from pathlib import Path

TEX_FILE = Path(__file__).resolve().parent.parent / "review_draft" / "paper.tex"

with open(TEX_FILE) as f:
    content = f.read()

count = 0

def add_space(m):
    global count
    count += 1
    return m.group(1) + " " + m.group(2)

# Match \cite{...} or \citet{...} or \citep{...} immediately followed by a-z
pattern = r'(\\cite\w*\{[^}]+\})([a-z])'
content = re.sub(pattern, add_space, content)

with open(TEX_FILE, "w") as f:
    f.write(content)

print(f"Added {count} missing spaces after \\cite commands")
