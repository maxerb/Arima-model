"""Explore (D-21): search a BFS LIK methods PDF for a per-position origin/type classification.
Usage: python scripts/explore/search_bfs_methods_pdf.py <pdf> [keywords...]"""
import sys
from pypdf import PdfReader
r = PdfReader(sys.argv[1]); keys = sys.argv[2:] or ["Herkunft", "Inland", "Ausland", "dauerhaft"]
for i, p in enumerate(r.pages):
    t = p.extract_text() or ""
    hits = [k for k in keys if k in t]
    if hits: print(f"--- page {i+1}: {hits}"); print(t[:1500])
