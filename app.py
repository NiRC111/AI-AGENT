# -*- coding: utf-8 -*-
"""
Government Quasi-Judicial AI System — Zilla Parishad, Chandrapur
• Professional Government UI with official masthead (your two images)
• Mandatory Case + GR inputs (PDF/TXT/Image)
• Smart field extraction from Marathi case text (candidate, village, hearing, attendees, distance, refs…)
• Clause highlighter for GR
• Quasi-judicial orders (Marathi & English) with signature block & watermark
• Marathi-first; English optional
• EasyOCR for scanned docs (Marathi/Hindi/English)
"""

import io, os, re, datetime, tempfile, base64, pathlib
from typing import List, Tuple, Dict

import streamlit as st
import numpy as np
from PIL import Image

# ---------- Page ----------
st.set_page_config(page_title="Government Quasi-Judicial AI — ZP Chandrapur", layout="wide")

# ---------- Styles ----------
st.markdown("""
<style>
:root{
  --gov:#0B3A82; --ink:#0b1220; --muted:#475569; --line:#e5e7eb; --wash:#f8fafc;
  --ok:#1a7f37; --warn:#b58100; --bad:#b42318;
}
html, body { background:#ffffff; color:var(--ink); }
.block-container { max-width: 1180px !important; padding-top: 0 !important; }

/* Masthead */
.mast{display:flex;align-items:center;gap:16px;padding:12px 14px;border-bottom:1px solid var(--line);margin-bottom:12px;}
.mast-left{display:flex;align-items:center;gap:12px}
.mast-right{margin-left:auto}
.mast h1{font-size:1.05rem;margin:0;font-weight:800;color:#0B3A82}
.mast .sub{font-size:.92rem;color:#0f172a}

/* Section */
.section-title{margin:18px 0 8px 0;padding:10px 12px;border:1px solid var(--line);
  border-left:4px solid var(--gov);border-radius:8px;background:var(--wash);font-weight:700}
.card{border:1px solid var(--line);border-radius:12px;padding:16px;background:#fff}

/* Tabs */
.stTabs [data-baseweb="tab-list"]{gap:6px}
.stTabs [role="tab"]{padding:10px 14px;border-radius:10px 10px 0 0;background:#f3f4f6;border:1px solid var(--line);border-bottom:none;font-weight:600;color:#111827}
.stTabs [aria-selected="true"]{background:#ffffff;border-bottom:1px solid #fff}

/* Order block */
.order-block{border:1px solid var(--line);border-radius:10px;padding:22px;background:#fff}
.hl{background:#fff3cd;border-bottom:2px solid #facc15}

/* Watermark */
.wm-wrap{position:relative}
.wm-bg{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;pointer-events:none;z-index:0}
.wm-bg img{opacity:.09;width:46%;min-width:260px;max-width:520px;filter:grayscale(100%)}
.order-content{position:relative;z-index:1}

/* Signature block */
.sig-block{margin-top:24px;padding-top:12px;border-top:1px dashed var(--line);line-height:1.45}
.sig-rows{display:grid;grid-template-columns:1fr 1fr;gap:10px 24px}
.sig-label{color:#6b7280;font-size:.92rem}
.sig-name{font-weight:700}
.sig-desig{margin-top:-2px}

/* Alerts */
.alert-warn{border-left:4px solid var(--warn);padding:10px 12px;background:#fffaf0}
</style>
""", unsafe_allow_html=True)

# ---------- Load masthead images ----------
ASSET_DIR = pathlib.Path(__file__).parent / "assets"
def _b64(path: pathlib.Path) -> str:
    if not path.exists(): return ""
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("utf-8")

maha_emblem = _b64(ASSET_DIR / "maha_emblem.png")
zp_banner   = _b64(ASSET_DIR / "zp_chandrapur_banner.png")

