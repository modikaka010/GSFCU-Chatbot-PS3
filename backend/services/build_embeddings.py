"""
build_embeddings.py - incremental embedding builder for the university KB.

- Re-uses embeddings for entries whose text has not changed.
- Retries on 503/429 with backoff and saves progress as it goes.
- Entries deleted from the KB disappear from the embeddings file.

Run from PROJECT ROOT:  python -m backend.services.build_embeddings
"""

import json
import os
import random
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
KB_DIR = PROJECT_ROOT / "knowledge_base" / "documents"
EMBEDDINGS_PATH = PROJECT_ROOT / "knowledge_base" / "kb_embeddings.json"

# IMPORTANT: must be the SAME model used in rag_service.py for queries.
EMBEDDING_MODEL = "models/gemini-embedding-2"

MAX_ATTEMPTS = 6
BASE_DELAY = 4
DELAY_BETWEEN_CALLS = 0.5
REQUIRED = ("id", "title", "content")

load_dotenv(PROJECT_ROOT / ".env")
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY was not found in .env")

client = genai.Client(api_key=api_key)


def build_text(entry: dict) -> str:
    return (
        f"Category: {entry.get('category', 'general')}\n"
        f"Title: {entry['title']}\n\n"
        f"{entry['content'].strip()}"
    )


def embed_with_retry(text: str):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.models.embed_content(model=EMBEDDING_MODEL, contents=text)
            return response.embeddings[0].values
        except Exception as exc:
            wait = BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 2)
            print(f"  ! {type(exc).__name__} ({attempt}/{MAX_ATTEMPTS}) - waiting {wait:.0f}s")
            time.sleep(wait)
    return None


def save(embedded: list):
    with open(EMBEDDINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(embedded, f)


def main():
    # Read every *.json in documents/ (skip backups), so hand-written files
    # like people_and_faqs.json sit next to the auto-generated gsfcu_kb.json
    entries = []
    for path in sorted(KB_DIR.glob("*.json")):
        if "backup" in path.name:
            continue
        with open(path, "r", encoding="utf-8") as f:
            part = json.load(f)
        print(f"Loaded {len(part):>4} entries from {path.name}")
        entries.extend(part)

    # Validate before spending any API quota
    seen = set()
    for n, e in enumerate(entries, start=1):
        missing = [k for k in REQUIRED if not str(e.get(k, "")).strip()]
        if missing:
            raise ValueError(f"Entry #{n} is missing {missing}: {e}")
        if e["id"] in seen:
            raise ValueError(f"Duplicate id: {e['id']}")
        seen.add(e["id"])

    old = {}
    if EMBEDDINGS_PATH.exists():
        with open(EMBEDDINGS_PATH, "r", encoding="utf-8") as f:
            old = {item["id"]: item for item in json.load(f)}

    embedded, reused, created, failed = [], 0, 0, []

    for i, entry in enumerate(entries, start=1):
        text = build_text(entry)
        prev = old.get(entry["id"])

        record_meta = {
            "id": entry["id"],
            "title": entry["title"],
            "category": entry.get("category", ""),
            "source": entry.get("source", ""),
            "text": text,
        }

        if prev and prev["text"] == text:
            embedded.append({**record_meta, "embedding": prev["embedding"]})
            reused += 1
            continue

        print(f"[{i}/{len(entries)}] Embedding: {entry['title']}")
        vector = embed_with_retry(text)
        if vector is None:
            failed.append(entry["id"])
            print("  x FAILED")
            continue

        embedded.append({**record_meta, "embedding": vector})
        created += 1
        save(embedded)
        time.sleep(DELAY_BETWEEN_CALLS)

    save(embedded)
    print(f"\nReused {reused}, newly embedded {created}, failed {len(failed)}.")
    print(f"Total saved: {len(embedded)} -> {EMBEDDINGS_PATH}")
    if failed:
        print("Failed (re-run to retry):", ", ".join(failed))


if __name__ == "__main__":
    main()