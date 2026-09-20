# Dental Buddy — PDF to SQLite Knowledge Base

## Folder structure

```text
Dental_Buddy_PDF_Importer/
├── pdfs/
│   ├── Oral_Medicine.pdf
│   ├── Orthodontics.pdf
│   └── Prosthodontics.pdf
├── data/
│   └── schema.sql
├── scripts/
│   ├── import_pdfs.py
│   └── search_database.py
└── output/
    └── dental_buddy.db
```

## Install

```bash
pip install pymupdf
```

Optional OCR for scanned PDFs:

```bash
pip install pytesseract pillow
```

Tesseract OCR itself must also be installed on the computer if `--ocr` is used.

## Import all PDFs

Put your books in `pdfs/`, then:

```bash
python scripts/import_pdfs.py
```

For scanned/image-only books:

```bash
python scripts/import_pdfs.py --ocr
```

Import one book:

```bash
python scripts/import_pdfs.py --pdf "pdfs/Oral Medicine.pdf" --ocr
```

## Search

```bash
python scripts/search_database.py "lichen planus"
```

## Database design

The database stores:

- books
- every PDF page
- detected chapters
- detected topics/subtopics
- MCQ/case/reference records
- FTS5 full-text indexes

Every extracted item retains a source PDF page so Dental Buddy can show where the information came from.

## Important

This importer does not silently invent missing textbook content. If a scanned page cannot be read, it remains available as a source page and can be reprocessed with OCR.

For high-quality textbook databases, review the automatically detected chapter/topic boundaries after import.
