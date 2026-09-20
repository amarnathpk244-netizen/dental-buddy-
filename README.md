# Pocket Dentistry — Local Study Database

Student Mode now uses `study_database.db` for local study retrieval.

### Student Mode
- No Gemini/API calls
- Local curriculum
- Local topic search
- Local notes
- Local practice questions
- Local SQLite database

### Doctor Mode
Gemini API remains available for:
- X-ray AI
- Cephalometric assistance
- Soft-tissue clinical reasoning

## Important
The included database is a **starter structured knowledge base**, not a complete collection of every BDS textbook or verified KUHS previous-year paper. More verified content can be added to the same database without changing the app architecture.

Run:
```bash
pip install -r requirements.txt
streamlit run app.py
```
