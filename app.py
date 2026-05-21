"""
Lecture Notes Generator — Streamlit app
- Upload a lecture video/audio
- Transcribe with Groq (Whisper, free-tier)
- Summarize into structured notes with Google Gemini (free-tier)
- Monochromatic blue UI

>>> PASTE YOUR API KEYS BELOW <<<
"""

import os
import json
import tempfile
from pathlib import Path

import streamlit as st
from groq import Groq
import google.genai as genai

# ============================================================
# 🔑 PUT YOUR API KEYS HERE
# ============================================================
GROQ_API_KEY   = st.secrets["GROQ_API_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# Models (free-tier friendly defaults)
WHISPER_MODEL = "whisper-large-v3"   # or "whisper-large-v3"
GEMINI_MODEL  = "gemini-2.0-flash"         # or "gemini-1.5-flash" / "gemini-1.5-pro"
LANGUAGE_HINT = ""                          # e.g. "en", "" to auto-detect
# ============================================================

# ---------- Page config & theme ----------
st.set_page_config(
    page_title="Lecture Notes Generator",
    page_icon="📖",
    layout="wide",
)

NAVY_CSS = """
<style>
:root {
    --blue-900:#052c5b;
    --blue-800:#0a3b73;
    --blue-700:#0e4f8f;
    --blue-600:#1666b1;
    --blue-500:#2a84c9;
    --blue-300:#8fbde8;
    --blue-100:#eef7ff;
}
html, body, [class*="css"], .stApp {
    background: var(--blue-100);
    color: var(--blue-900);
    font-family: 'Inter', system-ui, sans-serif;
}
.stApp .block-container, .stApp .main {
    background: transparent !important;
}

h1, h2, h3, h4 { color: var(--blue-800) !important; letter-spacing:-0.01em; }
.stButton>button, .stDownloadButton>button, button {
    background: var(--blue-700) !important; color: var(--blue-100) !important;
    border:0 !important; padding: 0.55rem 1.1rem !important; font-weight:600 !important;
    box-shadow: none !important; background-image: none !important;
    -webkit-appearance: none !important; appearance: none !important; outline: none !important;
}
.stButton>button:hover, .stDownloadButton>button:hover, button:hover { background: var(--blue-600) !important; }
.stProgress > div > div > div > div { background-color: var(--blue-600); }
div[data-testid="stFileUploader"] section {
    background: white; border:1px dashed var(--blue-500); border-radius:12px;
}
.notes-card {
    background:white; border-left:5px solid var(--blue-700);
    padding:1.25rem 1.5rem; border-radius:10px; margin-bottom:1rem;
    box-shadow: 0 1px 3px rgba(10,54,91,0.06);
}
.kpi {
    background:var(--blue-700); color:white; padding:1rem; border-radius:10px;
    text-align:center;
}
.kpi .v { font-size:1.6rem; font-weight:700; }
.kpi .l { font-size:0.8rem; opacity:0.9; text-transform:uppercase; letter-spacing:0.08em;}
hr { border-color: var(--blue-300); }
/* Make all corners sharp */
* { border-radius: 0 !important; }
</style>
"""
st.markdown(NAVY_CSS, unsafe_allow_html=True)

EXTRA_CSS = """
<style>
/* Top banner / header */
header, .stApp header, div[role='banner'], div[role='toolbar'], nav {
    background: var(--blue-100) !important;
    color: var(--blue-900) !important;
}
/* Buttons (primary and download) */
.stButton>button, .stDownloadButton>button, button {
    background: var(--blue-700) !important;
    color: #ffffff !important;
    border: 0 !important; box-shadow: none !important; background-image: none !important;
    -webkit-appearance: none !important; appearance: none !important; outline: none !important;
}
/* Ensure SVG icons in buttons are visible */
button svg, .stButton>button svg, .stDownloadButton>button svg {
    fill: #ffffff !important;
}
/* Sidebar / menu */
.stSidebar { background: var(--blue-100) !important; color: var(--blue-900) !important; }
/* Centered caption helper */
.center-caption { text-align: center; color: var(--blue-900); display:block; width:100%; margin-top:0.25rem; }
/* Make links and emphasized text use blue tones */
a, a:visited { color: var(--blue-700) !important; }
/* Normalize header / top-bar action buttons to consistent size */
header button, div[role='toolbar'] button, [data-testid="stHeader"] button,
.css-1v3fvcr button, .css-1d391kg button {
    height: 36px !important;
    min-width: 36px !important;
    padding: 6px 10px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-sizing: border-box !important;
}
header button svg, div[role='toolbar'] button svg { width:16px !important; height:16px !important; }
</style>
"""
st.markdown(EXTRA_CSS, unsafe_allow_html=True)

# ---------- Header ----------
st.markdown("# Lecture Notes Generator")
st.markdown(
    "Upload a lecture **video or audio** file. We'll transcribe it with **Groq Whisper** "
    "and turn it into clean, structured notes with **Gemini**."
)

# Resolve keys (constants above, or env vars as a fallback)
_groq_key = GROQ_API_KEY if GROQ_API_KEY and not GROQ_API_KEY.startswith("paste-") \
    else os.getenv("GROQ_API_KEY", "")
_gemini_key = GEMINI_API_KEY if GEMINI_API_KEY and not GEMINI_API_KEY.startswith("paste-") \
    else os.getenv("GEMINI_API_KEY", "")

if not _groq_key or not _gemini_key:
    st.warning(
        "Open `app.py` and paste your **Groq** and **Gemini** API keys at the top of the file "
        "(constants `GROQ_API_KEY` and `GEMINI_API_KEY`)."
    )

uploaded = st.file_uploader(
    "Drop a lecture file here",
    type=["mp3", "wav", "m4a", "mp4", "mov", "mkv", "webm", "ogg", "flac"],
    accept_multiple_files=False,
)

# Center the Generate Notes button and place the free-tier message below it
c1, c2, c3 = st.columns([1, 1, 1])
with c2:
    run = st.button("Generate Notes", use_container_width=True, type="primary",
                    disabled=uploaded is None)
    st.markdown("<div class='center-caption'>Groq free tier limits file size to ~25 MB.\n"
                "For larger lectures, extract audio first (e.g. with ffmpeg).</div>",
                unsafe_allow_html=True)

# ---------- Helpers ----------
def transcribe_with_groq(file_bytes: bytes, filename: str, api_key: str,
                         model: str, lang: str) -> str:
    client = Groq(api_key=api_key)
    suffix = Path(filename).suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        with open(tmp_path, "rb") as f:
            kwargs = dict(file=(filename, f.read()), model=model,
                          response_format="text")
            if lang.strip():
                kwargs["language"] = lang.strip()
            result = client.audio.transcriptions.create(**kwargs)
        return result if isinstance(result, str) else getattr(result, "text", str(result))
    finally:
        try: os.unlink(tmp_path)
        except OSError: pass


NOTES_PROMPT = """You are an expert academic note-taker.
Given the raw transcript of a lecture, produce concise, easy-to-digest study notes.

Return STRICT JSON with this schema:
{
  "title": "short lecture title",
  "tldr": "2-3 sentence summary",
  "key_points": ["bullet", "bullet", ...],
  "sections": [
     {
        "heading": "section name",
        "bullets": ["point", "point", ...],
        "visual": {
            "type": "mermaid" | "table" | "none",
            "content": "mermaid code OR markdown table OR empty"
        }
     }
  ],
  "key_terms": [{"term":"...", "definition":"..."}],
  "questions": ["review question", ...]
}

Rules:
- Be faithful to the transcript; do not invent facts.
- Prefer short bullets over paragraphs.
- Include at least one helpful visual (mermaid diagram OR markdown table) where it aids understanding.
- Keep mermaid diagrams small (<=10 nodes) and syntactically valid.
- Output JSON only. No prose, no code fences.

TRANSCRIPT:
\"\"\"
__TRANSCRIPT__
\"\"\"
"""

def summarize_with_gemini(transcript: str, api_key: str, model_name: str) -> dict:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    prompt = NOTES_PROMPT.replace("__TRANSCRIPT__", transcript[:120_000])
    resp = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json",
                           "temperature": 0.3},
    )
    txt = resp.text.strip()
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        cleaned = txt.strip("`").lstrip("json").strip()
        return json.loads(cleaned)


