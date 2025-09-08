# -*- coding: utf-8 -*-
"""
Government Quasi-Judicial AI System — Zilla Parishad, Chandrapur
Fixes in this version:
- Strong contrast: dark-blue masthead (white text), black body text
- Works even if assets/ images missing
- Branding panel to upload State Emblem + ZP banner at runtime
- Mandatory Case+GR & detailed Marathi order with extracted facts
"""

import io, os, re, datetime, tempfile, base64, pathlib
from typing import List, Tuple, Dict
import streamlit as st
import numpy as np
from PIL import Image

# ───────────────── PAGE / THEME ─────────────────
st.set_page_config(page_title="Government Quasi-Judicial AI — ZP Chandrapur", layout="wide")

# Strong contrast styles (no white-on-white)
st.markdown("""
<style>
:root{
  --gov:#0B3A82; --gov2:#11408a; --ink:#0b1220; --muted:#475569;
  --line:#e5e7eb; --wash:#f8fafc; --ok:#1a7f37; --warn:#b58100; --bad:#b42318;
}
html, body { background:#ffffff; color:var(--ink); }
.block-container { max-width: 1180px !important; padding-top: 0 !important; }

/* Masthead: deep blue bg with white text */
.mast{
  display:flex;align-items:center;gap:16px;padding:14px 16px;
  background: linear-gradient(180deg,var(--gov),var(--gov2));
  border-bottom:1px solid rgba(0,0,0,.08); margin-bottom:12px; color:#ffffff;
}
.mast-left{display:flex;align-items:center;gap:12px}
.mast-right{margin-left:auto}
.mast h1{font-size:1.08rem;margin:0;font-weight:800;color:#ffffff}
.mast .sub{font-size:.92rem;color:#eaf0ff}

/* Section / cards */
.section-title{margin:18px 0 8px 0;padding:10px 12px;border:1px solid var(--line);
  border-left:4px solid var(--gov);border-radius:8px;background:var(--wash);font-weight:700;color:var(--ink)}
.card{border:1px solid var(--line);border-radius:12px;padding:16px;background:#fff;color:var(--ink)}

/* Tabs */
.stTabs [data-baseweb="tab-list"]{gap:6px}
.stTabs [role="tab"]{padding:10px 14px;border-radius:10px 10px 0 0;background:#f3f4f6;border:1px solid var(--line);border-bottom:none;font-weight:600;color:#111827}
.stTabs [aria-selected="true"]{background:#ffffff;border-bottom:1px solid #fff}

/* Order block + highlight */
.order-block{border:1px solid var(--line);border-radius:10px;padding:22px;background:#fff;color:var(--ink)}
.hl{background:#fff3cd;border-bottom:2px solid #facc15}

/* Watermark */
.wm-wrap{position:relative}
.wm-bg{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;pointer-events:none;z-index:0}
.wm-bg img{opacity:.10;width:46%;min-width:260px;max-width:520px;filter:grayscale(100%)}
.order-content{position:relative;z-index:1}

/* Signature block */
.sig-block{margin-top:24px;padding-top:12px;border-top:1px dashed var(--line);line-height:1.45;color:var(--ink)}
.sig-rows{display:grid;grid-template-columns:1fr 1fr;gap:10px 24px}
.sig-label{color:#6b7280;font-size:.92rem}
.sig-name{font-weight:700}

/* Alerts */
.alert-warn{border-left:4px solid var(--warn);padding:10px 12px;background:#fffaf0;color:var(--ink)}
</style>
""", unsafe_allow_html=True)

# ───────────────── BRANDING (works even if assets missing) ─────────────────
ASSETS = pathlib.Path(__file__).parent / "assets"

def _b64_file(path: pathlib.Path) -> str:
    if path.exists():
        return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("utf-8")
    return ""

# placeholders (white icons on blue bg) if files not present
PLACE_EMBLEM = """data:image/svg+xml;base64,{}""".format(base64.b64encode(
b'''<svg xmlns="http://www.w3.org/2000/svg" width="70" height="70"><rect width="100%" height="100%" fill="#0B3A82"/><text x="50%" y="55%" fill="#ffffff" font-size="12" font-family="Arial" text-anchor="middle">STATE</text></svg>'''
).decode("utf-8"))
PLACE_BANNER = """data:image/svg+xml;base64,{}""".format(base64.b64encode(
b'''<svg xmlns="http://www.w3.org/2000/svg" width="360" height="46"><rect width="100%" height="100%" fill="#ffffff"/><text x="50%" y="60%" fill="#0B3A82" font-size="18" font-family="Arial" text-anchor="middle">Zilla Parishad Chandrapur</text></svg>'''
).decode("utf-8"))

