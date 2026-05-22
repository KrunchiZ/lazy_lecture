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
import traceback
from pathlib import Path
import subprocess
import shutil
try:
    import imageio_ffmpeg as _imageio_ffmpeg  # optional fallback for environments without system ffmpeg
except Exception:
    _imageio_ffmpeg = None

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
GEMINI_MODEL_CANDIDATES = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]
LANGUAGE_HINT = ""                          # e.g. "en", "" to auto-detect
# Maximum safe upload size for Groq (MB). Can be overridden with env var GROQ_MAX_MB
GROQ_MAX_MB = int(os.getenv("GROQ_MAX_MB", "25"))
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
    --app-bg:#e9f1fb;
    --app-surface:#f8fbff;
    --app-text:#0a2a52;
    --app-heading:#062345;
    --app-muted:#446284;
    --app-border:#8aa8cf;
    --app-accent:#0b3d73;
    --app-accent-hover:#124d8f;
    --app-on-accent:#f8fbff;
    color-scheme: light dark;
}
@media (prefers-color-scheme: dark) {
    :root {
        --app-bg:#061120;
        --app-surface:#0b1d33;
        --app-text:#e8f1fc;
        --app-heading:#f6f9fe;
        --app-muted:#9db3cf;
        --app-border:#35547d;
        --app-accent:#2a5d99;
        --app-accent-hover:#3b72b4;
        --app-on-accent:#f6f9fe;
    }
}
html, body, [class*="css"], .stApp {
    background: var(--app-bg);
    color: var(--app-text);
    font-family: 'Inter', system-ui, sans-serif;
}
.stApp, .stApp p, .stApp li, .stApp label, .stApp span, .stApp small,
.stApp div[data-testid="stMarkdownContainer"], .stApp div[data-testid="stMarkdownContainer"] * {
    color: var(--app-text);
}
.stApp .block-container, .stApp .main {
    background: transparent !important;
}

h1, h2, h3, h4 { color: var(--app-heading) !important; letter-spacing:-0.01em; }
.stButton>button, .stDownloadButton>button, button {
    background: var(--app-accent) !important; color: var(--app-on-accent) !important;
    border:0 !important; padding: 0.55rem 1.1rem !important; font-weight:600 !important;
    box-shadow: none !important; background-image: none !important;
    -webkit-appearance: none !important; appearance: none !important; outline: none !important;
}
.stButton>button:hover, .stDownloadButton>button:hover, button:hover { background: var(--app-accent-hover) !important; }
.stProgress > div > div > div > div { background-color: var(--app-accent-hover); }
div[data-testid="stFileUploader"] section {
    background: var(--app-surface); border:1px dashed var(--app-border); border-radius:12px;
}
.notes-card {
    background:var(--app-surface); border-left:5px solid var(--app-accent);
    padding:1.25rem 1.5rem; border-radius:10px; margin-bottom:1rem;
    box-shadow: 0 1px 3px rgba(6,35,69,0.08);
}
.kpi {
    background:var(--app-accent); color:var(--app-on-accent); padding:1rem; border-radius:10px;
    text-align:center;
}
.kpi .v { font-size:1.6rem; font-weight:700; }
.kpi .l { font-size:0.8rem; opacity:0.9; text-transform:uppercase; letter-spacing:0.08em;}
hr { border-color: var(--app-border); }
/* Make all corners sharp */
* { border-radius: 0 !important; }
</style>
"""
st.markdown(NAVY_CSS, unsafe_allow_html=True)

EXTRA_CSS = """
<style>
/* Top banner / header */
header, .stApp header, div[role='banner'], div[role='toolbar'], nav {
    background: var(--app-bg) !important;
    color: var(--app-text) !important;
}
/* Buttons (primary and download) */
.stButton>button, .stDownloadButton>button, button {
    background: var(--app-accent) !important;
    color: var(--app-on-accent) !important;
    border: 0 !important; box-shadow: none !important; background-image: none !important;
    -webkit-appearance: none !important; appearance: none !important; outline: none !important;
}
/* Ensure SVG icons in buttons are visible */
button svg, .stButton>button svg, .stDownloadButton>button svg {
    fill: var(--app-on-accent) !important;
}
/* Sidebar / menu */
.stSidebar { background: var(--app-bg) !important; color: var(--app-text) !important; }
/* Centered caption helper */
.center-caption { text-align: center; color: var(--app-muted); display:block; width:100%; margin-top:0.25rem; }
/* Make links and emphasized text use blue tones */
a, a:visited { color: var(--app-accent) !important; }
  /* Streamlit expander header styling */
  [data-testid="stExpander"] details summary {
      background: var(--app-bg) !important;
      color: var(--app-text) !important;
      border: 1px solid var(--app-border) !important;
  }
  [data-testid="stExpander"] details[open] summary {
      background: var(--app-accent) !important;
      color: var(--app-on-accent) !important;
      border-color: var(--app-accent) !important;
  }
  [data-testid="stExpander"] details summary:hover {
      background: var(--app-bg) !important;
      color: var(--app-text) !important;
  }
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
<script>
    (function(){
        function hide200MB(){
            try{
                document.querySelectorAll('[data-testid="stFileUploader"] *').forEach(function(el){
                    if(el && el.innerText && el.innerText.includes('200 MB')){
                        el.style.display = 'none';
                    }
                });
            }catch(e){}
        }
        window.addEventListener('load', hide200MB);
        setTimeout(hide200MB, 500);
        new MutationObserver(hide200MB).observe(document.body, {childList:true, subtree:true});
    })();
