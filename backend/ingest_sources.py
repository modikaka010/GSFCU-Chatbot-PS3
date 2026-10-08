"""
ingest_sources.py - download GSFC University web pages + PDFs and turn them
into knowledge-base entries (no LLM involved, so nothing gets invented).

Place in: backend/ingest_sources.py
Run from the PROJECT ROOT:   python backend/ingest_sources.py

What it does
  1. Downloads every page / PDF in SOURCES below (add more any time).
  2. Removes menu/footer lines that repeat on many pages.
  3. Cuts the text into ~150-word entries and tags each with a category,
     title and source URL.
  4. Merges them into knowledge_base/documents/gsfcu_kb.json.
     - Entries whose id starts with "auto-" are replaced on every run.
     - Entries you wrote by hand (any other id) are never touched.
  5. Saves the raw text of each source to knowledge_base/raw/ so you can
     check what was extracted.

Then:  python -m backend.services.build_embeddings
"""

import io
import json
import re
import time
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parent.parent
KB_PATH = PROJECT_ROOT / "knowledge_base" / "documents" / "gsfcu_kb.json"
RAW_DIR = PROJECT_ROOT / "knowledge_base" / "raw"

B = "https://www.gsfcuniversity.ac.in"
U = B + "/upload/file/"

# (id, url, category, title)
# Categories follow the problem statement:
#  procedures, academics, events, student-life, facilities, exams,
#  services, contact, faq, ieee, about, placements
SOURCES = [
    # --- About
    ("about", B + "/about-gsfcu", "about", "About GSFC University"),
    ("vision", B + "/vision-and-mission", "about", "Vision and mission of GSFC University"),
    ("usp", B + "/usp", "about", "Unique selling points of GSFC University"),
    ("recognition", B + "/gsfcu-recognition-and-approval", "about", "Recognition and approval of GSFC University"),

    # --- Department and course information
    ("schools", B + "/schools", "academics", "Schools at GSFC University"),
    ("prog-btech-cse", "https://gsfcuniversity.ac.in/btech-computer-science-and-engineering-program", "academics", "B.Tech. Computer Science and Engineering"),
    ("prog-btech-ece", B + "/btech_ece_program", "academics", "B.Tech. Electronics and Communication Engineering"),
    ("prog-bca", B + "/bca-computer-application", "academics", "Bachelor in Computer Application (BCA)"),
    ("prog-mtech-cse", B + "/mtech-computer-science-and-engineering-program", "academics", "M.Tech. Computer Science and Engineering"),
    ("prog-btech-chem", B + "/btech-chemical-engineering-program", "academics", "B.Tech. Chemical Engineering"),
    ("prog-btech-fehs", B + "/btech-fire-and-safety-engineering-program", "academics", "B.Tech. Fire and Environment, Health, Safety"),
    ("prog-pgd-safety", B + "/pg-diploma-industrial-safety", "academics", "PG Diploma in Industrial Safety"),
    ("prog-bsc-chem", B + "/bsc-hons-chemistry", "academics", "B.Sc. (Hons.) Chemistry"),
    ("prog-msc-ds", B + "/msc-data-science", "academics", "M.Sc. Data Science"),
    ("prog-bsc-biotech", "https://gsfcuniversity.ac.in/bsc-hons-biotechnology", "academics", "B.Sc. (Hons.) Biotechnology"),
    ("prog-bsc-micro", B + "/bsc-hons-microbiology", "academics", "B.Sc. (Hons.) Microbiology"),
    ("prog-bba", "https://gsfcuniversity.ac.in/bachelor-of-business-administration-bba", "academics", "BBA General"),
    ("prog-bba-ba", B + "/bba-business-analytics", "academics", "BBA Business Analytics"),
    ("prog-bcom", B + "/bachelor-of-commerce-bcom", "academics", "B.Com."),
    ("prog-mba", B + "/masters-of-business-administration-mba", "academics", "MBA"),
    ("cbcs", "https://gsfcuniversity.ac.in/cbcs", "academics", "Choice Based Credit System (CBCS)"),
    ("internship", B + "/internship", "academics", "Internship"),
    ("minor-degree", B + "/minor-degree-in-core-engineering-program", "academics", "Minor degree program in core engineering"),

    # --- Academic and administrative procedures
    ("apply", B + "/apply-for-admission", "procedures", "How to apply for admission"),
    ("pdf-fees", U + "Fee Structure_AY 2026-27_21.09.2026.pdf", "procedures", "Fee structure AY 2026-27"),
    ("pdf-refund", B + "/upload/ckfiles/Policy-AdmissionWithdrawalANDFeeRefund_%20AY2026-27.pdf", "procedures", "Admission withdrawal and fee refund policy AY 2026-27"),
    ("pdf-calendar", U + "AcademicCalender_Odd-AY-'2026-27.pdf", "procedures", "Academic calendar odd semester AY 2026-27"),

    # --- Examination-related information
    ("exam-policies", "https://gsfcuniversity.ac.in/examinationpolicies", "exams", "Examination policies"),
    ("exam-timetable", "https://gsfcuniversity.ac.in/examtimetable", "exams", "Exam time table"),
    ("exam-contact", "https://gsfcuniversity.ac.in/contactexamcell", "exams", "Exam cell contact"),
    ("onei", B + "/onei", "exams", "Online Exam Initiative (ONEI)"),

    # --- General FAQs (university + program wise)
    ("pdf-faq-cse", U + "BTech CSE-FAQs 2025.pdf", "faq", "FAQs B.Tech. Computer Science and Engineering"),
    ("pdf-faq-bca", U + "FAQ_2025_BCA.pdf", "faq", "FAQs BCA"),
    ("pdf-faq-chem", U + "Chemical FAQ_Oct2025.pdf", "faq", "FAQs B.Tech. Chemical Engineering"),
    ("pdf-faq-fehs", U + "BTech F&EHS- FAQs.pdf", "faq", "FAQs B.Tech. Fire and EHS"),
    ("pdf-faq-bba", U + "BBA FAQ 22-06-21.pdf", "faq", "FAQs BBA"),

    # --- Campus facilities
    ("amenities", B + "/amenities", "facilities", "Campus amenities"),
    ("facilities", "https://gsfcuniversity.ac.in/view_all/3781", "facilities", "Campus facilities"),
    ("hostel-girls", B + "/girl-s-hostel", "facilities", "Girls hostel"),
    ("hostel-boys", B + "/boy-s-hostel", "facilities", "Boys hostel"),
    ("transport", B + "/transportation", "facilities", "Transportation"),
    ("campus", B + "/gsfcu-campus", "facilities", "GSFCU campus"),
    ("library", "https://gsfcuniversity.ac.in/library/all/15", "facilities", "Library"),

    # --- Student clubs and activities
    ("clubs", B + "/student-managed-clubs", "student-life", "Student managed clubs"),
    ("chapters", B + "/student-managed-chapters", "student-life", "Student managed chapters"),
    ("sports", B + "/sports", "student-life", "Sports"),
    ("pinups", "https://gsfcuniversity.ac.in/pinups", "student-life", "PINUPS"),
    ("ncc", B + "/nationalcadetcorps-ncc", "student-life", "National Cadet Corps (NCC)"),
    ("vichar", B + "/vichar-vimarsh-gsfcu", "student-life", "Vichar Vimarsh"),
    ("vartalap", B + "/vartalap-gsfcu", "student-life", "Vartalap"),

    # --- Student services
    ("students-corner", B + "/students-corner", "services", "Students' corner"),
    ("placements", B + "/campus-placement", "placements", "Campus placements"),
    ("committees", B + "/committees", "services", "University committees"),
    ("ombudsperson", B + "/gsfcu-ombudsperson", "services", "Ombudsperson"),
    ("suggestion", B + "/suggestion", "services", "Suggestion"),

    # --- University events
    ("events", B + "/eventsgallery", "events", "Upcoming events"),
    ("news", B + "/all_latestNews", "events", "Latest news and events"),
    ("press", B + "/press-release", "events", "Press releases"),

    # --- Contact information
    ("contact", B + "/contact-us-304", "contact", "Contact GSFC University"),

    # --- IEEE Student Branch
    ("pdf-ieee", U + "Latest News.pdf", "ieee", "IEEE Student Branch at GSFC University"),
]