# load from assets if present, else placeholders
maha_emblem = _b64_file(ASSETS / "maha_emblem.png") or PLACE_EMBLEM
zp_banner   = _b64_file(ASSETS / "zp_chandrapur_banner.png") or PLACE_BANNER

# Sidebar: Branding overrides
with st.sidebar:
    st.markdown("### Branding / Logos")
    st.caption("Upload logos if you don’t see your official images.")
    em_up = st.file_uploader("State Emblem (PNG/SVG)", type=["png","svg"], key="emblem")
    bn_up = st.file_uploader("ZP Banner (PNG/SVG)", type=["png","svg"], key="banner")
    if em_up:
        mahadata = em_up.read()
        if em_up.name.lower().endswith(".svg"):
            maha_emblem = "data:image/svg+xml;base64,"+base64.b64encode(mahadata).decode("utf-8")
        else:
            maha_emblem = "data:image/png;base64,"+base64.b64encode(mahadata).decode("utf-8")
    if bn_up:
        bnd = bn_up.read()
        if bn_up.name.lower().endswith(".svg"):
            zp_banner = "data:image/svg+xml;base64,"+base64.b64encode(bnd).decode("utf-8")
        else:
            zp_banner = "data:image/png;base64,"+base64.b64encode(bnd).decode("utf-8")

# Masthead (now always dark-blue with white text)
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

# ───────────────── UTILITIES / EXTRACTION ─────────────────
DEVN = re.compile(r"[\u0900-\u097F]")
AADHAAR = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
PAN     = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
MOBILE  = re.compile(r"\b[6-9]\d{9}\b")

def redact(s:str)->str:
    s = AADHAAR.sub("XXXX XXXX XXXX", s)
    s = PAN.sub("XXXXX9999X", s)
    s = MOBILE.sub("XXXXXXXXXX", s)
    return s

def read_txt(b: bytes) -> str:
    for enc in ("utf-8","utf-8-sig","utf-16","utf-16le","utf-16be"):
        try: return b.decode(enc)
        except: pass
    return b.decode("latin-1","ignore")

def extract_text_pdf(pdf: bytes) -> str:
    text = ""
    try:
        import fitz
        doc = fitz.open(stream=pdf, filetype="pdf")
        text = "\n".join([p.get_text("text") for p in doc]).strip()
        doc.close()
    except: pass
    if len(text) < 60:
        try:
            from pdfminer.high_level import extract_text
            with tempfile.NamedTemporaryFile(delete=False,suffix=".pdf") as tmp:
                tmp.write(pdf); p=tmp.name
            t2 = extract_text(p) or ""
            try: os.unlink(p)
            except: pass
            if DEVN.search(t2) or len(t2)>len(text): text = t2
        except: pass
    if len(text) < 50:
        try:
            from pypdf import PdfReader
            r = PdfReader(io.BytesIO(pdf))
            t3 = "\n".join([(pg.extract_text() or "") for pg in r.pages]).strip()
            if DEVN.search(t3) or len(t3)>len(text): text = t3
        except: pass
    return text.strip()

def easyocr_text(img_bytes: bytes) -> str:
    try:
        import easyocr
        reader = easyocr.Reader(["mr","hi","en"], gpu=False, verbose=False)
        arr = np.array(Image.open(io.BytesIO(img_bytes)).convert("RGB"))
        lines = reader.readtext(arr, detail=0, paragraph=True)
        return "\n".join(lines).strip()
    except:
        return ""

def extract_any(file) -> str:
    name = (file.name or "").lower()
    data = file.read()
    if name.endswith(".txt"):  return read_txt(data)
    if name.endswith(".pdf"):  return extract_text_pdf(data)
    if name.endswith((".png",".jpg",".jpeg",".webp",".tif",".tiff")): return easyocr_text(data)
    return ""

