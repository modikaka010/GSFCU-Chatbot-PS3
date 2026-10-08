import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai


project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(project_root / ".env")

gemini_key = os.getenv("GEMINI_API_KEY")
groq_key = os.getenv("GROQ_API_KEY")

if not gemini_key and not groq_key:
    raise ValueError("Set GEMINI_API_KEY and/or GROQ_API_KEY in .env")

GROQ_MODEL = "openai/gpt-oss-120b"
GEMINI_MODEL = "gemini-3.6-flash"

FRIENDLY_ERROR = (
    "Sorry, I'm getting a lot of requests right now. "
    "Please try again in a few seconds."
)

gemini_client = genai.Client(api_key=gemini_key) if gemini_key else None

groq_client = None
if groq_key:
    from groq import Groq
    groq_client = Groq(api_key=groq_key)


# --------------------------------------------------
# Provider calls (unchanged from your version)
# --------------------------------------------------

def _groq(prompt: str) -> str:
    resp = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,          # lower = fewer invented details
        max_tokens=1500,
        reasoning_effort="low",
    )
    return resp.choices[0].message.content


def _gemini(prompt: str) -> str:
    interaction = gemini_client.interactions.create(
        model=GEMINI_MODEL,
        input=prompt
    )
    return interaction.output_text


PROVIDERS = []
if groq_client:
    PROVIDERS.append(("groq", _groq))
if gemini_client:
    PROVIDERS.append(("gemini", _gemini))


def _generate(prompt: str) -> str:
    """Try each provider (2 quick attempts). Never raises."""
    for name, call in PROVIDERS:
        for attempt in range(2):
            try:
                return call(prompt)
            except Exception as exc:
                print(f"[llm] {name} attempt {attempt + 1} failed: "
                      f"{type(exc).__name__}: {str(exc)[:100]}")
                time.sleep(1.5)
    return FRIENDLY_ERROR


# --------------------------------------------------
# Public functions
# --------------------------------------------------

def generate_answer(question: str, contexts: list, history: list = None,
                    partial: bool = False) -> str:
    """
    Grounded answer for a university question.
    contexts = retrieved KB entries (dicts with 'title' and 'text').
    history  = last few turns [{"role": "user"|"bot", "text": ...}].
    partial  = True when the match is only moderately close.
    """

    context_block = "\n\n".join(
        f"[Source {i}] {c['title']}\n{c['text']}"
        for i, c in enumerate(contexts, start=1)
    )

    history_block = ""
    if history:
        lines = [f"{'Student' if h['role'] == 'user' else 'Assistant'}: {h['text'][:300]}"
                 for h in history[-4:]]
        history_block = "RECENT CONVERSATION (for follow-up questions only):\n" + \
            "\n".join(lines) + "\n\n"

    caution = ""
    if partial:
        caution = (
            "- The sources below may only be loosely related. If they do not "
            "directly answer the question, say you don't have that detail.\n"
        )

    prompt = f"""
You are the student information assistant for GSFC University, Vadodara.
You reply in a chat window.

{history_block}VERIFIED UNIVERSITY INFORMATION:
-----------------
{context_block}
-----------------

STUDENT QUESTION:
{question}

RULES:
- Answer ONLY from the verified information above. Never add fees, dates,
  deadlines, names, phone numbers, email addresses, links, or rules that are
  not written in it.
- If the information does not cover part of the question, say clearly:
  "I don't have that detail" and suggest contacting the relevant university
  office. Do not guess.
{caution}- Answer only what was asked. Keep it under 120 words.
- Do not mention "Source 1" or the word "context". The app shows sources itself.

FORMAT (Markdown): one short direct sentence, then at most 4 bullets starting
with "-". Use only bold text and "-" bullets. No headings, tables, or italics.
End with one short follow-up offer only if it is closely related.
"""
    return _generate(prompt)


def classify_question(question: str):
    """
    Returns "university", "other", or None if the AI could not be reached.
    Used only when retrieval finds no good match.
    """

    prompt = f"""
Is this message from a student asking about university life: admissions,
fees, programs, departments, exams, academic calendar, hostels, transport,
facilities, events, clubs, placements, contacts, or campus services?

Message: "{question}"

Reply with exactly one word: UNIVERSITY or OTHER.
"""
    answer = _generate(prompt)
    if answer == FRIENDLY_ERROR:
        return None
    return "university" if "UNIVERSITY" in answer.upper() else "other"