st.markdown(f"""
<div class="mast">
  <div class="mast-left">
    <img src="{maha_emblem}" width="70"/>
    <div>
      <h1>Government Quasi-Judicial AI System</h1>
      <div class="sub">Zilla Parishad, Chandrapur · जिल्हा परिषद, चंद्रपूर · Government of Maharashtra</div>
    </div>
  </div>
  <div class="mast-right">
    <img src="{zp_banner}" height="46"/>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------- Lazy imports ----------
def _mods():
    out = {}
    try:
        import fitz         # PyMuPDF
        out["fitz"] = fitz
    except Exception as e:
        out["fitz"] = None; out["fitz_err"] = str(e)
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract_text
        out["pdfminer_extract_text"] = pdfminer_extract_text
    except Exception as e:
        out["pdfminer_extract_text"] = None; out["pdfminer_err"] = str(e)
    try:
        from pypdf import PdfReader
        out["PdfReader"] = PdfReader
    except Exception as e:
        out["PdfReader"] = None; out["pypdf_err"] = str(e)
    try:
        import easyocr
        out["easyocr"] = easyocr
    except Exception as e:
        out["easyocr"] = None; out["easyocr_err"] = str(e)
    return out

OCR_LANGS = ["mr","hi","en"]
DEVN = re.compile(r"[\u0900-\u097F]")  # Devanagari block
AADHAAR = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
PAN     = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
MOBILE  = re.compile(r"\b[6-9]\d{9}\b")

def red(s:str)->str:
    s = AADHAAR.sub("XXXX XXXX XXXX", s)
    s = PAN.sub("XXXXX9999X", s)
    s = MOBILE.sub("XXXXXXXXXX", s)
    return s

# ---------- Extraction helpers ----------
def read_txt(b: bytes) -> str:
    for enc in ("utf-8","utf-8-sig","utf-16","utf-16le","utf-16be"):
        try: return b.decode(enc)
        except: pass
    return b.decode("latin-1","ignore")

def extract_text_with_pypdf(pdf: bytes) -> str:
    PdfReader = _mods().get("PdfReader")
    if not PdfReader: return ""
    try:
        reader = PdfReader(io.BytesIO(pdf))
        return "\n".join([(p.extract_text() or "") for p in reader.pages]).strip()
    except: return ""

def extract_text_from_pdf(pdf: bytes) -> str:
    mods = _mods()
    fitz = mods.get("fitz")
    pdfminer_extract_text = mods.get("pdfminer_extract_text")
    text = ""
    # A) PyMuPDF
    try:
        if fitz:
            doc = fitz.open(stream=pdf, filetype="pdf")
            text = "\n".join([p.get_text("text") for p in doc]).strip()
            doc.close()
    except: pass
    # B) Blocks (often better)
    try:
        if fitz and (not DEVN.search(text) or len(text)<60):
            doc = fitz.open(stream=pdf, filetype="pdf")
            parts=[]
            for p in doc:
                blocks = p.get_text("blocks") or []
                blocks.sort(key=lambda b:(round(b[1],1), round(b[0],1)))
                for b in blocks:
                    if len(b)>=5 and (b[4] or "").strip():
                        parts.append(b[4].strip())
            doc.close()
            tb = "\n".join(parts).strip()
            if len(tb)>len(text) or (DEVN.search(tb) and not DEVN.search(text)): text = tb
    except: pass
    # C) pdfminer
    if (not DEVN.search(text)) and pdfminer_extract_text:
        try:
            with tempfile.NamedTemporaryFile(delete=False,suffix=".pdf") as tmp:
                tmp.write(pdf); p=tmp.name
            t2 = pdfminer_extract_text(p) or ""
            try: os.unlink(p)
            except: pass
            if DEVN.search(t2) or len(t2)>len(text): text=t2
        except: pass
    # D) pypdf
    if len(text)<50:
        t3 = extract_text_with_pypdf(pdf)
        if DEVN.search(t3) or len(t3)>len(text): text=t3
    return text.strip()

def easy_ocr_image(img_bytes: bytes) -> str:
    m = _mods()
    easyocr = m.get("easyocr")
    if not easyocr: return ""
    try:
        reader = easyocr.Reader(OCR_LANGS, gpu=False, verbose=False)
        arr = np.array(Image.open(io.BytesIO(img_bytes)).convert("RGB"))
        lines = reader.readtext(arr, detail=0, paragraph=True)
        return "\n".join(lines).strip()
    except: return ""

def extract_any(file) -> str:
    name = (file.name or "").lower()
    data = file.read()
    if name.endswith(".txt"):  return read_txt(data)
    if name.endswith(".pdf"):  return extract_text_from_pdf(data)
    if name.endswith((".png",".jpg",".jpeg",".webp",".tif",".tiff")): return easy_ocr_image(data)
    return ""

# ---------- Clause highlight ----------
_CLAUSE = re.compile("|".join([
    r"(कलम\s*\d+[A-Za-z]?)", r"(धोरण\s*\d+)", r"(अट\s*\d+)",
    r"(Clause\s*\d+)", r"(Section\s*\d+[A-Za-z]?)"
]), flags=re.I)

def highlight_gr(text: str, max_lines=140) -> str:
    if not text.strip(): return "<em>—</em>"
    out=[]
    for ln in text.splitlines()[:max_lines]:
        if any(k in ln for k in ["स्थानिक","रहिवासी"]) or _CLAUSE.search(ln):
            ln = _CLAUSE.sub(r"<span class='hl'>\\1</span>", ln)
            out.append(f"• {ln}")
        else:
            out.append(ln)
    if len(text.splitlines())>max_lines: out.append("…")
    return "<br>".join(out)

# ---------- Marathi case parsing (pulls concrete facts) ----------
MAR_CAND = re.compile(r"(सौ\.|श्री\.?)\s*([अ-ह]+[^\s,]*)\s+([अ-ह][^,]*)[, ]+\s*रा\.\s*([अ-ह][^,]*)(?:,\s*ता\.\s*([अ-ह][^,]*))?", re.U)
MAR_HEAR = re.compile(r"(सुनावणी)\s*(दिनांक|दिनाँक|दि\.?)\s*[:\-]?\s*(\d{1,2}/\d{1,2}/\d{4})", re.U)
MAR_HEAR_TIME = re.compile(r"(सकाळी|सायंकाळी)\s*([०-९0-9]{1,2}(\.[0-9]+)?)\s*(वा|वाजता)", re.U)
MAR_DIST = re.compile(r"(\d+|\d+[\.]\d+|[०-९]+)\s*(कि\.?मी\.?|किमी|किलोमीटर)", re.U)
MAR_REF_LINE = re.compile(r"(शासन निर्णय|पत्र|तक्रार अर्ज|सुनावणी|क्रमांक|दिनांक)", re.U)

def parse_marathi_case(text: str) -> Dict:
    d = {
        "complainant_name": "", "complainant_village":"", "complainant_taluka":"",
        "hearing_date":"", "hearing_time":"", "distance_km":"", "attendees":[],
        "refs":[]
    }
    # candidate/complainant
    m = MAR_CAND.search(text)
    if m:
        d["complainant_name"] = f"{m.group(2)} {m.group(3)}".strip()
        d["complainant_village"] = (m.group(4) or "").strip()
        d["complainant_taluka"]  = (m.group(5) or "").strip()
    # hearing date/time
    mh = MAR_HEAR.search(text)
    if mh: d["hearing_date"] = mh.group(3)
    mht = MAR_HEAR_TIME.search(text)
    if mht:
        d["hearing_time"] = f"{mht.group(2)} {mht.group(4)}".replace("वा","वाजता")
    # distance mention
    md = MAR_DIST.search(text)
    if md: d["distance_km"] = md.group(0)
    # attendees (simple bullets after “उपस्थित होते”)
    if "उपस्थित होते" in text:
        block = text.split("उपस्थित होते",1)[-1].split("तक्रार",1)[0]
        lines = [ln.strip(" \n\t•-") for ln in block.splitlines() if ln.strip()]
        d["attendees"] = [ln for ln in lines if re.search(r"(श्री|श्रीमती|सौ\.)", ln)]
    # references
    for ln in text.splitlines():
        if MAR_REF_LINE.search(ln):
            d["refs"].append(ln.strip())
    # dedupe, shorten refs
    d["refs"] = list(dict.fromkeys(d["refs"]))[:8]
    return d

# ---------- Orders ----------
def order_marathi(meta: dict, decision: dict, facts: dict, gr_text: str) -> str:
    today = datetime.date.today().strftime("%d/%m/%Y")
    refs = decision.get("refs", []) or facts.get("refs", [])
    refs_md = "\n\t" + "\n\t".join([f"{i+1}.\t{r}" for i,r in enumerate(refs)]) if refs else "\n\t—"
    comp = facts.get("complainant_name") or "—"
    village = facts.get("complainant_village") or "—"
    taluka  = facts.get("complainant_taluka") or "—"
    hdate   = facts.get("hearing_date") or meta.get("hearing_date","—")
    htime   = facts.get("hearing_time") or "—"
    dist    = facts.get("distance_km") or "—"

    # Find a GR clause reference if present
    clause_hint = "शासन निर्णय दिनांकातील स्थानिक रहिवासी अटीचा भंग दिसून येतो."
    if "स्थानिक" in gr_text and "रहिवासी" in gr_text:
        clause_hint = "शासन निर्णयातील **स्थानिक रहिवासी** अटीचा भंग झाल्याचे नोंदीवरून दिसते."

    attendees = facts.get("attendees", [])
    att_block = ("\n\t" + "\n\t".join([f"{i+1}.\t{a}" for i,a in enumerate(attendees)]) ) if attendees else "\n\t—"

    return f"""📝 **निर्णय-आदेश (अर्धन्यायिक – मराठी मसुदा)**

**कार्यालय :** {meta['officer']}  
**फाईल क्र.:** {decision['case_id']}  
**विषय :** {decision['subject']}  
**दिनांक :** {today}

**संदर्भ :** {refs_md}

⸻

**प्रकरण :**  
सदर प्रकरण {taluka} तालुक्यातील **{village}** येथील अंगणवाडी मदतनीस पदावरील निवडीसंबंधी आहे. तक्रारकर्त्या **{comp}** यांनी निवड स्थानिक रहिवासी निकषांचा अवलंब न करता {dist} अंतरावरील उमेदवारास देण्यात आल्याचे मांडले आहे. सदरप्रमाणे सुनावणी **दिनांक {hdate} रोजी {htime}** घेण्यात आली.

**सुनावणीत उपस्थित:**{att_block}

**तपासणी व निष्कर्ष :**  
• शासन नोंदी व GR परीक्षणावरून {clause_hint}  
• ग्रामीण/आदिवासी प्रकल्पांत मदतनीस पदासाठी **संबंधित महसुली गावातील स्थानिक रहिवासी महिला** असणे आवश्यक.  
• उपलब्ध कागदपत्रांनुसार तक्रारकर्त्या पात्रता निकष (शैक्षणिक व स्थानिक) पूर्ण करतात.  
• त्यामुळे पूर्वनिवड GR विरुद्ध झालेली दिसते.

⸻

**आदेश :**  
1) नानकपठार येथील मदतनीस पदाची **पूर्वीची निवड रद्द** करण्यात येते.  
2) शासन निर्णयातील अटीप्रमाणे **स्थानीय पात्र उमेदवार** (**{comp}**, रा. {village}, ता. {taluka}) यांची निवड व नियुक्ती मान्य करण्यात येते.  
3) संबंधित प्रकल्प अधिकारी यांनी **७ (सात) दिवसांच्या** आत नियुक्ती आदेश निर्गमित करून अनुपालन अहवाल सादर करावा.  
4) जर कोणाकडे भूषणीय आक्षेप/अतिरीक्त कागदपत्रे असतील, तर ते **१५ दिवसांच्या** आत या कार्यालयास सादर करावीत.