# GR highlighter
_CLAUSE = re.compile("|".join([
    r"(कलम\s*\d+[A-Za-z]?)", r"(धोरण\s*\d+)", r"(अट\s*\d+)",
    r"(Clause\s*\d+)", r"(Section\s*\d+[A-Za-z]?)"
]), re.I)
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

# Marathi fact parser
MAR_CAND = re.compile(r"(सौ\.|श्री\.?)\s*([अ-ह][^\s,]*)\s+([अ-ह][^,]*)[, ]+\s*रा\.\s*([अ-ह][^,]*)(?:,\s*ता\.\s*([अ-ह][^,]*))?", re.U)
MAR_HEAR = re.compile(r"(सुनावणी)\s*(दिनांक|दिनाँक|दि\.?)\s*[:\-]?\s*(\d{1,2}/\d{1,2}/\d{4})", re.U)
MAR_HEAR_TIME = re.compile(r"(सकाळी|सायंकाळी)\s*([०-९0-9]{1,2}(\.[0-9]+)?)\s*(वा|वाजता)", re.U)
MAR_DIST = re.compile(r"(\d+|\d+[\.]\d+|[०-९]+)\s*(कि\.?मी\.?|किमी|किलोमीटर)", re.U)
MAR_REF_LINE = re.compile(r"(शासन निर्णय|पत्र|तक्रार अर्ज|सुनावणी|क्रमांक|दिनांक)", re.U)

def parse_marathi_case(text: str) -> Dict:
    d = {
        "complainant_name":"", "complainant_village":"", "complainant_taluka":"",
        "hearing_date":"", "hearing_time":"", "distance_km":"", "attendees":[], "refs":[]
    }
    m = MAR_CAND.search(text)
    if m:
        d["complainant_name"] = f"{m.group(2)} {m.group(3)}".strip()
        d["complainant_village"] = (m.group(4) or "").strip()
        d["complainant_taluka"]  = (m.group(5) or "").strip()
    mh = MAR_HEAR.search(text)
    if mh: d["hearing_date"] = mh.group(3)
    mht = MAR_HEAR_TIME.search(text)
    if mht: d["hearing_time"] = f"{mht.group(2)} वाजता"
    md = MAR_DIST.search(text)
    if md: d["distance_km"] = md.group(0)
    if "उपस्थित होते" in text:
        block = text.split("उपस्थित होते",1)[-1].split("तक्रार",1)[0]
        lines = [ln.strip(" \n\t•-") for ln in block.splitlines() if ln.strip()]
        d["attendees"] = [ln for ln in lines if re.search(r"(श्री|श्रीमती|सौ\.)", ln)]
    for ln in text.splitlines():
        if MAR_REF_LINE.search(ln):
            d["refs"].append(ln.strip())
    d["refs"] = list(dict.fromkeys(d["refs"]))[:8]
    return d

# Order builders (Marathi & English)
def order_marathi(meta: dict, decision: dict, facts: dict, gr_text: str) -> str:
    today = datetime.date.today().strftime("%d/%m/%Y")
    refs = decision.get("refs", []) or facts.get("refs", [])
    refs_md = "\n\t" + "\n\t".join([f"{i+1}.\t{r}" for i,r in enumerate(refs)]) if refs else "\n\t—"
    comp   = facts.get("complainant_name") or "—"
    village= facts.get("complainant_village") or "—"
    taluka = facts.get("complainant_taluka") or "—"
    hdate  = facts.get("hearing_date") or meta.get("hearing_date","—")
    htime  = facts.get("hearing_time") or "—"
    dist   = facts.get("distance_km") or "—"
    attendees = facts.get("attendees", [])
    att_block = ("\n\t" + "\n\t".join([f"{i+1}.\t{a}" for i,a in enumerate(attendees)]) ) if attendees else "\n\t—"
    clause_hint = "शासन निर्णयातील **स्थानिक रहिवासी** अटीचा भंग झाल्याचे दिसते." if ("स्थानिक" in gr_text and "रहिवासी" in gr_text) else "शासन निर्णयानुसार स्थानिक निकष लागू."

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
• उपलब्ध GR व नोंदी परीक्षणावरून – {clause_hint}  
• ग्रामीण/आदिवासी प्रकल्पांत मदतनीस पदासाठी **संबंधित महसुली गावातील स्थानिक रहिवासी महिला** असणे आवश्यक.  
• सहज उपलब्ध कागदपत्रांनुसार तक्रारकर्त्या पात्रता निकष (शैक्षणिक व स्थानिक) पूर्ण करतात.  
• त्यामुळे पूर्वनिवड GR विरुद्ध झालेली दिसते.

