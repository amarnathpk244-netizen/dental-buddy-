
import os, json, re, html, sqlite3, base64
from datetime import date, datetime
from io import BytesIO
import streamlit as st

st.set_page_config(page_title="Pocket Dentistry", page_icon="🦷", layout="centered", initial_sidebar_state="collapsed")

DAILY_ANALYSIS_LIMIT = 3
MODEL_NAME = "gemini-3.6-flash"

# ============================================================
# V12 CURRICULUM — LOCAL / API-FREE
# ============================================================
V12_CURRICULUM = {'First Year': ['Dental Anatomy & Dental Histology', 'Head & Neck Anatomy'], 'Second Year': ['General Pathology', 'General Microbiology', 'Pharmacology'], 'Third Year': ['Oral Pathology', 'General Medicine', 'General Surgery'], 'Final Year / Part I': ['Oral Medicine & Radiology', 'Periodontics', 'Public Health Dentistry', 'Orthodontics'], 'Final Year / Part II': ['Oral & Maxillofacial Surgery', 'Pedodontics', 'Prosthodontics', 'Conservative Dentistry & Endodontics']}
V12_SECTIONS = {'Dental Anatomy & Dental Histology': ['Theory', 'Histology Slides', 'Tooth Carving', 'Spotters', 'MCQs', 'Practical Exam'], 'Head & Neck Anatomy': ['Histology', 'Dissection', 'Specimen Demonstration', 'Spotters', 'MCQs', 'Practical Exam'], 'General Pathology': ['Lecture Demonstrations', 'Histopathology Slides', 'Specimens', 'Student Practicals', 'Spotters', 'MCQs', 'Practical Exam'], 'General Microbiology': ['Organisms', 'Practical Slides', 'Culture Media', 'Animals', 'Instruments', 'Spotters', 'MCQs', 'Practical Exam'], 'Pharmacology': ['Dispensing Pharmacy', 'Dosage Forms', 'Prescription Writing', 'Dental Prescriptions', 'Spotters', 'MCQs', 'Practical Exam'], 'Oral Pathology': ['Hard Tissue Anomalies', 'Gross Specimens', 'Histopathology', 'Forensic Odontology', 'Spotters', 'MCQs', 'University Exam'], 'General Medicine': ['Theory', 'Clinical Training', 'Clinical Examination', 'MCQs', 'University Exam'], 'General Surgery': ['Theory', 'Clinical Training', 'Clinical Examination', 'MCQs', 'University Exam'], 'Oral Medicine & Radiology': ['Oral Medicine', 'Radiology', 'Clinical Training', 'Spotters', 'MCQs', 'Practical Exam', 'University Exam'], 'Periodontics': ['Theory', 'Clinical Tutorials', 'Demonstrations', 'Clinical Requirements', 'Spotters', 'MCQs', 'Practical Exam', 'University Exam'], 'Public Health Dentistry': ['Public Health', 'Dental Public Health', 'Research & Statistics', 'Practice Management', 'Palliative Care', 'Field Programme', 'Preventive Dentistry', 'Spotters', 'University Exam'], 'Orthodontics': ['Third Year Theory', 'Final Year Part I Theory', 'Clinical Training', 'Desirable Exercises', 'Spotters', 'MCQs', 'Practical Exam', 'University Exam'], 'Oral & Maxillofacial Surgery': ['Third Year Theory', 'Final Year Part I Theory', 'Final Year Part II Theory', 'Clinical Requirements', 'Spotters', 'MCQs', 'Practical Exam', 'University Exam'], 'Pedodontics': ['Third Year Theory', 'Final Year Part I Theory', 'Final Year Part II Theory', 'Clinical Requirements', 'Assignments', 'Spotters', 'MCQs', 'Practical Exam', 'University Exam'], 'Prosthodontics': ['Complete Denture', 'Removable Partial Prosthodontics', 'Fixed Partial Prosthodontics', 'Miscellaneous Prosthodontics', 'Clinical Requirements', 'Spotters', 'MCQs', 'Practical Exam', 'University Exam'], 'Conservative Dentistry & Endodontics': ['Conservative Dentistry', 'Endodontics', 'Clinical Requirements', 'Spotters', 'MCQs', 'Practical Exam', 'University Exam']}