**अपील :**  
वरील आदेशाविरुद्ध असमाधान असल्यास, लागू तरतुदीनुसार **६० दिवसांच्या** आत सक्षम प्राधिकरणाकडे अपील करता येईल.

⸻

(मुख्य कार्यकारी अधिकारी)  
जिल्हा परिषद, चंद्रपूर
"""

def order_english(meta: dict, decision: dict, facts: dict) -> str:
    today = datetime.date.today().strftime("%d/%m/%Y")
    comp   = facts.get("complainant_name") or "Complainant"
    village= facts.get("complainant_village") or "village"
    taluka = facts.get("complainant_taluka") or "taluka"
    return f"""📝 **Decision Order (Quasi-Judicial Draft)**

**Office:** {meta['officer']}  
**File No.:** {decision['case_id']}  
**Subject:** {decision['subject']}  
**Date:** {today}

**Order:**  
On consideration of the record and the applicable Government Resolution(s), it is found that the **local residency requirement** is mandatory for the post in question. The earlier selection appears contrary to the GR. The complainant **{comp}** of **{village}, {taluka}** satisfies the eligibility and local criteria.

**Directions:**  
1) The earlier selection is **hereby cancelled**.  
2) The concerned Project Officer shall **select and appoint the eligible local candidate ({comp})** and issue the appointment order within **7 days**.  
3) Compliance report be submitted thereafter.  
4) Any aggrieved person may file an appeal before the competent authority within **60 days** as per applicable provisions.

