#!/usr/bin/env python3
"""
Dental Buddy PDF -> SQLite importer

Usage:
    python scripts/pdf_to_database.py
    python scripts/pdf_to_database.py --pdf "pdfs/OMFS/book.pdf"

Dependencies:
    pip install pypdf

The importer:
1. Finds PDFs in the pdfs/ folder (or one supplied PDF).
2. Extracts page text.
3. Stores pages and searchable chunks.
4. Detects likely chapter/section headings using common dental-book patterns.
5. Builds SQLite FTS5 indexes.
6. Avoids duplicate imports by filename.
"""

import argparse
import os
import re
import sqlite3
from datetime import datetime

try:
    from pypdf import PdfReader
except ImportError:
    raise SystemExit("Install pypdf first: pip install pypdf")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "database", "dental_buddy.sqlite")
PDF_ROOT = os.path.join(BASE, "pdfs")

SUBJECT_MAP = {
    "Oral_Medicine_Radiology": "Oral Medicine & Radiology",
    "Orthodontics": "Orthodontics",
    "Prosthodontics": "Prosthodontics",
    "OMFS": "Oral & Maxillofacial Surgery",
    "Pedodontics": "Pedodontics",
    "Periodontics": "Periodontics",
    "Conservative_Endodontics": "Conservative Dentistry & Endodontics",
    "Public_Health_Dentistry": "Public Health Dentistry",
    "General": "General Dentistry",
}

def clean_text(text):
    if not text:
        return ""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    return text.strip()

def subject_from_path(pdf_path):
    rel = os.path.relpath(pdf_path, PDF_ROOT)
    top = rel.split(os.sep)[0]
    return SUBJECT_MAP.get(top, top.replace("_", " "))

def looks_like_heading(line):
    line = clean_text(line)
    if not line or len(line) < 3 or len(line) > 180:
        return False

    # Common textbook chapter patterns
    patterns = [
        r"^(chapter|unit|module|part)\s+([0-9ivxlcdm]+|[a-z])\b",
        r"^\d+(\.\d+)*[\)\.\-:]\s+\S+",
        r"^(contents|introduction|conclusion|references|bibliography|appendix)$",
    ]
    if any(re.match(p, line, re.I) for p in patterns):
        return True

    words = line.split()
    if len(words) <= 12 and line.upper() == line and any(c.isalpha() for c in line):
        return True

    return False

def heading_number_title(line):
    line = clean_text(line)
    m = re.match(r"^(chapter|unit|module|part)\s+([0-9ivxlcdm]+|[a-z]+)\s*[:.\-]?\s*(.*)$", line, re.I)
    if m:
        return m.group(2), m.group(3).strip() or line
    m = re.match(r"^(\d+(?:\.\d+)*)[\)\.\-:]\s+(.+)$", line)
    if m:
        return m.group(1), m.group(2).strip()
    return None, line

def chunk_text(text, max_chars=5000):
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, current = [], ""
    for p in paragraphs:
        if len(current) + len(p) + 2 <= max_chars:
            current = (current + "\n\n" + p).strip()
        else:
            if current:
                chunks.append(current)
            current = p
    if current:
        chunks.append(current)
    return chunks

def ensure_schema(conn):
    schema_path = os.path.join(BASE, "database", "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

def import_pdf(conn, pdf_path):
    pdf_path = os.path.abspath(pdf_path)
    filename = os.path.basename(pdf_path)
    subject = subject_from_path(pdf_path)

    existing = conn.execute(
        "SELECT id FROM documents WHERE filename=?", (filename,)
    ).fetchone()

    if existing:
        conn.execute("DELETE FROM documents WHERE id=?", (existing[0],))
        conn.commit()

    reader = PdfReader(pdf_path)
    page_texts = []
    for page in reader.pages:
        try:
            page_texts.append(clean_text(page.extract_text() or ""))
        except Exception:
            page_texts.append("")

    title = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ")
    now = datetime.now().isoformat(timespec="seconds")

    cur = conn.execute("""
        INSERT INTO documents
        (filename, subject, title, source_type, imported_at, page_count)
        VALUES (?,?,?,?,?,?)
    """, (filename, subject, title, "user_uploaded_pdf", now, len(page_texts)))
    doc_id = cur.lastrowid

    for i, text in enumerate(page_texts, 1):
        conn.execute(
            "INSERT INTO pages(document_id,page_number,text) VALUES (?,?,?)",
            (doc_id, i, text)
        )

    # Detect headings and create chapter ranges.
    detected = []
    for i, text in enumerate(page_texts, 1):
        for line in text.splitlines():
            line = clean_text(line)
            if looks_like_heading(line):
                num, title_line = heading_number_title(line)
                detected.append((i, num, title_line))

    # De-duplicate headings appearing in headers/footers.
    unique = []
    seen = set()
    for item in detected:
        key = (item[0], item[1], item[2].lower())
        if key not in seen:
            unique.append(item)
            seen.add(key)

    # Only create chapter records when headings are reasonably spaced.
    for idx, (page, num, heading) in enumerate(unique):
        next_page = unique[idx + 1][0] if idx + 1 < len(unique) else len(page_texts) + 1
        if next_page <= page:
            continue
        # Ignore tiny repeated headings.
        if idx > 0 and page == unique[idx - 1][0] and heading.lower() == unique[idx - 1][2].lower():
            continue
        conn.execute("""
            INSERT INTO chapters(document_id,chapter_number,title,start_page,end_page)
            VALUES (?,?,?,?,?)
        """, (doc_id, num, heading, page, next_page - 1))

    conn.commit()

    # Build chunks page-by-page, with chapter association.
    chapters = conn.execute("""
        SELECT id,title,start_page,end_page
        FROM chapters WHERE document_id=? ORDER BY start_page
    """, (doc_id,)).fetchall()

    def chapter_for_page(page_no):
        for ch in chapters:
            if ch[2] <= page_no <= ch[3]:
                return ch
        return None

    for page_no, text in enumerate(page_texts, 1):
        if not text:
            continue
        ch = chapter_for_page(page_no)
        heading = ch[1] if ch else ""
        for chunk in chunk_text(text):
            conn.execute("""
                INSERT INTO chunks(document_id,chapter_id,page_start,page_end,heading,text)
                VALUES (?,?,?,?,?,?)
            """, (doc_id, ch[0] if ch else None, page_no, page_no, heading, chunk))

    conn.commit()

    # Rebuild FTS indexes.
    conn.execute("INSERT INTO pages_fts(pages_fts) VALUES('rebuild')")
    conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
    conn.commit()

    print(f"Imported: {filename} | {subject} | {len(page_texts)} pages")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", help="Import one PDF instead of scanning pdfs/")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(DB), exist_ok=True)
    conn = sqlite3.connect(DB)
    ensure_schema(conn)

    if args.pdf:
        paths = [os.path.abspath(args.pdf)]
    else:
        paths = []
        for root, _, files in os.walk(PDF_ROOT):
            for name in files:
                if name.lower().endswith(".pdf"):
                    paths.append(os.path.join(root, name))

    if not paths:
        print("No PDFs found. Put textbooks into the pdfs/<subject>/ folders.")
        return

    for pdf in sorted(paths):
        try:
            import_pdf(conn, pdf)
        except Exception as e:
            print(f"FAILED: {pdf}\n  {e}")

    conn.close()
    print("Database ready:", DB)

if __name__ == "__main__":
    main()
