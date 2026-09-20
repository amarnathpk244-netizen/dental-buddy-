import sqlite3, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "database", "dental_buddy.sqlite")

def search(query, limit=10):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute("""
        SELECT c.id, d.title AS document, d.subject,
               c.heading, c.page_start, c.page_end, c.text
        FROM chunks_fts f
        JOIN chunks c ON c.id = f.rowid
        JOIN documents d ON d.id = c.document_id
        WHERE chunks_fts MATCH ?
        LIMIT ?
    """, (query, limit)).fetchall()
    con.close()
    return rows

if __name__ == "__main__":
    q = " ".join(sys.argv[1:]).strip()
    if not q:
        print("Usage: python scripts/search_database.py \"lichen planus\"")
        raise SystemExit
    for r in search(q):
        print(f"\n[{r['subject']}] {r['document']} | p.{r['page_start']}")
        print(r['heading'])
        print(r['text'][:1000])