(Chief Executive Officer)  
Zilla Parishad, Chandrapur
"""

# ---------- UI Tabs ----------
t1, t2, t3, t4 = st.tabs(["1) Case Intake", "2) Documents", "3) Analyze", "4) Order"])

# Case Intake
with t1:
    st.markdown("<div class='section-title'>Case Intake</div>", unsafe_allow_html=True)
    c1,c2,c3 = st.columns([1.2,1.2,1])
    with c1:
        case_id   = st.text_input("File / Case ID", "ZP/CH/2025/0001")
        officer   = st.text_input("Officer", "मुख्य कार्यकारी अधिकारी, जिल्हा परिषद, चंद्रपूर")
        hearing_d = st.text_input("Hearing Date (dd/mm/yyyy)", "13/05/2025")
    with c2:
        subject_p = st.selectbox("Case Subject (pick)", [
            "Anganwadi Helper/Worker Selection",
            "Teacher Appointment (ZP School)",
            "Transfers / Service Matters",
            "Works Contract / Tender",
            "MGNREGA Wage Claim",
            "Procurement Irregularity",
            "Health (PHC/RH) Staffing",
            "ZP Benefit Eligibility",
            "Other"
        ], index=0)
        subject_f = st.text_input("Or type subject (free)", "अंगणवाडी मदतनीस निवडीबाबत निर्णय")
        subject   = subject_f.strip() or subject_p
    with c3:
        red_mode  = st.toggle("Sensitive mode (redact Aadhaar/PAN/Mobile)", value=True)
        preview_l = st.radio("Default Order Language", ["Marathi","English"], index=0, horizontal=True)
    st.caption("Subject & File No. appear in the order. Sensitive-mode masks numbers in previews.")

# Documents
with t2:
    st.markdown("<div class='section-title'>Documents — Case & GR (both mandatory)</div>", unsafe_allow_html=True)
    a,b = st.columns(2)
    with a:
        st.markdown("**📄 CASE** (PDF/TXT/Image)")
        case_up = st.file_uploader("Upload Case", type=["pdf","txt","png","jpg","jpeg","webp","tif","tiff"])
        case_txt_fallback = st.text_area("Or paste case text (fallback)", height=140)
    with b:
        st.markdown("**📑 GOVERNMENT GR** (PDF/TXT/Image)")
        gr_up   = st.file_uploader("Upload GR", type=["pdf","txt","png","jpg","jpeg","webp","tif","tiff"])
        gr_txt_fallback   = st.text_area("Or paste GR text (fallback)", height=140)

    refs_text = st.text_area("References (one per line)", 
        "महाराष्ट्र शासन, महिला व बालविकास विभाग शासन निर्णय क्रमांक एबावि-2022/प्र.क्र.94/का-6, दिनांक 02/02/2023\n"
        "मा. आयुक्त, ईबावि, नवी मुंबई यांचे पत्र, दिनांक 31/01/2025\n"
        "तक्रार अर्ज, दिनांक 28/03/2025\n"
        f"सुनावणी दिनांक : {hearing_d}"
    )

# Analyze
with t3:
    st.markdown("<div class='section-title'>Analyze (Extract facts & checks)</div>", unsafe_allow_html=True)
    run = st.button("Run Analysis", type="primary", use_container_width=True)
    if run:
        if not (case_up or case_txt_fallback.strip()):
            st.error("❌ Provide CASE file or pasted case text.")
        elif not (gr_up or gr_txt_fallback.strip()):
            st.error("❌ Provide GR file or pasted GR text.")
        else:
            # Read texts
            case_text = (case_txt_fallback.strip() or extract_any(case_up) or "").strip()
            gr_text   = (gr_txt_fallback.strip()   or extract_any(gr_up)   or "").strip()

            # Previews
            with st.expander("CASE Preview"):
                st.code(red(case_text[:1500]) if red_mode else case_text[:1500] or "—")
            with st.expander("GR Preview"):
                st.code(red(gr_text[:1500]) if red_mode else gr_text[:1500] or "—")
                if gr_text:
                    st.markdown("**Highlighted clauses/keywords**", unsafe_allow_html=True)
                    st.markdown(f"<div class='card'>{highlight_gr(gr_text)}</div>", unsafe_allow_html=True)

            # Parse facts
            facts = parse_marathi_case(case_text)

            # Decision skeleton
            decision = {
                "case_id": case_id,
                "subject": subject,
                "refs": [ln.strip() for ln in refs_text.splitlines() if ln.strip()][:10],
            }
            meta = {
                "officer": officer,
                "hearing_date": hearing_d,
            }

            st.session_state["decision"] = decision
            st.session_state["meta"]     = meta
            st.session_state["facts"]    = facts
            st.session_state["grtext"]   = gr_text

            st.success("Analysis complete.")
            with st.expander("Extracted facts (auto)"):
                st.json(facts)

# Order
with t4:
    st.markdown("<div class='section-title'>Order (Generate • Watermark • Signature)</div>", unsafe_allow_html=True)
    if "decision" not in st.session_state:
        st.info("Run **Analyze** first.")
    else:
        decision = st.session_state["decision"]
        meta     = st.session_state["meta"]
        facts    = st.session_state.get("facts", {})
        gr_text  = st.session_state.get("grtext","")

        # Controls
        col1,col2,col3 = st.columns([1.2,1.2,1])
        with col1:
            sign_name = st.text_input("Signatory Name", "(Name of CEO)")
            sign_desg = st.text_input("Designation", "Chief Executive Officer")
        with col2:
            sign_place = st.text_input("Place", "Chandrapur")
            sign_date  = st.text_input("Sign Date (dd/mm/yyyy)", datetime.date.today().strftime("%d/%m/%Y"))
        with col3:
            add_wm   = st.toggle("Watermark with State Emblem", value=True)
            show_sig = st.toggle("Include Signature Block", value=True)

        def sig_block(lang="mr"):
            if lang=="mr":
                return f"""