⸻

**आदेश :**  
1) नानकपठार येथील मदतनीस पदाची **पूर्वीची निवड रद्द** करण्यात येते.  
2) शासन निर्णयातील अटीप्रमाणे **स्थानीय पात्र उमेदवार** (**{comp}**, रा. {village}, ता. {taluka}) यांची निवड व नियुक्ती मान्य करण्यात येते.  
3) संबंधित प्रकल्प अधिकारी यांनी **७ (सात) दिवसांच्या** आत नियुक्ती आदेश निर्गमित करून अनुपालन अहवाल सादर करावा.  
4) कोणाकडे वस्तुनिष्ठ आक्षेप/अतिरीक्त कागदपत्रे असल्यास, ते **१५ दिवसांच्या** आत या कार्यालयास सादर करावीत.

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
On consideration of the record and applicable Government Resolution(s), the **local residency** requirement is mandatory. The earlier selection appears contrary to the GR. The complainant **{comp}** of **{village}, {taluka}** satisfies the eligibility and local criteria.

**Directions:**  
1) The earlier selection is **hereby cancelled**.  
2) The concerned Project Officer shall **select and appoint the eligible local candidate ({comp})** and issue the appointment order within **7 days**.  
3) Compliance report be submitted thereafter.  
4) Any aggrieved person may file an appeal before the competent authority within **60 days** as per applicable provisions.