def render_mermaid(code: str):
    html = f"""
    <div class="mermaid">{code}</div>
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{ startOnLoad: true, theme: 'base',
                themeVariables: {{ primaryColor:'#0e4f8f', primaryTextColor:'#ffffff',
                                                     lineColor:'#1666b1', fontFamily:'Inter' }}}});
      mermaid.run();
    </script>
    """
    st.components.v1.html(html, height=380, scrolling=True)


def render_notes(notes: dict):
    st.markdown(f"## {notes.get('title', 'Lecture Notes')}")
    st.markdown(f"<div class='notes-card'><b>TL;DR.</b> {notes.get('tldr','')}</div>",
                unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='kpi'><div class='v'>{len(notes.get('key_points',[]))}</div>"
                f"<div class='l'>Key points</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi'><div class='v'>{len(notes.get('sections',[]))}</div>"
                f"<div class='l'>Sections</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi'><div class='v'>{len(notes.get('key_terms',[]))}</div>"
                f"<div class='l'>Key terms</div></div>", unsafe_allow_html=True)

    st.markdown("### Key Points")
    for b in notes.get("key_points", []):
        st.markdown(f"- {b}")

    st.markdown("### Sections")
    for s in notes.get("sections", []):
        with st.expander(s.get("heading", "Section"), expanded=True):
            for b in s.get("bullets", []):
                st.markdown(f"- {b}")
            v = s.get("visual") or {}
            vt = v.get("type", "none")
            content = (v.get("content") or "").strip()
            if vt == "mermaid" and content:
                render_mermaid(content)
            elif vt == "table" and content:
                st.markdown(content)

    terms = notes.get("key_terms", [])
    if terms:
        st.markdown("### Key Terms")
        for t in terms:
            st.markdown(f"- **{t.get('term','')}** — {t.get('definition','')}")

    qs = notes.get("questions", [])
    if qs:
        st.markdown("### Self-Check Questions")
        for q in qs:
            st.markdown(f"- {q}")