<div class="sig-block">
  <div class="sig-rows">
    <div><span class="sig-label">स्थान :</span> {sign_place}</div>
    <div><span class="sig-label">दिनांक :</span> {sign_date}</div>
  </div>
  <div style="height:36px"></div>
  <div class="sig-name">({sign_name})</div>
  <div class="sig-desig">{sign_desg}</div>
  <div>जिल्हा परिषद, चंद्रपूर</div>
  <div class="small">[कार्यालयीन शिक्का / Official Seal]</div>
</div>
"""
            else:
                return f"""
<div class="sig-block">
  <div class="sig-rows">
    <div><span class="sig-label">Place:</span> {sign_place}</div>
    <div><span class="sig-label">Date:</span> {sign_date}</div>
  </div>
  <div style="height:36px"></div>
  <div class="sig-name">({sign_name})</div>
  <div class="sig-desig">{sign_desg}</div>
  <div>Zilla Parishad, Chandrapur</div>
  <div class="small">[Office Seal / Official Stamp]</div>
</div>
"""

        # Build orders
        mr = order_marathi(meta, decision, facts, gr_text)
        en = order_english(meta, decision, facts)

        # Watermark wrapper
        wm_top = f"""<div class="order-block wm-wrap"><div class="wm-bg"><img src="{maha_emblem}"/></div><div class="order-content">""" if add_wm \
                 else """<div class="order-block"><div class="order-content">"""
        wm_bot = "</div></div>"

        # Marathi
        st.markdown("#### 📜 Marathi Order")
        st.markdown(wm_top + mr + (sig_block("mr") if show_sig else "") + wm_bot, unsafe_allow_html=True)
        mr_dl = mr + (f"\n\n({sign_name})\n{sign_desg}\nस्थान: {sign_place}  दिनांक: {sign_date}\n" if show_sig else "")
        st.download_button("Download (Marathi).md", mr_dl, file_name=f"{decision['case_id']}_Order_MR.md", use_container_width=True)

        # English
        st.markdown("#### 📜 English Order")
        st.markdown(wm_top + en + (sig_block("en") if show_sig else "") + wm_bot, unsafe_allow_html=True)
        en_dl = en + (f"\n\n({sign_name})\n{sign_desg}\nPlace: {sign_place}  Date: {sign_date}\n" if show_sig else "")
        st.download_button("Download (English).md", en_dl, file_name=f"{decision['case_id']}_Order_EN.md", use_container_width=True)
