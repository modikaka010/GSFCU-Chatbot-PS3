"""
calibrate_threshold.py - find good STRONG_MATCH / WEAK_MATCH values.

Run from inside backend/:   python calibrate_threshold.py
Edit both lists so they match what is REALLY in gsfcu_kb.json.
"""

import time

from services.rag_service import search_kb

# Questions the KB DOES answer
IN_KB = [
    "which schools does the university have",
    "how do I contact the admission office",
    "what hostels are available",
    "tell me about the IEEE student branch",
    "which companies recruit from the university",
]

# University-related questions the KB does NOT answer, plus off-topic ones
NOT_IN_KB = [
    "what is today's canteen menu",
    "who is the head of the physics department",
    "who won the cricket world cup",
    "how do I cook pasta",
    "what is the weather today",
]


def run(label, questions):
    print(f"\n--- {label} ---")
    scores = []
    for q in questions:
        top = search_kb(q, top_k=1)[0]
        scores.append(top["similarity"])
        print(f"{top['similarity']:.3f}  {top['title'][:34]:<34}  <- {q}")
        time.sleep(1)
    return scores


in_scores = run("IN knowledge base", IN_KB)
out_scores = run("NOT in knowledge base", NOT_IN_KB)

print("\nLowest 'in KB' score  :", round(min(in_scores), 3))
print("Highest 'not in KB'   :", round(max(out_scores), 3))
print("Set STRONG_MATCH just below the lowest 'in KB' score,")
print("and WEAK_MATCH a bit above the highest 'not in KB' score.")
print("Then add them to .env as STRONG_MATCH=... and WEAK_MATCH=...")