(Chief Executive Officer)  
Zilla Parishad, Chandrapur
"""

# ───────────────── UI ─────────────────
t1, t2, t3, t4 = st.tabs(["1) Case Intake", "2) Documents", "3) Analyze", "4) Order"])

with t1:
    st.markdown("<div class='section-title'>Case Intake</div>", unsafe_allow_html=True)
    c1,c2,c3 = st.columns([1.2,1.2,1])
    with c1:
        case_id = st.text_input("File / Case ID", "ZP/CH/2025/0001")
        officer = st.text_input("Officer", "मुख्य कार्यकारी अधिकारी, जिल्हा परिषद, चंद्रपूर")
        hearing_d = st.text_input("Hearing Date (dd/mm/yyyy)", "13/05/2025")
    with c2:
        subject_p = st.selectbox("Case Subject (pick)", [
            "Anganwadi Helper/Worker Selection","Teacher Appointment (ZP School)","Transfers / Service Matters",
            "Works Contract / Tender","MGNREGA Wage Claim","Procurement Irregularity","Health (PHC/RH) Staffing",
            "ZP Benefit Eligibility","Other"
        ], index=0)
        subject_f = st.text_input("Or type subject (free)", "अंगणवाडी मदतनीस निवडीबाबत निर्णय")
        subject = subject_f.strip() or subject_p
    with c3:
        red_mode = st.toggle("Sensitive mode (mask Aadhaar/PAN/Mobile)", value=True)
        lang_pref = st.radio("Default Order Language", ["Marathi","English"], index=0, horizontal=True)
    st.caption("Subject & File No. appear in the order. Sensitive-mode masks numbers in previews.")

with t2:
    st.markdown("<div class='section-title'>Documents — Case & GR (both mandatory)</div>", unsafe_allow_html=True)
    a,b = st.columns(2)
    with a:
        st.markdown("**📄 CASE** (PDF/TXT/Image)")
        case_up = st.file_uploader("Upload Case", type=["pdf","txt","png","jpg","jpeg","webp","tif","tiff"])
        case_txt = st.text_area("Or paste case text (fallback)", height=140)
    with b:
        st.markdown("**📑 GOVERNMENT GR** (PDF/TXT/Image)")
        gr_up = st.file_uploader("Upload GR", type=["pdf","txt","png","jpg","jpeg","webp","tif","tiff"])
        gr_txt = st.text_area("Or paste GR text (fallback)", height=140)
    refs_text = st.text_area("References (one per line)",
        "महाराष्ट्र शासन, महिला व बालविकास विभाग शासन निर्णय क्रमांक एबावि-2022/प्र.क्र.94/का-6, दिनांक 02/02/2023\n"
        "मा. आयुक्त, ईबावि, नवी मुंबई यांचे पत्र, दिनांक 31/01/2025\n"
        "तक्रार अर्ज, दिनांक 28/03/2025\n"
        f"सुनावणी दिनांक : {hearing_d}"
    )

with t3:
    st.markdown("<div class='section-title'>Analyze (Extract facts & checks)</div>", unsafe_allow_html=True)
    if st.button("Run Analysis", type="primary", use_container_width=True):
        if not (case_up or case_txt.strip()):
            st.error("❌ Provide CASE file or paste case text.")
        elif not (gr_up or gr_txt.strip()):
            st.error("❌ Provide GR file or paste GR text.")
        else:
            ctext = (case_txt.strip() or extract_any(case_up) or "").strip()
            gtext = (gr_txt.strip()   or extract_any(gr_up)   or "").strip()
            with st.expander("CASE Preview"):
                st.code(red(ctext[:1500]) if red_mode else ctext[:1500] or "—")
            with st.expander("GR Preview"):
                st.code(red(gtext[:1500]) if red_mode else gtext[:1500] or "—")
                if gtext:
                    st.markdown("**Highlighted clauses/keywords**", unsafe_allow_html=True)
                    st.markdown(f"<div class='card'>{highlight_gr(gtext)}</div>", unsafe_allow_html=True)
            facts = parse_marathi_case(ctext)
            decision = {"case_id": case_id, "subject": subject, "refs":[ln.strip() for ln in refs_text.splitlines() if ln.strip()][:10]}
            meta = {"officer": officer, "hearing_date": hearing_d}
            st.session_state["facts"]=facts; st.session_state["decision"]=decision; st.session_state["meta"]=meta; st.session_state["grtext"]=gtext
            st.success("Analysis complete.")
            with st.expander("Extracted facts"):
                st.json(facts)

with t4:
    st.markdown("<div class='section-title'>Order (Generate • Watermark • Signature)</div>", unsafe_allow_html=True)
    if "decision" not in st.session_state:
        st.info("Run **Analyze** first.")
    else:
        decision = st.session_state["decision"]; meta = st.session_state["meta"]; facts = st.session_state["facts"]; gtext = st.session_state["grtext"]
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
  <div class="sig-rows"><div><span class="sig-label">स्थान :</span> {sign_place}</div><div><span class="sig-label">दिनांक :</span> {sign_date}</div></div>
  <div style="height:36px"></div>
  <div class="sig-name">({sign_name})</div><div class="sig-desg">{sign_desg}</div><div>जिल्हा परिषद, चंद्रपूर</div>
</div>"""
            return f"""
<div class="sig-block">
  <div class="sig-rows"><div><span class="sig-label">Place:</span> {sign_place}</div><div><span class="sig-label">Date:</span> {sign_date}</div></div>
  <div style="height:36px"></div>
  <div class="sig-name">({sign_name})</div><div class="sig-desg">{sign_desg}</div><div>Zilla Parishad, Chandrapur</div>
</div>"""

        mr = order_marathi(meta, decision, facts, gtext)
        en = order_english(meta, decision, facts)
        wm_top = f"""<div class="order-block wm-wrap"><div class="wm-bg"><img src="{maha_emblem}"/></div><div class="order-content">""" if add_wm else """<div class="order-block"><div class="order-content">"""
        wm_bot = "</div></div>"

        st.markdown("#### 📜 Marathi Order")
        st.markdown(wm_top + mr + (sig_block("mr") if show_sig else "") + wm_bot, unsafe_allow_html=True)
        st.download_button("Download (Marathi).md",
                           mr + (f"\n\n({sign_name})\n{sign_desg}\nस्थान: {sign_place}  दिनांक: {sign_date}\n" if show_sig else ""),
                           file_name=f"{decision['case_id']}_Order_MR.md", use_container_width=True)

        st.markdown("#### 📜 English Order")
        st.markdown(wm_top + en + (sig_block("en") if show_sig else "") + wm_bot, unsafe_allow_html=True)
        st.download_button("Download (English).md",
                           en + (f"\n\n({sign_name})\n{sign_desg}\nPlace: {sign_place}  Date: {sign_date}\n" if show_sig else ""),
                           file_name=f"{decision['case_id']}_Order_EN.md", use_container_width=True)
