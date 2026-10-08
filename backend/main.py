import json
import os
import re
import uuid
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.llm_service import generate_answer, classify_question
from services.rag_service import search_kb, reload_index
from services.small_talk import small_talk_reply, OFF_TOPIC


app = FastAPI(title="GSFC University Student Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Settings (recalibrate with calibrate_threshold.py)
# --------------------------------------------------

STRONG_MATCH = float(os.getenv("STRONG_MATCH", 0.70))   # confident: answer from KB
WEAK_MATCH = float(os.getenv("WEAK_MATCH", 0.55))       # related: answer cautiously
MAX_CONTEXT = 3                                          # KB entries sent to the LLM

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "knowledge_base"
MISSING_LOG = LOG_DIR / "missing_queries.jsonl"
FEEDBACK_LOG = LOG_DIR / "feedback.jsonl"

UNAVAILABLE = (
    "I couldn't find verified information about that in my university "
    "database, so I don't want to guess. 🙏\n\n"
    "Please contact the university directly:\n"
    "- **Phone:** 0265-3093740 / 07573002444\n"
    "- **Email:** admission@gsfcuniversity.ac.in\n"
    "- **Website:** https://www.gsfcuniversity.ac.in/contact-us-304\n\n"
    "I've noted your question so the information can be added."
)

PARTIAL_NOTICE = (
    "ℹ️ I only found loosely related information, so this answer may be "
    "incomplete. Please confirm with the university office.\n\n"
)


# --------------------------------------------------
# Conversation memory (in RAM; fine for a prototype)
# --------------------------------------------------

MAX_SESSIONS = 500
MAX_MESSAGES = 6
SESSIONS: "OrderedDict[str, list]" = OrderedDict()


def get_history(session_id: str) -> list:
    return SESSIONS.get(session_id, [])


def remember(session_id: str, role: str, text: str):
    history = SESSIONS.setdefault(session_id, [])
    history.append({"role": role, "text": text})
    del history[:-MAX_MESSAGES]
    SESSIONS.move_to_end(session_id)
    while len(SESSIONS) > MAX_SESSIONS:
        SESSIONS.popitem(last=False)


ALIASES = [
    (re.compile(r"\b(uni|varsity|college|gsfcu|gsfc uni)\b", re.I), "GSFC University"),
    (re.compile(r"\bhod\b", re.I), "head of department"),
    (re.compile(r"\bdean\b", re.I), "dean head of school"),
    (re.compile(r"\bsem\b", re.I), "semester"),
]


def normalize_query(text: str) -> str:
    """Turn student short forms into the wording used in the knowledge base."""
    for pattern, replacement in ALIASES:
        text = pattern.sub(replacement, text)
    return re.sub(r"(GSFC University\s*){2,}", "GSFC University ", text).strip()


def retrieval_query(message: str, history: list) -> str:
    """Short follow-ups ("what about fees?") borrow the previous question."""
    previous = [h["text"] for h in history if h["role"] == "user"]
    if previous and len(message.split()) <= 6:
        return f"{previous[-1]} {message}"
    return message


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def _append_jsonl(path: Path, record: dict):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        print(f"[log] could not write {path.name}: {exc}")


def log_missing(question: str, results: list):
    _append_jsonl(MISSING_LOG, {
        "time": datetime.now().isoformat(timespec="seconds"),
        "question": question,
        "closest": [(r["title"], round(r["similarity"], 3)) for r in results],
    })


def build_sources(entries: list) -> list:
    seen, sources = set(), []
    for e in entries:
        key = e["source"] or e["title"]
        if key not in seen:
            seen.add(key)
            sources.append({"title": e["title"], "url": e["source"]})
    return sources


def reply(text, kind, session_id, entries=None, similarity=None):
    return {
        "response": text,
        "source": kind,                       # small_talk | knowledge_base | ...
        "session_id": session_id,
        "similarity": None if similarity is None else round(similarity, 3),
        "sources": build_sources(entries or []),
    }


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class FeedbackRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    response: str
    helpful: bool


# --------------------------------------------------
# Routes
# --------------------------------------------------

@app.get("/")
@app.get("/api/health")
def health():
    return {"status": "ok", "service": "GSFC University Student Chatbot",
            "active_sessions": len(SESSIONS)}


@app.post("/api/reload")
def reload_kb():
    """Re-read embeddings after running build_embeddings (no restart needed)."""
    reload_index()
    return {"status": "reloaded"}


@app.post("/api/feedback")
def feedback(req: FeedbackRequest):
    _append_jsonl(FEEDBACK_LOG, {
        "time": datetime.now().isoformat(timespec="seconds"),
        **req.model_dump(),
    })
    return {"status": "thanks"}


# Both paths work, so an existing frontend calling /api/career-chat keeps working
@app.post("/api/chat")
@app.post("/api/career-chat")
def chat(request: ChatRequest):
    session_id = request.session_id or uuid.uuid4().hex
    message = request.message.strip()
    history = get_history(session_id)

    # 0) Empty message
    if not message:
        return reply("Please type a question and I'll be happy to help. 😊",
                     "small_talk", session_id)

    # 1) Greetings / thanks / bye: instant, no API call, never logged
    talk = small_talk_reply(message)
    if talk:
        remember(session_id, "user", message)
        remember(session_id, "bot", talk)
        return reply(talk, "small_talk", session_id)

    # 2) Retrieve closest KB entries (short forms like "uni" expanded first)
    original_message = message
    message = normalize_query(message)
    try:
        results = search_kb(retrieval_query(message, history), top_k=MAX_CONTEXT)
    except Exception as exc:
        print(f"[rag] search failed: {type(exc).__name__}: {str(exc)[:120]}")
        return reply("Sorry, I couldn't search the university database right "
                     "now. Please try again in a few seconds.", "error", session_id)

    top = results[0]
    print("[rag] top matches:",
          [(r["title"], round(r["similarity"], 3)) for r in results])

    # 3a) Strong match: grounded answer
    if top["similarity"] >= STRONG_MATCH:
        used = [r for r in results if r["similarity"] >= WEAK_MATCH][:MAX_CONTEXT]
        answer = generate_answer(message, used, history)
        remember(session_id, "user", message)
        remember(session_id, "bot", answer)
        return reply(answer, "knowledge_base", session_id, used, top["similarity"])

    # 3b) Weak match: answer cautiously and log so staff can fill the gap
    if top["similarity"] >= WEAK_MATCH:
        log_missing(original_message, results)
        used = [r for r in results if r["similarity"] >= WEAK_MATCH][:MAX_CONTEXT]
        answer = PARTIAL_NOTICE + generate_answer(message, used, history, partial=True)
        remember(session_id, "user", message)
        remember(session_id, "bot", answer)
        return reply(answer, "knowledge_base_partial", session_id, used, top["similarity"])

    # 3c) No match: university question we lack, or off-topic?
    kind = classify_question(message)

    if kind is None:
        return reply("Sorry, I'm getting a lot of requests right now. "
                     "Please try again in a few seconds.", "error", session_id)

    if kind == "other":
        return reply(OFF_TOPIC, "off_topic", session_id)

    # University question but not in the KB: NO guessing. Point to the office.
    log_missing(original_message, results)
    remember(session_id, "user", message)
    remember(session_id, "bot", UNAVAILABLE)
    return reply(UNAVAILABLE, "unavailable", session_id, similarity=top["similarity"])