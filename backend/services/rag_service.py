"""
rag_service.py - semantic search over the GSFC University knowledge base.

Each KB entry (knowledge_base/documents/gsfcu_kb.json) looks like:
  {"id", "category", "title", "content", "source", "last_updated"}
Embeddings are built by build_embeddings.py.
"""

import json
import os
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from google import genai


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EMBEDDINGS_PATH = PROJECT_ROOT / "knowledge_base" / "kb_embeddings.json"

# Must be the SAME model used in build_embeddings.py
EMBEDDING_MODEL = "models/gemini-embedding-2"

load_dotenv(PROJECT_ROOT / ".env")
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY was not found in .env")

client = genai.Client(api_key=api_key)

_INDEX = None  # (items, normalised matrix, title word sets)

# Words too common to count as a keyword match
STOPWORDS = {
    "tell", "about", "what", "which", "does", "have", "with", "that", "this",
    "from", "your", "there", "where", "when", "please", "give", "information",
    "details", "university", "gsfc", "know", "want", "need", "like", "show",
    "can", "how", "who", "are", "the", "and", "for",
}
TITLE_BONUS = 0.04     # per shared keyword
MAX_BONUS = 0.08


def _words(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower())
            if len(w) >= 3 and w not in STOPWORDS}


def _load_index():
    global _INDEX
    if _INDEX is None:
        with open(EMBEDDINGS_PATH, "r", encoding="utf-8") as f:
            items = json.load(f)
        matrix = np.array([i["embedding"] for i in items], dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1
        title_words = [_words(i["title"]) for i in items]
        _INDEX = (items, matrix / norms, title_words)
    return _INDEX


def reload_index():
    """Call after rebuilding embeddings, so no restart is needed."""
    global _INDEX
    _INDEX = None
    _embed_query.cache_clear()
    _load_index()


@lru_cache(maxsize=256)
def _embed_query(question: str) -> tuple:
    """Cached, so repeated questions don't use embedding quota."""
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=question,
    )
    return tuple(response.embeddings[0].values)


def search_kb(question: str, top_k: int = 3) -> list:
    """
    Top_k most relevant KB entries (highest score first).
    Score = cosine similarity + a small bonus when a keyword of the question
    also appears in the entry title (helps short questions like "hostel fee").
    """
    items, matrix, title_words = _load_index()

    q = np.array(_embed_query(question.strip()), dtype=np.float32)
    norm = np.linalg.norm(q)
    if norm:
        q = q / norm

    sims = matrix @ q
    q_words = _words(question)
    bonus = np.array([
        min(MAX_BONUS, TITLE_BONUS * len(q_words & tw)) for tw in title_words
    ], dtype=np.float32)
    scores = np.minimum(sims + bonus, 1.0)

    order = np.argsort(-scores)[:top_k]

    return [
        {
            "id": items[i]["id"],
            "title": items[i]["title"],
            "category": items[i].get("category", ""),
            "source": items[i].get("source", ""),
            "text": items[i]["text"],
            "similarity": float(scores[i]),
        }
        for i in order
    ]