def notes_to_markdown(notes: dict) -> str:
    lines = [f"# {notes.get('title','Lecture Notes')}", "",
             f"**TL;DR.** {notes.get('tldr','')}", "", "## Key Points"]
    lines += [f"- {b}" for b in notes.get("key_points", [])]
    for s in notes.get("sections", []):
        lines += ["", f"## {s.get('heading','Section')}"]
        lines += [f"- {b}" for b in s.get("bullets", [])]
        v = s.get("visual") or {}
        if v.get("type") == "mermaid" and v.get("content"):
            lines += ["", "```mermaid", v["content"], "```"]
        elif v.get("type") == "table" and v.get("content"):
            lines += ["", v["content"]]
    if notes.get("key_terms"):
        lines += ["", "## Key Terms"]
        lines += [f"- **{t.get('term','')}** — {t.get('definition','')}"
                  for t in notes["key_terms"]]
    if notes.get("questions"):
        lines += ["", "## Self-Check Questions"]
        lines += [f"- {q}" for q in notes["questions"]]
    return "\n".join(lines)


# ---------- Main flow ----------
if run and uploaded is not None:
    if not _groq_key or not _gemini_key:
        st.error("Please paste your Groq and Gemini API keys at the top of `app.py`.")
        st.stop()

    file_bytes = uploaded.read()
    size_mb = len(file_bytes) / (1024 * 1024)
    st.info(f"`{uploaded.name}` — {size_mb:.1f} MB")

    with st.status("Transcribing with Groq Whisper…", expanded=False) as s:
        try:
            transcript = transcribe_with_groq(
                file_bytes, uploaded.name, _groq_key, WHISPER_MODEL, LANGUAGE_HINT
            )
            s.update(label="Transcription complete", state="complete")
        except Exception as e:
            s.update(label="Transcription failed", state="error")
            st.exception(e); st.stop()

    with st.expander("Full transcript", expanded=False):
        st.text_area(" ", transcript, height=240, label_visibility="collapsed")

    with st.status("Summarizing with Gemini…", expanded=False) as s:
        try:
            notes = summarize_with_gemini(transcript, _gemini_key, GEMINI_MODEL)
            s.update(label="Notes generated", state="complete")
        except Exception as e:
            s.update(label="Summarization failed", state="error")
            st.exception(e); st.stop()

    st.markdown("---")
    render_notes(notes)

    md = notes_to_markdown(notes)
    st.download_button("⬇️ Download notes (Markdown)", md,
                       file_name=f"{Path(uploaded.name).stem}_notes.md",
                       mime="text/markdown")
    st.download_button("⬇️ Download transcript (TXT)", transcript,
                       file_name=f"{Path(uploaded.name).stem}_transcript.txt",
                       mime="text/plain")
else:
    st.markdown("---")
    st.markdown(
        "#### How it works\n"
        "1. **Upload** an audio or video recording of your lecture.\n"
        "2. **Download** the notes as Markdown."
    )
