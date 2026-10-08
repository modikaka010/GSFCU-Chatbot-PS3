"""
report_missing.py - show which questions the knowledge base could not answer.

Replaces process_missing.py. For a university, answers must come from
OFFICIAL sources, so we do NOT auto-generate new entries with an LLM
(that would invent facts). Instead, staff read this report, find the real
answer, and add it to gsfcu_kb.json.

Run from inside backend/:   python report_missing.py
Then:  python -m backend.services.build_embeddings   (from project root)
and call POST /api/reload (or restart the backend).
"""

import json
from collections import Counter
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "knowledge_base" / "missing_queries.jsonl"

if not PATH.exists():
    raise SystemExit("No missing_queries.jsonl yet - nothing to report.")

records = []
for line in PATH.read_text(encoding="utf-8").splitlines():
    try:
        records.append(json.loads(line))
    except json.JSONDecodeError:
        pass

counts = Counter(r["question"].strip().lower() for r in records)
print(f"{len(records)} unanswered questions, {len(counts)} distinct.\n")
print("Most asked (add these to the knowledge base first):")
for question, n in counts.most_common(25):
    print(f"  {n:>3}x  {question}")
