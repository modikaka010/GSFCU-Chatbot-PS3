"""
small_talk.py - instant, hand-written replies for messages that are not
university questions (greetings, "what are you", thanks, bye, off-topic).

No API calls, so these never use your Gemini/Groq quota and are never
logged as "missing information".

Place in: backend/services/small_talk.py
"""

import re


EXAMPLES = (
    "- What programs does the School of ICT offer?\n"
    "- How can I contact the admission office?\n"
    "- Tell me about the IEEE Student Branch"
)

GREETING = (
    "Hi! 👋 I'm the GSFC University student assistant. I can help with "
    "programs and schools, admissions, exams, hostels, facilities, events, "
    "clubs, placements and contacts.\n\n"
    "Try asking:\n" + EXAMPLES
)

HOW_ARE_YOU = (
    "I'm doing great, thanks for asking! 😊 How can I help you with "
    "university information today?\n\n"
    "You could ask:\n" + EXAMPLES
)

ABOUT_ME = (
    "I'm an AI assistant for GSFC University students. I answer questions "
    "using the university's verified information (programs, admissions, "
    "exams, hostels, facilities, events, clubs, contacts) and I show where "
    "each answer comes from.\n\n"
    "If I don't have verified information, I'll say so instead of guessing, "
    "and point you to the right office.\n\n"
    "What would you like to know?"
)

THANKS = "You're welcome! 😊 Ask me anything else about the university whenever you like."

BYE = "Goodbye, and all the best with your studies! 🎓"

OFF_TOPIC = (
    "That's a little outside what I can help with, since I'm the GSFC "
    "University student assistant. 😊\n\n"
    "I'm happy to help with questions like:\n" + EXAMPLES + "\n\n"
    "What would you like to know about the university?"
)


# Patterns are matched against the WHOLE (cleaned, lowercase) message,
# so "hello I want to be a doctor" is NOT treated as small talk.
RULES = [
    (HOW_ARE_YOU, [
        r"how are you( doing| today)?",
        r"how r u",
        r"how are things",
        r"how is it going",
        r"how's it going",
        r"what's up",
        r"whats up",
        r"wassup",
        r"sup",
    ]),
    (ABOUT_ME, [
        r"(who|what) (are|r) (you|u)( exactly)?",
        r"(tell me about|introduce) (yourself|you)",
        r"(what is|what's|whats) your name",
        r"who (made|created|built|developed) (you|u)",
        r"are you (a )?(bot|ai|robot|human|real|chatbot)",
        r"what can you do",
        r"what do you do",
        r"how can you help( me)?",
        r"(can you )?help( me)?",
        r"what (can|do) (i|we) (ask|do) (you|here)",
    ]),
    (THANKS, [
        r"(thanks|thank you|thx|ty|thanks a lot|thank you so much|many thanks|shukriya|dhanyavad)",
        r"(ok |okay )?(thanks|thank you)( a lot| so much)?",
    ]),
    (BYE, [
        r"(bye|goodbye|good bye|see you|see ya|good night|tata|bye bye)",
    ]),
]

GREETING_ONLY = [
    r"(hi+|hello+|hey+|hii+|hola|yo|namaste|namaskar|hi there|hello there|hey there)",
    r"good (morning|afternoon|evening)",
]

GREETING_PREFIX = re.compile(r"^(hi+|hello+|hey+|hii+|hola|namaste|namaskar)\s+")


def _clean(message: str) -> str:
    text = re.sub(r"[^\w\s']", " ", message.lower())
    return re.sub(r"\s+", " ", text).strip()


def _matches(patterns, text: str) -> bool:
    return any(re.fullmatch(p, text) for p in patterns)


def small_talk_reply(message: str):
    """Return a ready-made reply if the message is small talk, else None."""
    text = _clean(message)

    # Long messages are real questions, not small talk
    if not text or len(text.split()) > 8:
        return None

    if _matches(GREETING_ONLY, text):
        return GREETING

    # Allow a leading greeting: "hello how are you", "hi what are you"
    rest = GREETING_PREFIX.sub("", text, count=1)

    for reply, patterns in RULES:
        if _matches(patterns, rest) or _matches(patterns, text):
            return reply

    return None