</script>
"""
st.markdown(EXTRA_CSS, unsafe_allow_html=True)

# ---------- Header ----------
st.markdown("# Lecture Notes Generator")
st.markdown(
    "Upload a lecture **video or audio** file. We'll transcribe it with **Groq Whisper** "
    "and turn it into clean, structured notes with **Gemini**."
)

if "generated_result" not in st.session_state:
    st.session_state.generated_result = None

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

# If a file is present, check its size against the Groq limit so we don't accidentally
# use up the user's Groq quota. Use the uploaded.size attribute when available.
size_mb = None
if uploaded is not None:
    try:
        size_mb = (uploaded.size if hasattr(uploaded, 'size') else len(uploaded.getvalue())) / (1024 * 1024)
    except Exception:
        size_mb = None

is_video = False
ffmpeg_exe = shutil.which('ffmpeg')
if not ffmpeg_exe and _imageio_ffmpeg is not None:
    try:
        ffmpeg_exe = _imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        ffmpeg_exe = None
ffmpeg_available = ffmpeg_exe is not None
if uploaded is not None:
    try:
        is_video = Path(uploaded.name).suffix.lower() in {'.mp4', '.mov', '.mkv', '.webm', '.avi', '.flv'}
    except Exception:
        is_video = False

oversize = size_mb is not None and GROQ_MAX_MB is not None and size_mb > float(GROQ_MAX_MB)
override = False
if oversize and not is_video:
    st.warning(f"Uploaded file is {size_mb:.1f} MB — exceeds Groq safe limit of {GROQ_MAX_MB} MB.")
    override = st.checkbox("Override and allow uploading large file (use with caution)")
elif is_video and not ffmpeg_available:
    st.warning("Uploaded file is a video but ffmpeg is not available to auto-extract audio.")
    override = st.checkbox("Override and upload the original video (use with caution)")

current_result = st.session_state.generated_result

# Center the Generate Notes button and place the free-tier message below it
c1, c2, c3 = st.columns([1, 1, 1])
with c2:
    # Determine whether Generate should be enabled: videos auto-extract if ffmpeg present,
    # oversize non-video files require explicit override.
    if uploaded is None:
        disabled = True
    elif is_video:
        disabled = not (ffmpeg_available or override)
    else:
        disabled = oversize and not override
    run = st.button("Generate Notes", use_container_width=True, type="primary",
                    disabled=disabled)
    st.markdown("<div class='center-caption'>Groq free tier limits file size to ~25 MB.<br>"
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
                "type": "table" | "none",
                "content": "markdown table OR empty"
            }
     }
  ],
  "key_terms": [{"term":"...", "definition":"..."}],
  "questions": ["review question", ...],
  "study_materials": [
     {
        "resource": "Name of book, article, video, or concept",
        "description": "Why it's relevant and what it covers"
     }
  ]
}

Rules:
- Be faithful to the transcript for the core notes.
- Use visual elements (Markdown tables) to make content easy to digest.
    - Generate additional study materials/notes related to the discussed topics.
    - Prefer simple, compact tables that fit inside notes.
    - Do not use HTML or fenced code blocks for table content; output plain Markdown tables.
- Output JSON only. No prose, no code fences.

TRANSCRIPT:
\"\"\"
__TRANSCRIPT__
\"\"\"
"""

