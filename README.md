# Dental Buddy — PDF Knowledge Database

## What this package does

Drop your legally usable dental PDFs into the subject folders. The importer extracts page text, detects likely chapters/headings, creates searchable chunks, and stores everything in SQLite with FTS5.

### Folder structure

pdfs/
- Oral_Medicine_Radiology/
- Orthodontics/
- Prosthodontics/
- OMFS/
- Pedodontics/
- Periodontics/
- Conservative_Endodontics/
- Public_Health_Dentistry/
- General/

## 1. Install

```bash
pip install pypdf
```

## 2. Add PDFs

Example:

```text
pdfs/Oral_Medicine_Radiology/Oral_Medicine_Textbook.pdf
pdfs/Orthodontics/MBT.pdf
pdfs/OMFS/OMFS_Textbook.pdf
```

Only use PDFs you are allowed to process/store in your application.

## 3. Import everything

```bash
python scripts/pdf_to_database.py
```

Or import one PDF:

```bash
python scripts/pdf_to_database.py --pdf "pdfs/OMFS/OMFS_Textbook.pdf"
```

## 4. Test search

```bash
python scripts/search_database.py "lichen planus"
python scripts/search_database.py "deep bite"
python scripts/search_database.py "complete denture"
```

## Database tables

- `documents` — PDF metadata
- `pages` — page-level extracted text
- `chapters` — detected chapter/section headings
- `chunks` — RAG-ready text chunks with page references
- `topics` — BDS topic index
- `chunks_fts` — full-text search index
- `pages_fts` — page full-text search index

## How Dental Buddy can use it

Student asks a question → SQLite FTS search → retrieve relevant chunks → send only those chunks to the AI → generate an answer → display textbook name + page number.

This reduces unnecessary API calls and makes references traceable.

## Important limitation

PDF extraction is text-based. Scanned/image-only PDFs may need OCR before they can be searched accurately. Heading detection is heuristic, so it should be checked for each textbook.