WORDS_PER_CHUNK = 150
MAX_WORDS = 230
MIN_WORDS = 25
MAX_CHUNKS_PER_SOURCE = 12
BOILERPLATE_SHARE = 0.4        # a line on >40% of pages is menu/footer junk
HEADERS = {"User-Agent": "Mozilla/5.0 (GSFCU-student-chatbot project)"}


def fix_url(url: str) -> str:
    return quote(url, safe=":/%")


def fetch(url: str):
    """Returns ('pdf'|'html', bytes) or None."""
    try:
        r = requests.get(fix_url(url), headers=HEADERS, timeout=40)
        r.raise_for_status()
    except Exception as exc:
        print(f"  x download failed: {type(exc).__name__}: {str(exc)[:80]}")
        return None
    is_pdf = url.lower().endswith(".pdf") or "pdf" in r.headers.get("content-type", "")
    return ("pdf" if is_pdf else "html"), r.content


def pdf_to_lines(data: bytes) -> list:
    reader = PdfReader(io.BytesIO(data))
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    return clean_lines(text.splitlines())


def html_to_lines(data: bytes) -> list:
    soup = BeautifulSoup(data, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "form",
                     "noscript", "aside", "iframe", "svg"]):
        tag.decompose()
    return clean_lines(soup.get_text("\n", strip=True).splitlines())