def summarize_with_gemini(transcript: str, api_key: str, model_name: str) -> dict:
    import urllib.request
    import urllib.error
    
    # Always use the GEMINI_API_KEY constant defined at the top of the app
    key = GEMINI_API_KEY
    if not key:
        raise ValueError("GEMINI_API_KEY is missing. Please set it at the top of app.py.")
    
    def available_models() -> list[str]:
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        req = urllib.request.Request(list_url, method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return [
            model.get("name", "").split("/")[-1]
            for model in payload.get("models", [])
            if "generateContent" in model.get("supportedGenerationMethods", [])
        ]

    prompt = NOTES_PROMPT.replace("__TRANSCRIPT__", transcript[:120_000])
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "responseMimeType": "application/json"
        }
    }

    model_candidates = [model_name] + [m for m in GEMINI_MODEL_CANDIDATES if m != model_name]
    try:
        supported = set(available_models())
        model_candidates = [m for m in model_candidates if m in supported] or model_candidates
    except Exception:
        pass

    last_error = None
    raw = None
    for selected_model in model_candidates:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model}:generateContent?key={key}"
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw = resp.read().decode("utf-8")
            break
        except urllib.error.HTTPError as he:
            msg = he.read().decode("utf-8")
            last_error = f"Gemini API Error {he.code} for {selected_model}: {msg}"
            if he.code != 404:
                raise RuntimeError(last_error)
        except Exception as e:
            last_error = f"Failed to call Gemini API with {selected_model}: {e}"

    if raw is None:
        raise RuntimeError(last_error or "Failed to call Gemini API")
        
    data = json.loads(raw)
    try:
        txt = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        raise RuntimeError(f"Unexpected response format from Gemini: {raw[:500]}")
        
    txt = txt.strip()
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        cleaned = txt.strip("`").lstrip("json").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            raise RuntimeError(f"Failed to parse JSON response: {txt[:200]}")



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
            if vt == "table" and content:
                st.markdown(content)
            elif content:
                st.code(content, language="text")

    terms = notes.get("key_terms", [])
    if terms:
        st.markdown("### Key Terms")
        for t in terms:
            st.markdown(f"- **{t.get('term','')}** — {t.get('definition','')}")

    materials = notes.get("study_materials", [])
    if materials:
        st.markdown("### 📚 Additional Study Materials")
        for m in materials:
            st.markdown(f"- **{m.get('resource','')}**: {m.get('description','')}")
            
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
        if v.get("type") == "table" and v.get("content"):
            lines += ["", v["content"]]
        elif v.get("content"):
            lines += ["", "```", v["content"], "```"]
    if notes.get("key_terms"):
        lines += ["", "## Key Terms"]
        lines += [f"- **{t.get('term','')}** — {t.get('definition','')}"
                  for t in notes["key_terms"]]
    if notes.get("study_materials"):
        lines += ["", "## Additional Study Materials"]
        lines += [f"- **{m.get('resource','')}**: {m.get('description','')}"
                  for m in notes["study_materials"]]

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
    filename = uploaded.name
    size_mb = len(file_bytes) / (1024 * 1024)
    st.info(f"`{filename}` — {size_mb:.1f} MB")

    # If the file is a video and ffmpeg is available, always extract audio automatically
    if is_video and ffmpeg_available:
        st.info("Video detected — extracting audio with ffmpeg…")
        in_path = None
        out_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as in_tmp:
                in_tmp.write(file_bytes)
                in_path = in_tmp.name
            with tempfile.NamedTemporaryFile(delete=False, suffix='.m4a') as out_tmp:
                out_path = out_tmp.name
            cmd = [ffmpeg_exe, '-y', '-i', in_path, '-vn', '-ac', '1', '-ar', '16000', '-b:a', '64k', out_path]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0 and out_path and os.path.exists(out_path):
                file_bytes = open(out_path, 'rb').read()
                filename = f"{Path(filename).stem}.m4a"
                size_mb = len(file_bytes) / (1024 * 1024)
                st.info(f"Extracted audio: {size_mb:.1f} MB — sending to Groq")
            else:
                # Extraction failed
                if not override:
                    st.error("Automatic audio extraction failed (ffmpeg error). Enable override to proceed with the original file.")
                    raise SystemExit
                else:
                    st.warning("Automatic extraction failed; proceeding with original file as override requested.")
        except SystemExit:
            st.stop()
        except Exception as e:
            if not override:
                st.error(f"Audio extraction failed: {e}. Enable override to proceed.")
                st.stop()
            else:
                st.warning("Audio extraction failed; proceeding with original file as override requested.")
        finally:
            try:
                if in_path and os.path.exists(in_path):
                    os.unlink(in_path)
                if out_path and os.path.exists(out_path):
                    os.unlink(out_path)
            except Exception:
                pass

    with st.status("Transcribing with Groq Whisper…", expanded=False) as s:
        try:
            transcript = transcribe_with_groq(
                file_bytes, filename, _groq_key, WHISPER_MODEL, LANGUAGE_HINT
            )
            s.update(label="Transcription complete", state="complete")
        except Exception as e:
            s.update(label="Transcription failed", state="error")
            st.exception(e); st.stop()

    with st.expander("Full transcript", expanded=False):
        st.text_area(" ", transcript, height=240, label_visibility="collapsed")

    with st.status("Summarizing with Gemini…", expanded=False) as s:
        try:
            notes = summarize_with_gemini(transcript, _gemini_key, GEMINI_MODEL_CANDIDATES[0])
            s.update(label="Notes generated", state="complete")
        except Exception as e:
            s.update(label="Summarization failed", state="error")
            st.exception(e); st.stop()

    st.session_state.generated_result = {
        "filename": uploaded.name,
        "transcript": transcript,
        "notes": notes,
    }
    current_result = st.session_state.generated_result

if current_result:
    transcript = current_result["transcript"]
    notes = current_result["notes"]

    st.markdown("---")
    render_notes(notes)

    md = notes_to_markdown(notes)
    st.download_button("⬇️ Download notes (Markdown)", md,
                       file_name=f"{Path(current_result['filename']).stem}_notes.md",
                       mime="text/markdown")
    st.download_button("⬇️ Download transcript (TXT)", transcript,
                       file_name=f"{Path(current_result['filename']).stem}_transcript.txt",
                       mime="text/plain")
else:
    st.markdown("---")
    st.markdown(
        "#### How it works\n"
        "1. **Upload** an audio or video recording of your lecture.\n"
        "2. **Download** the notes as Markdown."
    )