# ============================================================
# STYLE
# ============================================================
st.markdown("""
<style>
.block-container{max-width:900px;padding-top:2.2rem;padding-bottom:3rem}
.hero-title{text-align:center;font-size:2.8rem;font-weight:900;background:linear-gradient(90deg,#ff758c,#ff7eb3,#17b978,#00b4d8);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hero-subtitle{text-align:center;font-weight:700;margin-bottom:1.5rem}
.mode-card{padding:1.3rem;border-radius:18px;border:2px solid #00acc1;background:rgba(0,172,193,.08);margin-bottom:1rem}
.chapter-card{padding:1rem;border-radius:14px;border:1px solid rgba(0,180,216,.3);margin-bottom:.7rem}
div.stButton>button{border-radius:13px;min-height:2.8rem;font-weight:700}
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATABASE
# ============================================================
DB_FILE="pocket_dentistry.db"

def db_connect():
    c=sqlite3.connect(DB_FILE,check_same_thread=False)
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

def save_case(email,name,ctype,image,title,report):
    c=db_connect()
    c.execute("INSERT INTO cases(created_at,patient_email,patient_name,case_type,image_name,report_title,report) VALUES(?,?,?,?,?,?,?)",
              (str(datetime.now()),email,name,ctype,image,title,report))
    c.commit(); c.close()

def get_cases(email=""):
    c=db_connect()
    if email.strip():
        r=c.execute("SELECT * FROM cases WHERE patient_email=? ORDER BY id DESC",(email.strip(),)).fetchall()
    else:
        r=c.execute("SELECT * FROM cases ORDER BY id DESC LIMIT 50").fetchall()
    c.close(); return r

def save_review(context,rating,suggestion):
    c=db_connect()
    c.execute("INSERT INTO reviews(created_at,context,rating,suggestion) VALUES(?,?,?,?)",
              (str(datetime.now()),context,rating,suggestion))
    c.commit(); c.close()

def save_practical(title,subject,description,file_name,file_type):
    c=db_connect()
    c.execute("INSERT INTO practicals(created_at,title,subject,description,file_name,file_type) VALUES(?,?,?,?,?,?)",
              (str(datetime.now()),title,subject,description,file_name,file_type))
    c.commit(); c.close()

def get_practicals():
    c=db_connect()
    r=c.execute("SELECT * FROM practicals ORDER BY id DESC").fetchall()
    c.close(); return r

# ============================================================
# GEMINI
# ============================================================
def get_api_key():
    try: key=st.secrets.get("GEMINI_API_KEY","")
    except Exception: key=""
    return str(key or os.getenv("GEMINI_API_KEY","")).strip()

def get_client():
    """Gemini is loaded only for Doctor Mode AI requests."""
    try:
        from google import genai
    except ImportError:
        raise RuntimeError("google-genai is not installed. Run: pip install google-genai")

    key = get_api_key()
    if not key:
        return None

    try:
        return genai.Client(api_key=key)
    except Exception:
        return None


def run_text_ai(prompt):
    c = get_client()
    if c is None:
        raise RuntimeError("Gemini API key not found or client could not be created.")

    r = c.models.generate_content(model=MODEL_NAME, contents=prompt)
    text = getattr(r, "text", None)

    if not text:
        raise RuntimeError("The AI returned an empty response.")

    return text


def run_image_analysis(uploaded, prompt):
    try:
        from google.genai import types
    except ImportError:
        raise RuntimeError("google-genai is not installed. Run: pip install google-genai")

    c = get_client()
    if c is None:
        raise RuntimeError("Gemini API key not found or client could not be created.")

    part = types.Part.from_bytes(
        data=uploaded.getvalue(),
        mime_type=uploaded.type or "image/png",
    )

    r = c.models.generate_content(
        model=MODEL_NAME,
        contents=[prompt, part],
    )

    text = getattr(r, "text", None)

    if not text:
        raise RuntimeError("The AI returned an empty response.")

    return text


def show_ai_error(e, title="AI request failed"):
    st.error(f"❌ {title}")
    st.markdown(friendly_error(e))


# ============================================================
# EXPORT
# ============================================================
def report_html(title,patient,report,kind="AI Report"):
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>{html.escape(title)}</title><style>
body{{font-family:Arial;max-width:850px;margin:40px auto;padding:20px}}
.box{{padding:15px;border:1px solid #ddd;border-radius:10px;margin:12px 0}}
</style></head><body><h1>🦷 Pocket Dentistry</h1>
<h2>{html.escape(title)}</h2><div class="box"><b>Patient/Target:</b>
{html.escape(patient or "Not provided")}<br><b>Type:</b>{html.escape(kind)}<br><b>Date:</b>{date.today()}</div>
<div class="box">{html.escape(report or "").replace(chr(10),"<br>")}</div>
<button onclick="window.print()">🖨️ Print / Save as PDF</button></body></html>"""

def pdf_bytes(title,patient,report,kind="AI Report"):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
        from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        b=BytesIO(); d=SimpleDocTemplate(b,pagesize=A4,rightMargin=40,leftMargin=40,topMargin=40,bottomMargin=40)
        s=getSampleStyleSheet(); title_s=ParagraphStyle("t",parent=s["Title"],alignment=TA_CENTER,fontSize=18)
        body=ParagraphStyle("b",parent=s["BodyText"],fontSize=9.5,leading=14)
        story=[Paragraph("Pocket Dentistry",title_s),Spacer(1,12),Paragraph(html.escape(title or "Report"),s["Heading2"]),
               Paragraph(f"<b>Target:</b> {html.escape(patient or 'Not provided')}<br/><b>Type:</b> {html.escape(kind)}<br/><b>Date:</b> {date.today()}",body),Spacer(1,12)]
        for line in (report or "").splitlines():
            if line.strip(): story += [Paragraph(html.escape(line.strip()),body),Spacer(1,4)]
        d.build(story); return b.getvalue()
    except Exception:return None

def show_export(title,patient,report,kind="AI Report"):
    if not report:return
    st.markdown("### 📄 Save / Download")
    doc=report_html(title,patient,report,kind)
    st.download_button("🌐 Download HTML",doc,"document.html","text/html",use_container_width=True)
    p=pdf_bytes(title,patient,report,kind)
    if p: st.download_button("📄 Download PDF",p,"document.pdf","application/pdf",use_container_width=True)

def review_section(context):
    st.markdown("### ⭐ Review & Suggestions")
    rating=st.radio("How useful was this?",["👍 Useful","😐 Partly useful","👎 Not useful"],horizontal=True,key=f"rating_{context}")
    suggestion=st.text_area("Suggestion / improvement idea",key=f"suggestion_{context}")
    if st.button("Submit review",key=f"review_{context}",use_container_width=True):
        save_review(context,rating,suggestion); st.success("Thank you!")

# ============================================================
# V12 CURRICULUM
# ============================================================
def v12_curriculum():
    st.markdown("### 🦷 V12 Curriculum")
    st.caption("Year → Subject → Topic / Practical Area • Local data • No API required")

    year=st.selectbox("📅 Year / Part",list(V12_CURRICULUM),key="v12_year")
    subjects=V12_CURRICULUM[year]
    subject=st.selectbox("📚 Subject",subjects,key="v12_subject")
    topics=V12_SECTIONS.get(subject,[])
    topic=st.selectbox("📝 Topic / Practical Area",topics,key="v12_topic")

    st.markdown(f"### 🎯 {topic}")
    st.success(f"**{year} → {subject} → {topic}**")

    st.markdown("#### Available areas")
    for x in topics:
        st.write(("**• "+x+"**") if x==topic else "• "+x)

    with st.expander("📚 View complete V12 curriculum"):
        for y,subs in V12_CURRICULUM.items():
            st.markdown(f"### {y}")
            for s in subs:
                st.markdown(f"**{s}**")
                st.caption(" • ".join(V12_SECTIONS.get(s,[])))

# ============================================================
# STUDENT PRACTICALS
# ============================================================
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
                    with open(os.path.join("uploads/practicals",f.name),"wb") as out: out.write(f.getbuffer())
                save_practical(title,subject,desc,fname,ftype); st.success("Saved!")

    st.markdown("---"); st.markdown("### 📂 Saved Records")
    for r in get_practicals():
        _,created,title,subject,desc,fname,ftype=r
        with st.expander(f"📌 {title} ({subject})"):
            st.write(desc or "No notes.")
            if fname!="No Media":
                p=os.path.join("uploads/practicals",fname)
                if os.path.exists(p):
                    if "video" in ftype.lower(): st.video(p)
                    else: st.image(p,use_container_width=True)

# ============================================================
# LIBRARY
# ============================================================
TEXTBOOK_LIBRARY={
"General Human Anatomy":{"BD Chaurasia's Human Anatomy (Vol 1-3)":["General Anatomy & Introduction","Upper Limb and Thorax","Abdomen and Pelvis","Head, Neck and Brain","Lower Limb","Embryology & General Histology","Osteology"]},
"General Human Physiology":{"Guyton and Hall Textbook of Medical Physiology":["General Physiology & Cell Physiology","Nerve and Muscle","Heart and Circulation","The Body Fluids and Kidneys","Respiration","Nervous System","Gastrointestinal Physiology","Endocrinology"]},
"General Pathology":{"Robbins & Cotran Pathologic Basis of Disease":["Cell Injury","Inflammation and Repair","Hemodynamics","Neoplasia","Genetic Diseases"]},
"Oral Pathology":{"Shafer's Textbook of Oral Pathology":["Developmental Disturbances","Dental Caries","Pulp Diseases","Periodontal Diseases","Cysts","Odontogenic Tumors"]},
"Oral Medicine & Radiology":{"Burket's Oral Medicine":["Patient Evaluation","Oral Mucosal Diseases","Ulcers","White Lesions","Salivary Gland Disorders"]},
"Periodontics":{"Carranza's Clinical Periodontology":["Periodontal Anatomy","Gingivitis","Periodontitis","Scaling and Root Planing","Periodontal Surgery"]},
"Conservative Dentistry & Endodontics":{"Cohen's Pathways of the Pulp":["Pulp Biology","Diagnosis","Root Canal Anatomy","Cleaning and Shaping","Obturation"]},
"Prosthodontics":{"Nallaswamy - Textbook of Prosthodontics":["Complete Dentures","Impression Making","Jaw Relations","Removable Partial Dentures","Fixed Prosthodontics"]},
"Orthodontics":{"Proffit - Contemporary Orthodontics":["Growth and Development","Malocclusion","Diagnosis","Fixed Appliances","Retention"]},
"Pedodontics":{"Nikhil Marwah - Textbook of Pediatric Dentistry":["Preventive Dentistry","Dental Caries","Pulp Therapy","Space Maintainers","Behavior Management"]},
"Public Health Dentistry":{"Soben Peter - Essentials of Preventive and Community Dentistry":["Epidemiology","Biostatistics","Indices (DMFT, OHI-S, CPITN)","Preventive Dentistry"]},
"General Medicine":{"Davidson's Principles and Practice of Medicine":["Cardiovascular Disease","Respiratory Disease","Endocrine Disease","Gastrointestinal Disease","Neurological Disease"]},
"General Surgery":{"Bailey & Love's Short Practice of Surgery":["Wounds and Scars","Burns","Surgical Infection","Head and Neck Surgery","Abdominal Surgery"]}
}

def library():
    st.markdown("### 📚 Digital Library")
    subjects=list(TEXTBOOK_LIBRARY)
    subject=st.selectbox("Subject",subjects)
    book=st.selectbox("Textbook",list(TEXTBOOK_LIBRARY[subject]))
    chapter=st.selectbox("Chapter",TEXTBOOK_LIBRARY[subject][book])
    q=st.text_area("What do you want to understand?")
    if st.button("🤖 Ask the Library",type="primary",use_container_width=True) and q.strip():
        try:
            with st.spinner("Preparing explanation..."):
                ans=run_text_ai(f"Subject: {subject}\nTextbook: {book}\nChapter: {chapter}\nQuestion: {q}\nGive an academic dental/medical explanation. Do not invent citations.")
            st.markdown(ans); show_export(f"Explanation - {chapter}",subject,ans,"Explanation")
        except Exception as e: show_ai_error(e)

# ============================================================
# AI TUTOR / PYQ
# ============================================================

# ============================================================
# LOCAL STUDY DATABASE — NO API
# ============================================================
LOCAL_DB = "study_database.db"

def local_db():
    return sqlite3.connect(LOCAL_DB, check_same_thread=False)

def local_search(query):
    if not query.strip():
        return []
    c = local_db()
    q = f"%{query.strip()}%"
    rows = c.execute("""
        SELECT 'Note' AS kind, n.title AS title, n.content AS body
        FROM notes n
        WHERE n.title LIKE ? OR n.content LIKE ?
        UNION ALL
        SELECT q.question, q.question, COALESCE(q.answer,'')
        FROM questions q
        WHERE q.question LIKE ? OR COALESCE(q.answer,'') LIKE ?
        UNION ALL
        SELECT 'Viva', v.question, v.answer
        FROM viva v
        WHERE v.question LIKE ? OR v.answer LIKE ?
        ORDER BY title
        LIMIT 100
    """, (q,q,q,q,q,q)).fetchall()
    c.close()
    return rows

def local_study_hub():
    st.markdown("### 🔎 Local Study Search")
    st.caption("Searches only the Pocket Dentistry local study database — no Gemini/API call.")
    query = st.text_input("Search topic, question or keyword", placeholder="e.g. DMFT, periodontal pocket, complete denture")
    if query.strip():
        results = local_search(query)
        st.caption(f"{len(results)} local result(s)")
        if not results:
            st.info("No local content found for this search yet.")
        for kind,title,body in results:
            with st.expander(f"📚 {kind}: {title}"):
                st.markdown(body)

def local_subject_browser():
    c = local_db()
    years = [x[0] for x in c.execute("SELECT DISTINCT year FROM subjects ORDER BY id").fetchall()]
    year = st.selectbox("Year", years, key="local_year")
    subjects = [x[0] for x in c.execute("SELECT subject FROM subjects WHERE year=? ORDER BY subject",(year,)).fetchall()]
    subject = st.selectbox("Subject", subjects, key="local_subject")
    topics = [x[0] for x in c.execute("""
        SELECT t.topic FROM topics t JOIN subjects s ON s.id=t.subject_id
        WHERE s.year=? AND s.subject=? ORDER BY t.topic
    """,(year,subject)).fetchall()]
    topic = st.selectbox("Topic", topics, key="local_topic")
    row = c.execute("""
        SELECT n.title,n.content FROM notes n JOIN topics t ON t.id=n.topic_id
        JOIN subjects s ON s.id=t.subject_id
        WHERE s.year=? AND s.subject=? AND t.topic=?
        ORDER BY n.id LIMIT 1
    """,(year,subject,topic)).fetchone()
    c.close()

    st.markdown(f"### 📖 {topic}")
    if row:
        st.markdown(f"#### {row[0]}")
        st.markdown(row[1])
    else:
        st.info("This topic is in the curriculum, but detailed local notes have not been added yet.")

def student_ai():
    # Kept as a compatibility wrapper, but it is deliberately API-free.
    local_study_hub()


# ============================================================
# RADIOGRAPH AI
# ============================================================
COMMON_SAFETY="""You are an AI-assisted dental clinical decision-support system.
Analyze only information provided.
Never invent findings, tooth numbers, measurements or history.
Clearly state uncertainty and limitations.
Do not provide a definitive diagnosis or prescribe treatment.
"""

RADIOGRAPHS=["IOPA","OPG","Bitewing","Occlusal","Facial Radiograph","Lateral Cephalogram (Ceph)"]
CEPH=["Steiner Analysis","Downs Analysis","McNamara Analysis","Tweed Analysis","Wits Appraisal","Jarabak Analysis","Soft Tissue Profile Analysis","Combined / All Analyses"]

def xray():
    st.markdown("### 🩻 AI Radiographic Assessment")
    remaining=DAILY_ANALYSIS_LIMIT-st.session_state.count
    st.caption(f"AI analyses remaining today: {remaining}/{DAILY_ANALYSIS_LIMIT}")
    rtype=st.selectbox("Radiograph type",RADIOGRAPHS)
    ceph=st.selectbox("Cephalometric analysis",CEPH) if "Ceph" in rtype else ""
    calibration=st.radio("Scale calibration",["🤖 Auto estimation","✏️ Enter known mm/pixel"])
    scale=st.text_input("Known scale",value="1.0 mm/pixel") if "Enter" in calibration else "Auto-estimated"
    f=st.file_uploader("📤 Upload radiograph",type=["png","jpg","jpeg","webp"],key="xray_file")
    if f: st.image(f,use_container_width=True)
    name=st.text_input("Patient / Case identifier",key="xray_name")
    email=st.text_input("Patient email (optional)",key="xray_email")
    if st.button("🔍 Analyze X-ray",type="primary",use_container_width=True,disabled=remaining<=0):
        if not f: st.warning("Upload a radiograph first."); return
        prompt=COMMON_SAFETY+f"""
Radiograph type: {rtype}
Cephalometric analysis: {ceph}
Scale information: {scale}
Assess image quality and only visible/supportable findings. For Ceph, state which landmarks/measurements are actually assessable and do not invent values.
Return a structured educational radiographic assessment, uncertainty, and suggested next clinical step.
"""
        try:
            with st.spinner("Analyzing radiograph..."):
                ans=run_image_analysis(f,prompt)
            st.session_state.count+=1
            save_case(email,name,rtype,f.name,rtype+" Assessment",ans)
            st.success("Analysis completed.")
            st.markdown(ans); show_export(rtype+" Assessment",name,ans,"Radiographic AI")
            review_section("radiograph")
        except Exception as e: show_ai_error(e,"Radiographic AI analysis failed")

# ============================================================
# SOFT TISSUE
# ============================================================
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
    if st.button("🧠 Build Clinical Reasoning",type="primary",use_container_width=True):
        prompt=COMMON_SAFETY+f"""
Oral mucosal case:
Appearance: {lesion}
Site: {site}
Duration: {duration}
Pain: {pain}
Scrapability: {scrapable}
History: {history}
Provide problem representation, differential diagnoses, evidence ledger (supporting/opposing/unknown), missing information, ONE highest-value next clinical question, appropriate diagnostic test considerations, management categories and red flags. Do not give a definitive diagnosis.
"""
        try:
            with st.spinner("Processing..."):
                ans=run_image_analysis(image,prompt) if image else run_text_ai(prompt)
            save_case(email,name,"Soft Tissue",image.name if image else "None","Soft-Tissue Clinical Reasoning",ans)
            st.markdown(ans); show_export("Soft-Tissue Clinical Reasoning",name,ans,"Clinical Decision Support")
            review_section("soft_tissue")
        except Exception as e: show_ai_error(e,"Soft-tissue reasoning failed")

# ============================================================
# MODES
# ============================================================
def student_mode():
    st.markdown("## 🎓 Student Mode")
    if st.button("← Home",use_container_width=True): st.session_state.mode=None; st.rerun()
    tabs=st.tabs(["🔎 Local Study","📝 Local Questions","🧪 Practicals","📖 Digital Library","🦷 V12 Curriculum"])
    with tabs[0]: local_study_hub()
    with tabs[1]:
        st.markdown("### 📝 Local Question Bank")
        local_study_hub()
    with tabs[2]: practicals()
    with tabs[3]: library()
    with tabs[4]: v12_curriculum()

def doctor_mode():
    st.markdown("## 🩺 Doctor Mode")
    if st.button("← Home",use_container_width=True): st.session_state.mode=None; st.rerun()
    tabs=st.tabs(["🩻 X-ray AI","👄 Soft Tissue","📖 Clinical Library","📜 Case History"])
    with tabs[0]: xray()
    with tabs[1]: soft_tissue()
    with tabs[2]: library()
    with tabs[3]:
        st.markdown("### 📜 Saved Case History")
        email=st.text_input("Search patient email",key="history_email")
        rows=get_cases(email)
        if not rows: st.info("No saved cases found.")
        for r in rows:
            cid,created,pemail,name,ctype,img,title,report=r
            with st.expander(f"{created} — {name or 'Case'} — {ctype}"):
                st.write(f"**Patient:** {name or 'Not provided'}")
                st.write(f"**Email:** {pemail or 'Not provided'}")
                st.markdown(report)
                show_export(title or "Saved Case",name or "",report,ctype or "Saved Report")

# ============================================================
# HOME
# ============================================================
def home():
    st.markdown('<div class="hero-title">🦷 Pocket Dentistry & Medical Hub</div>',unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">AI-Powered Dental & Medical Learning & Clinical Decision-Support Platform</div>',unsafe_allow_html=True)
    st.info("🦷 V12 Curriculum is built into Student Mode and works locally without an API.")
    c1,c2=st.columns(2)
    with c1:
        st.markdown('<div class="mode-card"><h3>🎓 Student Mode</h3><p>AI Tutor • KUHS PYQ • Practicals • Digital Library • V12 Curriculum</p></div>',unsafe_allow_html=True)
        if st.button("🎓 Enter Student Mode",use_container_width=True): st.session_state.mode="student"; st.rerun()
    with c2:
        st.markdown('<div class="mode-card"><h3>🩺 Doctor Mode</h3><p>X-ray AI • Cephalometric analysis • Soft-tissue reasoning • Case history</p></div>',unsafe_allow_html=True)
        if st.button("🩺 Enter Doctor Mode",use_container_width=True): st.session_state.mode="doctor"; st.rerun()

if "mode" not in st.session_state: st.session_state.mode=None
if "analysis_date" not in st.session_state: st.session_state.analysis_date=str(date.today())
if "count" not in st.session_state: st.session_state.count=0
if st.session_state.analysis_date!=str(date.today()):
    st.session_state.analysis_date=str(date.today()); st.session_state.count=0

db_connect()

with st.sidebar:
    st.markdown("## 🦷 Pocket Dentistry")
    if st.button("🏠 Home",use_container_width=True): st.session_state.mode=None; st.rerun()
    if st.button("🎓 Student Mode",use_container_width=True): st.session_state.mode="student"; st.rerun()
    if st.button("🩺 Doctor Mode",use_container_width=True): st.session_state.mode="doctor"; st.rerun()

if st.session_state.mode=="student": student_mode()
elif st.session_state.mode=="doctor": doctor_mode()
else: home()
