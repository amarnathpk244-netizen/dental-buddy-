import os
import re
import html
import json
import base64
import sqlite3
from datetime import date, datetime
from io import BytesIO
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import streamlit as st

# ============================================================
# POCKET DENTISTRY
# DATABASE-FIRST + OPTIONAL CLOUDFLARE AI FALLBACK
# Gemini removed.
# ============================================================

st.set_page_config(
    page_title="Pocket Dentistry",
    page_icon="🦷",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DAILY_ANALYSIS_LIMIT = 3
APP_DB = "pocket_dentistry.db"
LOCAL_DB = "study_database.db"
DEFAULT_CF_MODEL = "@cf/google/gemma-4-26b-a4b-it"

# ============================================================
# V12 CURRICULUM
# ============================================================

V12_CURRICULUM = {
    "First Year": ["Dental Anatomy & Dental Histology", "Head & Neck Anatomy"],
    "Second Year": ["General Pathology", "General Microbiology", "Pharmacology"],
    "Third Year": ["Oral Pathology", "General Medicine", "General Surgery"],
    "Final Year / Part I": ["Oral Medicine & Radiology", "Periodontics", "Public Health Dentistry", "Orthodontics"],
    "Final Year / Part II": ["Oral & Maxillofacial Surgery", "Pedodontics", "Prosthodontics", "Conservative Dentistry & Endodontics"],
}

V12_SECTIONS = {
    "Dental Anatomy & Dental Histology": ["Theory","Histology Slides","Tooth Carving","Spotters","MCQs","Practical Exam"],
    "Head & Neck Anatomy": ["Histology","Dissection","Specimen Demonstration","Spotters","MCQs","Practical Exam"],
    "General Pathology": ["Lecture Demonstrations","Histopathology Slides","Specimens","Student Practicals","Spotters","MCQs","Practical Exam"],
    "General Microbiology": ["Organisms","Practical Slides","Culture Media","Animals","Instruments","Spotters","MCQs","Practical Exam"],
    "Pharmacology": ["Dispensing Pharmacy","Dosage Forms","Prescription Writing","Dental Prescriptions","Spotters","MCQs","Practical Exam"],
    "Oral Pathology": ["Hard Tissue Anomalies","Gross Specimens","Histopathology","Forensic Odontology","Spotters","MCQs","University Exam"],
    "General Medicine": ["Theory","Clinical Training","Clinical Examination","MCQs","University Exam"],
    "General Surgery": ["Theory","Clinical Training","Clinical Examination","MCQs","University Exam"],
    "Oral Medicine & Radiology": ["Oral Medicine","Radiology","Clinical Training","Spotters","MCQs","Practical Exam","University Exam"],
    "Periodontics": ["Theory","Clinical Tutorials","Demonstrations","Clinical Requirements","Spotters","MCQs","Practical Exam","University Exam"],
    "Public Health Dentistry": ["Public Health","Dental Public Health","Research & Statistics","Practice Management","Palliative Care","Field Programme","Preventive Dentistry","Spotters","University Exam"],
    "Orthodontics": ["Third Year Theory","Final Year Part I Theory","Clinical Training","Desirable Exercises","Spotters","MCQs","Practical Exam","University Exam"],
    "Oral & Maxillofacial Surgery": ["Third Year Theory","Final Year Part I Theory","Final Year Part II Theory","Clinical Requirements","Spotters","MCQs","University Exam"],
    "Pedodontics": ["Third Year Theory","Final Year Part I Theory","Final Year Part II Theory","Clinical Requirements","Assignments","Spotters","MCQs","Practical Exam","University Exam"],
    "Prosthodontics": ["Complete Denture","Removable Partial Prosthodontics","Fixed Partial Prosthodontics","Miscellaneous Prosthodontics","Clinical Requirements","Spotters","MCQs","Practical Exam","University Exam"],
    "Conservative Dentistry & Endodontics": ["Conservative Dentistry","Endodontics","Clinical Requirements","Spotters","MCQs","Practical Exam","University Exam"],
}

TEXTBOOK_LIBRARY = {
    "General Human Anatomy": {"BD Chaurasia's Human Anatomy (Vol 1-3)": ["General Anatomy & Introduction","Upper Limb and Thorax","Abdomen and Pelvis","Head, Neck and Brain","Lower Limb","Embryology & General Histology","Osteology"]},
    "General Human Physiology": {"Guyton and Hall Textbook of Medical Physiology": ["General Physiology & Cell Physiology","Nerve and Muscle","Heart and Circulation","The Body Fluids and Kidneys","Respiration","Nervous System","Gastrointestinal Physiology","Endocrinology"]},
    "General Pathology": {"Robbins & Cotran Pathologic Basis of Disease": ["Cell Injury","Inflammation and Repair","Hemodynamics","Neoplasia","Genetic Diseases"]},
    "Oral Pathology": {"Shafer's Textbook of Oral Pathology": ["Developmental Disturbances","Dental Caries","Pulp Diseases","Periodontal Diseases","Cysts","Odontogenic Tumors"]},
    "Oral Medicine & Radiology": {"Burket's Oral Medicine": ["Patient Evaluation","Oral Mucosal Diseases","Ulcers","White Lesions","Salivary Gland Disorders"]},
    "Periodontics": {"Carranza's Clinical Periodontology": ["Periodontal Anatomy","Gingivitis","Periodontitis","Scaling and Root Planing","Periodontal Surgery"]},
    "Conservative Dentistry & Endodontics": {"Cohen's Pathways of the Pulp": ["Pulp Biology","Diagnosis","Root Canal Anatomy","Cleaning and Shaping","Obturation"]},
    "Prosthodontics": {"Nallaswamy - Textbook of Prosthodontics": ["Complete Dentures","Impression Making","Jaw Relations","Removable Partial Dentures","Fixed Prosthodontics"]},
    "Orthodontics": {"Proffit - Contemporary Orthodontics": ["Growth and Development","Malocclusion","Diagnosis","Fixed Appliances","Retention"]},
    "Pedodontics": {"Nikhil Marwah - Textbook of Pediatric Dentistry": ["Preventive Dentistry","Dental Caries","Pulp Therapy","Space Maintainers","Behavior Management"]},
    "Public Health Dentistry": {"Soben Peter - Essentials of Preventive and Community Dentistry": ["Epidemiology","Biostatistics","Indices (DMFT, OHI-S, CPITN)","Preventive Dentistry"]},
    "General Medicine": {"Davidson's Principles and Practice of Medicine": ["Cardiovascular Disease","Respiratory Disease","Endocrine Disease","Gastrointestinal Disease","Neurological Disease"]},
    "General Surgery": {"Bailey & Love's Short Practice of Surgery": ["Wounds and Scars","Burns","Surgical Infection","Head and Neck Surgery","Abdominal Surgery"]},
}

st.markdown("""
<style>
.block-container{max-width:900px;padding-top:2.2rem;padding-bottom:3rem}
.hero-title{text-align:center;font-size:2.8rem;font-weight:900;background:linear-gradient(90deg,#ff758c,#ff7eb3,#17b978,#00b4d8);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hero-subtitle{text-align:center;font-weight:700;margin-bottom:1.5rem}
.mode-card{padding:1.3rem;border-radius:18px;border:2px solid #00acc1;background:rgba(0,172,193,.08);margin-bottom:1rem}
div.stButton>button{border-radius:13px;min-height:2.8rem;font-weight:700}
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATABASES
# ============================================================

def app_db():
    c = sqlite3.connect(APP_DB, check_same_thread=False)
    c.execute("""CREATE TABLE IF NOT EXISTS cases(
        id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT,patient_email TEXT,
        patient_name TEXT,case_type TEXT,image_name TEXT,report_title TEXT,report TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS reviews(
        id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT,context TEXT,rating TEXT,suggestion TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS practicals(
        id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT,title TEXT,subject TEXT,
        description TEXT,file_name TEXT,file_type TEXT)""")
    c.commit()
    return c

def local_db():
    c = sqlite3.connect(LOCAL_DB, check_same_thread=False)
    c.execute("""CREATE TABLE IF NOT EXISTS subjects(
        id INTEGER PRIMARY KEY AUTOINCREMENT,year TEXT,subject TEXT UNIQUE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS topics(
        id INTEGER PRIMARY KEY AUTOINCREMENT,subject_id INTEGER,topic TEXT,
        UNIQUE(subject_id,topic))""")
    c.execute("""CREATE TABLE IF NOT EXISTS notes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,topic_id INTEGER,title TEXT,content TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS exam_answers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,topic_id INTEGER,marks TEXT,title TEXT,content TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS questions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,question TEXT UNIQUE,question_type TEXT,year TEXT,answer TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS viva(
        id INTEGER PRIMARY KEY AUTOINCREMENT,question TEXT UNIQUE,answer TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS search_aliases(
        id INTEGER PRIMARY KEY AUTOINCREMENT,alias TEXT UNIQUE,topic TEXT)""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_topic ON topics(topic)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_note_title ON notes(title)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_question ON questions(question)")
    # Seed navigation structure only; no invented textbook answers.
    for year, subs in V12_CURRICULUM.items():
        for subject in subs:
            c.execute("INSERT OR IGNORE INTO subjects(year,subject) VALUES(?,?)",(year,subject))
    for subject in [s for subs in V12_CURRICULUM.values() for s in subs]:
        row = c.execute("SELECT id FROM subjects WHERE subject=?",(subject,)).fetchone()
        if row:
            for section in V12_SECTIONS.get(subject,[]):
                c.execute("INSERT OR IGNORE INTO topics(subject_id,topic) VALUES(?,?)",(row[0],section))
    c.commit()
    return c

def save_case(email,name,ctype,image,title,report):
    c=app_db()
    c.execute("INSERT INTO cases(created_at,patient_email,patient_name,case_type,image_name,report_title,report) VALUES(?,?,?,?,?,?,?)",
              (str(datetime.now()),email,name,ctype,image,title,report))
    c.commit(); c.close()

def get_cases(email=""):
    c=app_db()
    rows=c.execute("SELECT * FROM cases WHERE patient_email=? ORDER BY id DESC",(email.strip(),)).fetchall() if email.strip() else c.execute("SELECT * FROM cases ORDER BY id DESC LIMIT 50").fetchall()
    c.close(); return rows

def save_review(context,rating,suggestion):
    c=app_db()
    c.execute("INSERT INTO reviews(created_at,context,rating,suggestion) VALUES(?,?,?,?)",(str(datetime.now()),context,rating,suggestion))
    c.commit(); c.close()

def save_practical(title,subject,description,file_name,file_type):
    c=app_db()
    c.execute("INSERT INTO practicals(created_at,title,subject,description,file_name,file_type) VALUES(?,?,?,?,?,?)",
              (str(datetime.now()),title,subject,description,file_name,file_type))
    c.commit(); c.close()

def get_practicals():
    c=app_db(); rows=c.execute("SELECT * FROM practicals ORDER BY id DESC").fetchall(); c.close(); return rows

def db_counts():
    c=local_db(); out={}
    for t in ["subjects","topics","notes","exam_answers","questions","viva","search_aliases"]:
        out[t]=c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    c.close(); return out

# ============================================================
# CLOUDFLARE AI - OPTIONAL SECOND LAYER
# ============================================================

def cf_secrets():
    try:
        account=str(st.secrets.get("CLOUDFLARE_ACCOUNT_ID","")).strip()
        token=str(st.secrets.get("CLOUDFLARE_API_TOKEN","")).strip()
        model=str(st.secrets.get("CLOUDFLARE_MODEL",DEFAULT_CF_MODEL)).strip()
    except Exception:
        account=token=""; model=DEFAULT_CF_MODEL
    account=account or os.getenv("CLOUDFLARE_ACCOUNT_ID","").strip()
    token=token or os.getenv("CLOUDFLARE_API_TOKEN","").strip()
    model=model or DEFAULT_CF_MODEL
    return account,token,model

def cf_ready():
    a,t,_=cf_secrets()
    return bool(a and t)

def cf_call(payload):
    account,token,model=cf_secrets()
    if not account or not token:
        raise RuntimeError("Cloudflare AI is not configured. Add CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN in Streamlit Secrets.")
    url=f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"
    payload=dict(payload)
    payload["options"]={"rejectIfBusy":True}
    req=Request(url,data=json.dumps(payload).encode(),headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},method="POST")
    try:
        with urlopen(req,timeout=90) as r:
            data=json.loads(r.read().decode())
    except HTTPError as e:
        try: detail=e.read().decode()[:800]
        except Exception: detail=""
        raise RuntimeError(f"Cloudflare AI HTTP {e.code}: {detail}")
    except URLError as e:
        raise RuntimeError(f"Could not reach Cloudflare AI: {e.reason}")
    if not data.get("success",False):
        raise RuntimeError("Cloudflare AI error: "+json.dumps(data.get("errors",[]))[:800])
    return data.get("result")

def cf_text(prompt,system=None):
    result=cf_call({"messages":[
        {"role":"system","content":system or "You are Pocket Dentistry, a dental learning assistant. Be accurate, educational and transparent about uncertainty. Do not invent citations."},
        {"role":"user","content":prompt}], "max_tokens":1400,"temperature":0.2})
    if isinstance(result,dict) and result.get("response"):
        return str(result["response"])
    raise RuntimeError("Cloudflare AI returned an empty response.")

def cf_image(uploaded,prompt,system=None):
    mime=uploaded.type or "image/png"
    encoded=base64.b64encode(uploaded.getvalue()).decode()
    result=cf_call({"messages":[
        {"role":"system","content":system or "You are an AI-assisted dental clinical decision-support system. Analyze only visible/supportable information. Never invent findings, tooth numbers, measurements or history. State uncertainty. Do not give a definitive diagnosis."},
        {"role":"user","content":[
            {"type":"text","text":prompt},
            {"type":"image_url","image_url":{"url":f"data:{mime};base64,{encoded}"}}
        ]}], "max_tokens":1800,"temperature":0.1})
    if isinstance(result,dict) and (result.get("response") or result.get("description")):
        return str(result.get("response") or result.get("description"))
    raise RuntimeError("Cloudflare AI returned an empty image response.")

def show_ai_error(e,title="AI request failed"):
    st.error(f"❌ {title}")
    st.warning(str(e))

# ============================================================
# DATABASE SEARCH
# ============================================================

def norm(s):
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9\s&/-]"," ",str(s or "").lower())).strip()

def local_search(query,limit=200):
    if not query.strip(): return []
    c=local_db()
    raw=query.strip().lower()
    alias=c.execute("SELECT topic FROM search_aliases WHERE lower(alias)=?",(raw,)).fetchone()
    effective=alias[0] if alias else query.strip()
    p=f"%{effective}%"
    try:
        rows=c.execute("""
        SELECT 'Note',n.title,n.content FROM notes n
        WHERE lower(n.title) LIKE lower(?) OR lower(n.content) LIKE lower(?)
        UNION ALL
        SELECT 'Exam Answer — '||ea.marks,ea.title,ea.content FROM exam_answers ea
        WHERE lower(ea.title) LIKE lower(?) OR lower(ea.content) LIKE lower(?)
        UNION ALL
        SELECT 'Question',q.question,COALESCE(q.answer,'') FROM questions q
        WHERE lower(q.question) LIKE lower(?) OR lower(COALESCE(q.answer,'')) LIKE lower(?)
        UNION ALL
        SELECT 'Viva',v.question,v.answer FROM viva v
        WHERE lower(v.question) LIKE lower(?) OR lower(v.answer) LIKE lower(?)
        UNION ALL
        SELECT 'Curriculum Topic',t.topic,
        'This curriculum topic exists locally; detailed curated content has not been stored yet.'
        FROM topics t WHERE lower(t.topic) LIKE lower(?) LIMIT ?""",
        (p,p,p,p,p,p,p,p,p,limit)).fetchall()
    except Exception:
        rows=[]
    # Token fallback
    if len(rows)<3:
        for term in [x for x in norm(effective).split() if len(x)>2][:5]:
            p=f"%{term}%"
            try:
                extra=c.execute("""SELECT 'Note',title,content FROM notes WHERE lower(title) LIKE lower(?) OR lower(content) LIKE lower(?)
                UNION ALL SELECT 'Exam Answer — '||marks,title,content FROM exam_answers WHERE lower(title) LIKE lower(?) OR lower(content) LIKE lower(?)
                UNION ALL SELECT 'Question',question,COALESCE(answer,'') FROM questions WHERE lower(question) LIKE lower(?) OR lower(COALESCE(answer,'')) LIKE lower(?)
                UNION ALL SELECT 'Viva',question,answer FROM viva WHERE lower(question) LIKE lower(?) OR lower(answer) LIKE lower(?) LIMIT 50""",
                (p,p,p,p,p,p,p,p)).fetchall()
                for r in extra:
                    if r not in rows: rows.append(r)
            except Exception: pass
            if len(rows)>=limit: break
    c.close()
    return rows[:limit]

def render_results(rows,title="📚 Local Database Results"):
    if not rows: return
    st.success(f"📚 Found {len(rows)} local result(s). AI was not used.")
    st.markdown(f"### {title}")
    for kind,title2,body in rows:
        with st.expander(f"📚 {kind}: {title2}",expanded=kind.startswith("Exam Answer")):
            st.markdown(body or "No stored content.")

def ai_fallback(question,key,prefix="",context=""):
    st.info("No sufficiently matching curated database answer was found. AI is optional.")
    if not cf_ready():
        st.warning("Cloudflare AI is not configured. Database-only mode is still fully functional.")
        return
    if not st.button("🤖 Ask Free AI Fallback",type="primary",use_container_width=True,key=f"ai_{key}"):
        return
    prompt=f"""{prefix}
USER QUESTION:
{question}

LOCAL DATABASE CONTEXT:
{context or "No matching local context was found."}

Use local context when relevant. Do not pretend missing information is present.
Do not invent textbook citations. Give a clear educational answer."""
    try:
        with st.spinner("Preparing AI fallback..."):
            ans=cf_text(prompt)
        st.markdown("### 🤖 AI Fallback Answer")
        st.markdown(ans)
        st.caption("Optional Cloudflare AI fallback — database was checked first.")
    except Exception as e: show_ai_error(e,"Cloudflare AI fallback failed")

# ============================================================
# EXPORT
# ============================================================

def report_html(title,patient,report,kind="Report"):
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>body{{font-family:Arial;max-width:850px;margin:40px auto;padding:20px}}.box{{padding:15px;border:1px solid #ddd;border-radius:10px;margin:12px 0}}</style>
</head><body><h1>🦷 Pocket Dentistry</h1><h2>{html.escape(title)}</h2>
<div class="box"><b>Patient/Target:</b>{html.escape(patient or "Not provided")}<br>
<b>Type:</b>{html.escape(kind)}<br><b>Date:</b>{date.today()}</div>
<div class="box">{html.escape(report or "").replace(chr(10),"<br>")}</div>
<button onclick="window.print()">🖨️ Print / Save as PDF</button></body></html>"""

def pdf_bytes(title,patient,report,kind="Report"):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
        from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        b=BytesIO(); d=SimpleDocTemplate(b,pagesize=A4,rightMargin=40,leftMargin=40,topMargin=40,bottomMargin=40)
        s=getSampleStyleSheet(); ts=ParagraphStyle("PocketTitle",parent=s["Title"],alignment=TA_CENTER,fontSize=18)
        body=ParagraphStyle("PocketBody",parent=s["BodyText"],fontSize=9.5,leading=14)
        story=[Paragraph("Pocket Dentistry",ts),Spacer(1,12),Paragraph(html.escape(title or "Report"),s["Heading2"]),
               Paragraph(f"<b>Target:</b> {html.escape(patient or 'Not provided')}<br/><b>Type:</b> {html.escape(kind)}<br/><b>Date:</b> {date.today()}",body),Spacer(1,12)]
        for line in (report or "").splitlines():
            if line.strip(): story += [Paragraph(html.escape(line.strip()),body),Spacer(1,4)]
        d.build(story); return b.getvalue()
    except Exception: return None

def show_export(title,patient,report,kind="Report"):
    if not report: return
    st.markdown("### 📄 Save / Download")
    st.download_button("🌐 Download HTML",report_html(title,patient,report,kind),"document.html","text/html",use_container_width=True)
    p=pdf_bytes(title,patient,report,kind)
    if p: st.download_button("📄 Download PDF",p,"document.pdf","application/pdf",use_container_width=True)

def review_section(context):
    rating=st.radio("How useful was this?",["👍 Useful","😐 Partly useful","👎 Not useful"],horizontal=True,key=f"rating_{context}")
    suggestion=st.text_area("Suggestion / improvement idea",key=f"suggestion_{context}")
    if st.button("Submit review",key=f"review_{context}",use_container_width=True):
        save_review(context,rating,suggestion); st.success("Thank you!")

# ============================================================
# STUDENT
# ============================================================

def local_study_hub(key="study"):
    st.markdown("### 🔎 Local Study Search")
    st.caption("Database first. Matching local content is shown before any AI.")
    q=st.text_input("Search topic, question or keyword",placeholder="e.g. Ameloblastoma, Gingivitis, DMFT",key=f"search_{key}")
    if not q.strip(): return
    rows=local_search(q)
    if rows: render_results(rows,"📚 Local Study Results")
    else:
        st.warning("No matching curated local content found.")
        ai_fallback(q,f"study_{key}","You are helping a BDS student. Answer at university-exam level.")

def local_question_bank(key="questions"):
    st.markdown("### 📝 Local Question Bank")
    q=st.text_input("Search question / topic",placeholder="e.g. Ameloblastoma, DMFT",key=f"qbank_{key}")
    if not q.strip():
        st.info("Search for a topic or question to open stored answers."); return
    rows=local_search(q)
    if rows: render_results(rows,"📝 Stored Questions & Answers")
    else:
        st.warning("No stored question/answer found.")
        ai_fallback(q,f"qbank_ai_{key}","Provide an educational BDS answer. Structure it clearly if it is an exam question.")

def student_library():
    st.markdown("### 📚 Digital Library")
    st.caption("Local database first; optional AI only if local content is missing.")
    subjects=list(TEXTBOOK_LIBRARY)
    subject=st.selectbox("Subject",subjects,key="sl_subject")
    book=st.selectbox("Reference textbook",list(TEXTBOOK_LIBRARY[subject]),key="sl_book")
    chapter=st.selectbox("Chapter",TEXTBOOK_LIBRARY[subject][book],key="sl_chapter")
    q=st.text_area("What do you want to understand?",key="sl_question")
    if st.button("🔎 Search Local Database",use_container_width=True,key="sl_search"):
        rows=local_search(f"{chapter} {q}",100)
        if rows: render_results(rows,"📚 Local Library Results")
        else:
            st.warning("No matching curated local content found.")
            ai_fallback(q or chapter,"student_library",f"Subject: {subject}\nTextbook: {book}\nChapter: {chapter}\nExplain for a BDS student.")

def practicals():
    st.markdown("### 🧪 Student Practicals & Lab Hub")
    with st.form("practical_form"):
        title=st.text_input("Practical title")
        subject=st.selectbox("Subject",list(V12_SECTIONS))
        desc=st.text_area("Steps / notes")
        f=st.file_uploader("Upload image / GIF / video",type=["mp4","mov","gif","png","jpg","jpeg","webp"])
        submit=st.form_submit_button("💾 Save",use_container_width=True)
        if submit:
            if not title.strip(): st.warning("Enter a title.")
            else:
                fname=f.name if f else "No Media"; ftype=f.type if f else "None"
                if f:
                    os.makedirs("uploads/practicals",exist_ok=True)
                    safe=os.path.basename(f.name)
                    with open(os.path.join("uploads/practicals",safe),"wb") as out: out.write(f.getbuffer())
                save_practical(title,subject,desc,fname,ftype); st.success("Saved!")
    st.markdown("### 📂 Saved Records")
    for r in get_practicals():
        _,created,title,subject,desc,fname,ftype=r
        with st.expander(f"📌 {title} ({subject})"):
            st.write(desc or "No notes.")
            if fname!="No Media":
                p=os.path.join("uploads/practicals",os.path.basename(fname))
                if os.path.exists(p):
                    st.video(p) if "video" in (ftype or "").lower() else st.image(p,use_container_width=True)

def v12_curriculum():
    st.markdown("### 🦷 V12 Curriculum + Local Topic Library")
    year=st.selectbox("📅 Year / Part",list(V12_CURRICULUM),key="v12_year")
    subject=st.selectbox("📚 Subject",V12_CURRICULUM[year],key="v12_subject")
    section=st.selectbox("📝 Curriculum / Practical Area",V12_SECTIONS.get(subject,[]),key="v12_section")
    st.success(f"**{year} → {subject} → {section}**")
    c=local_db()
    topics=[x[0] for x in c.execute("SELECT DISTINCT t.topic FROM topics t JOIN subjects s ON s.id=t.subject_id WHERE s.subject=? ORDER BY t.topic",(subject,)).fetchall()]
    c.close()
    if not topics: st.info("No local topics yet."); return
    selected=st.selectbox("Open topic",topics,key="v12_local_topic")
    c=local_db()
    note=c.execute("""SELECT n.title,n.content FROM notes n JOIN topics t ON t.id=n.topic_id JOIN subjects s ON s.id=t.subject_id
    WHERE s.subject=? AND t.topic=? ORDER BY n.id LIMIT 1""",(subject,selected)).fetchone()
    answers=c.execute("""SELECT ea.marks,ea.title,ea.content FROM exam_answers ea JOIN topics t ON t.id=ea.topic_id JOIN subjects s ON s.id=t.subject_id
    WHERE s.subject=? AND t.topic=? ORDER BY CASE ea.marks WHEN '10-mark' THEN 1 WHEN '5-mark' THEN 2 WHEN '3-mark' THEN 3 WHEN '2-mark' THEN 4 ELSE 5 END""",(subject,selected)).fetchall()
    c.close()
    if note:
        st.markdown(f"## 📖 {note[0]}"); st.markdown(note[1])
    else: st.info("No detailed curated note is stored for this topic yet.")
    if answers:
        st.markdown("## 📝 University Answers")
        for marks,title,content in answers:
            with st.expander(f"{marks} — {title}",expanded=(marks=="10-mark")): st.markdown(content)
    else: st.warning("No complete exam answer is stored for this topic yet.")
    with st.expander("📚 View complete V12 curriculum"):
        for y,subs in V12_CURRICULUM.items():
            st.markdown(f"### {y}")
            for s in subs: st.markdown(f"**{s}** — {' • '.join(V12_SECTIONS.get(s,[]))}")

# ============================================================
# CLINICAL LIBRARY
# ============================================================

def doctor_library():
    st.markdown("### 📚 Clinical Digital Library")
    subjects=list(TEXTBOOK_LIBRARY)
    subject=st.selectbox("Subject",subjects,key="dl_subject")
    book=st.selectbox("Textbook",list(TEXTBOOK_LIBRARY[subject]),key="dl_book")
    chapter=st.selectbox("Chapter",TEXTBOOK_LIBRARY[subject][book],key="dl_chapter")
    q=st.text_area("What do you want to understand?",key="dl_question")
    if st.button("🔎 Search Database First",type="primary",use_container_width=True,key="dl_search") and q.strip():
        rows=local_search(f"{chapter} {q}",100)
        if rows:
            render_results(rows,"📚 Local Clinical Library Results")
            st.success("Database answer found — Cloudflare AI was not used.")
        else:
            ai_fallback(q,"doctor_library",f"Subject: {subject}\nTextbook: {book}\nChapter: {chapter}\nGive an academic dental/medical explanation. Do not invent citations.")

# ============================================================
# CLINICAL AI
# ============================================================

COMMON_SAFETY="""You are an AI-assisted dental clinical decision-support system.
Analyze only information provided. Never invent findings, tooth numbers, measurements or history.
Clearly state uncertainty and limitations. Do not provide a definitive diagnosis or prescribe treatment."""

RADIOGRAPHS=["IOPA","OPG","Bitewing","Occlusal","Facial Radiograph","Lateral Cephalogram (Ceph)"]
CEPH=["Steiner Analysis","Downs Analysis","McNamara Analysis","Tweed Analysis","Wits Appraisal","Jarabak Analysis","Soft Tissue Profile Analysis","Combined / All Analyses"]

def xray():
    st.markdown("### 🩻 AI Radiographic Assessment")
    if not cf_ready(): st.info("Cloudflare AI is not configured. Student/database features still work.")
    remaining=DAILY_ANALYSIS_LIMIT-st.session_state.analysis_count
    st.caption(f"AI analyses remaining today: {max(remaining,0)}/{DAILY_ANALYSIS_LIMIT}")
    rtype=st.selectbox("Radiograph type",RADIOGRAPHS)
    ceph=st.selectbox("Cephalometric analysis",CEPH) if "Ceph" in rtype else ""
    calibration=st.radio("Scale calibration",["🤖 Auto estimation","✏️ Enter known mm/pixel"])
    scale=st.text_input("Known scale",value="1.0 mm/pixel") if "Enter" in calibration else "Auto-estimated"
    f=st.file_uploader("📤 Upload radiograph",type=["png","jpg","jpeg","webp"],key="xray_file")
    if f: st.image(f,use_container_width=True)
    name=st.text_input("Patient / Case identifier",key="xray_name")
    email=st.text_input("Patient email (optional)",key="xray_email")
    if st.button("🔍 Analyze X-ray",type="primary",use_container_width=True,disabled=(remaining<=0),key="xray_button"):
        if not f: st.warning("Upload a radiograph first."); return
        if not cf_ready(): st.error("Cloudflare AI is not configured."); return
        prompt=COMMON_SAFETY+f"""
Radiograph type: {rtype}
Cephalometric analysis: {ceph}
Scale information: {scale}
Assess image quality and only visible/supportable findings.
For Ceph, state which landmarks/measurements are actually assessable and never invent values.
Return:
1. IMAGE QUALITY
2. VISIBLE / SUPPORTABLE FINDINGS
3. TOOTH / REGION if supportable
4. PROVISIONAL RADIOGRAPHIC IMPRESSION
5. UNCERTAINTY / LIMITATIONS
6. SUGGESTED NEXT CLINICAL STEP
This is educational decision support, not a definitive diagnosis."""
        try:
            with st.spinner("Analyzing radiograph with Cloudflare AI..."):
                ans=cf_image(f,prompt,COMMON_SAFETY)
            st.session_state.analysis_count+=1
            save_case(email,name,rtype,f.name,rtype+" Assessment",ans)
            st.success("Analysis completed."); st.markdown(ans)
            show_export(rtype+" Assessment",name,ans,"Radiographic AI")
            review_section("radiograph")
        except Exception as e: show_ai_error(e,"Radiographic AI analysis failed")

def soft_tissue():
    st.markdown("### 👄 Soft-Tissue Clinical Reasoning")
    name=st.text_input("Patient / Case identifier",key="soft_name")
    email=st.text_input("Patient email (optional)",key="soft_email")
    image=st.file_uploader("📷 Clinical photograph",type=["png","jpg","jpeg","webp"],key="soft_image")
    if image: st.image(image,use_container_width=True)
    lesion=st.selectbox("Primary appearance",["White lesion","Red lesion","Red-white lesion","Ulcer","Pigmented lesion","Swelling / mass","Vesicle / blister","Other / unclear"])
    site=st.text_input("Anatomical location")
    duration=st.text_input("Duration / progression")
    pain=st.selectbox("Pain",["Painless","Mild discomfort","Painful / Burning"])
    scrapable=st.selectbox("Scrapability",["Not applicable","Scrapable","Non-scrapable"])
    history=st.text_area("Additional history / findings")
    if st.button("🧠 Build Clinical Reasoning",type="primary",use_container_width=True,key="soft_button"):
        if not cf_ready(): st.error("Cloudflare AI is not configured."); return
        prompt=COMMON_SAFETY+f"""
Oral mucosal case:
Appearance: {lesion}
Site: {site}
Duration: {duration}
Pain: {pain}
Scrapability: {scrapable}
History: {history}
Provide:
1. Problem representation
2. Differential diagnosis categories
3. Evidence ledger: supporting / opposing / unknown
4. Missing information
5. ONE highest-value next clinical question
6. Appropriate diagnostic test considerations
7. Management categories
8. Red flags
Do not give a definitive diagnosis."""
        try:
            with st.spinner("Processing with Cloudflare AI..."):
                ans=cf_image(image,prompt,COMMON_SAFETY) if image else cf_text(prompt,COMMON_SAFETY)
            save_case(email,name,"Soft Tissue",image.name if image else "None","Soft-Tissue Clinical Reasoning",ans)
            st.markdown(ans); show_export("Soft-Tissue Clinical Reasoning",name,ans,"Clinical Decision Support")
            review_section("soft_tissue")
        except Exception as e: show_ai_error(e,"Soft-tissue reasoning failed")

# ============================================================
# DATABASE STATUS
# ============================================================

def database_admin():
    st.markdown("### 🗄️ Local Database Status")
    counts=db_counts()
    content=counts["notes"]+counts["exam_answers"]+counts["questions"]+counts["viva"]
    st.metric("Curated content records",content)
    c1,c2=st.columns(2)
    with c1:
        st.write(f"Subjects: **{counts['subjects']}**")
        st.write(f"Topics: **{counts['topics']}**")
        st.write(f"Notes: **{counts['notes']}**")
        st.write(f"Exam answers: **{counts['exam_answers']}**")
    with c2:
        st.write(f"Questions: **{counts['questions']}**")
        st.write(f"Viva: **{counts['viva']}**")
        st.write(f"Aliases: **{counts['search_aliases']}**")
    if content==0:
        st.warning("The database structure is ready, but no curated study content has been imported yet.")
    else:
        st.success("Curated local content is available. Search uses it before AI.")
    st.markdown("### 🤖 AI Fallback")
    if cf_ready():
        st.success(f"Cloudflare AI configured: `{cf_secrets()[2]}`")
    else:
        st.info("Cloudflare AI is OFF. Database-only mode works without AI.")

# ============================================================
# MODES / HOME
# ============================================================

def student_mode():
    st.markdown("## 🎓 Student Mode")
    if st.button("← Home",use_container_width=True,key="student_home"):
        st.session_state.mode=None; st.rerun()
    tabs=st.tabs(["🔎 Local Study","📝 Local Questions","🧪 Practicals","📖 Digital Library","🦷 V12 Curriculum"])
    with tabs[0]: local_study_hub("study")
    with tabs[1]: local_question_bank("questions")
    with tabs[2]: practicals()
    with tabs[3]: student_library()
    with tabs[4]: v12_curriculum()

def doctor_mode():
    st.markdown("## 🩺 Doctor Mode")
    if st.button("← Home",use_container_width=True,key="doctor_home"):
        st.session_state.mode=None; st.rerun()
    tabs=st.tabs(["🩻 X-ray AI","👄 Soft Tissue","📖 Clinical Library","📜 Case History","🗄️ DB Status"])
    with tabs[0]: xray()
    with tabs[1]: soft_tissue()
    with tabs[2]: doctor_library()
    with tabs[3]:
        st.markdown("### 📜 Saved Case History")
        email=st.text_input("Search patient email",key="history_email")
        rows=get_cases(email)
        if not rows: st.info("No saved cases found.")
        for r in rows:
            _,created,pemail,name,ctype,img,title,report=r
            with st.expander(f"{created} — {name or 'Case'} — {ctype}"):
                st.write(f"**Patient:** {name or 'Not provided'}")
                st.write(f"**Email:** {pemail or 'Not provided'}")
                st.markdown(report)
                show_export(title or "Saved Case",name or "",report,ctype or "Saved Report")
    with tabs[4]: database_admin()

def home():
    st.markdown('<div class="hero-title">🦷 Pocket Dentistry & Medical Hub</div>',unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Database-First Dental Learning & Clinical Decision-Support</div>',unsafe_allow_html=True)
    counts=db_counts()
    content=counts["notes"]+counts["exam_answers"]+counts["questions"]+counts["viva"]
    st.info("📚 Local database is checked first. 🤖 Optional Cloudflare AI is used only when local content is not sufficient.")
    if content: st.success(f"📚 Local knowledge base active — {content} curated content record(s).")
    else: st.warning("📚 Database structure is ready, but curated study content has not been imported yet.")
    c1,c2=st.columns(2)
    with c1:
        st.markdown('<div class="mode-card"><h3>🎓 Student Mode</h3><p>Local study • Question bank • Practicals • Digital Library • V12 Curriculum • AI fallback</p></div>',unsafe_allow_html=True)
        if st.button("🎓 Enter Student Mode",use_container_width=True,key="home_student"):
            st.session_state.mode="student"; st.rerun()
    with c2:
        st.markdown('<div class="mode-card"><h3>🩺 Doctor Mode</h3><p>X-ray AI • Cephalometric assessment • Soft-tissue reasoning • Case history</p></div>',unsafe_allow_html=True)
        if st.button("🩺 Enter Doctor Mode",use_container_width=True,key="home_doctor"):
            st.session_state.mode="doctor"; st.rerun()

# ============================================================
# START
# ============================================================

if "mode" not in st.session_state: st.session_state.mode=None
if "analysis_date" not in st.session_state: st.session_state.analysis_date=str(date.today())
if "analysis_count" not in st.session_state: st.session_state.analysis_count=0
if st.session_state.analysis_date!=str(date.today()):
    st.session_state.analysis_date=str(date.today()); st.session_state.analysis_count=0

app_db()
local_db()

with st.sidebar:
    st.markdown("## 🦷 Pocket Dentistry")
    if st.button("🏠 Home",use_container_width=True,key="side_home"):
        st.session_state.mode=None; st.rerun()
    if st.button("🎓 Student Mode",use_container_width=True,key="side_student"):
        st.session_state.mode="student"; st.rerun()
    if st.button("🩺 Doctor Mode",use_container_width=True,key="side_doctor"):
        st.session_state.mode="doctor"; st.rerun()
    st.markdown("---")
    counts=db_counts()
    content=counts["notes"]+counts["exam_answers"]+counts["questions"]+counts["viva"]
    st.markdown(f"### 📚 Database\nContent records: **{content}**")
    st.success("🤖 Cloudflare AI: ON") if cf_ready() else st.info("🤖 Cloudflare AI: OFF")

if st.session_state.mode=="student": student_mode()
elif st.session_state.mode=="doctor": doctor_mode()
else: home()