def clean_lines(lines: list) -> list:
    out = []
    for line in lines:
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) < 3 or line.lower().startswith(("javascript:", "http")):
            continue
        out.append(line)
    return out


def chunk_lines(lines: list) -> list:
    """Group lines into chunks of roughly WORDS_PER_CHUNK words."""
    chunks, current, count = [], [], 0
    for line in lines:
        words = len(line.split())
        if current and count + words > MAX_WORDS:
            chunks.append(" ".join(current))
            current, count = [], 0
        current.append(line)
        count += words
        if count >= WORDS_PER_CHUNK and line.endswith((".", ":", ")", "?")):
            chunks.append(" ".join(current))
            current, count = [], 0
    if current:
        chunks.append(" ".join(current))
    return [c for c in chunks if len(c.split()) >= MIN_WORDS]


def main():
    today = date.today().isoformat()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # ---- 1) download everything
    fetched = {}                       # id -> (kind, lines)
    for sid, url, cat, title in SOURCES:
        print(f"Downloading {sid} ...")
        got = fetch(url)
        if not got:
            continue
        kind, data = got
        try:
            lines = pdf_to_lines(data) if kind == "pdf" else html_to_lines(data)
        except Exception as exc:
            print(f"  x could not read: {type(exc).__name__}: {str(exc)[:80]}")
            continue
        if not lines:
            print("  ! no text found (scanned PDF?). Type this one in by hand.")
            continue
        fetched[sid] = (kind, lines)
        time.sleep(0.7)                # be polite to the university server

    # ---- 2) remove menu/footer lines repeated across many HTML pages
    html_pages = [lines for kind, lines in fetched.values() if kind == "html"]
    freq = Counter()
    for lines in html_pages:
        freq.update(set(lines))
    limit = max(3, int(len(html_pages) * BOILERPLATE_SHARE))
    boiler = {l for l, n in freq.items() if n > limit} if len(html_pages) >= 5 else set()
    print(f"\nRemoved {len(boiler)} repeated menu/footer lines.")

    # ---- 3) chunk -> entries
    entries, seen_text = [], set()
    for sid, url, cat, title in SOURCES:
        if sid not in fetched:
            continue
        kind, lines = fetched[sid]
        if kind == "html":
            lines = [l for l in lines if l not in boiler]
        (RAW_DIR / f"{sid}.txt").write_text("\n".join(lines), encoding="utf-8")

        chunks = chunk_lines(lines)[:MAX_CHUNKS_PER_SOURCE]
        for n, text in enumerate(chunks, start=1):
            if text in seen_text:
                continue
            seen_text.add(text)
            entries.append({
                "id": f"auto-{sid}-{n}",
                "category": cat,
                "title": title if len(chunks) == 1 else f"{title} (part {n})",
                "content": text,
                "source": fix_url(url),
                "last_updated": today,
            })
        print(f"  {sid:<18} {len(chunks)} entries")

    # ---- 4) merge with hand-written entries
    hand = []
    if KB_PATH.exists():
        old = json.loads(KB_PATH.read_text(encoding="utf-8"))
        hand = [e for e in old if not e["id"].startswith("auto-")]
        (KB_PATH.parent / "gsfcu_kb.backup.json").write_text(
            json.dumps(old, indent=2, ensure_ascii=False), encoding="utf-8")

    merged = hand + entries
    KB_PATH.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nKept {len(hand)} hand-written + added {len(entries)} auto entries "
          f"= {len(merged)} total.")
    print(f"Raw text saved in {RAW_DIR}")
    missing = [s[0] for s in SOURCES if s[0] not in fetched]
    if missing:
        print("Not downloaded (check URL / internet):", ", ".join(missing))
    print("\nNext: python -m backend.services.build_embeddings")


if __name__ == "__main__":
    main()