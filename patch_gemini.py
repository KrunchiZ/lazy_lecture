import re

with open("app.py", "r") as f:
    code = f.read()

# Replace NOTES_PROMPT to end of summarize_with_gemini
pattern = r"NOTES_PROMPT\s*=\s*\"\"\"You are an expert.*?def summarize_with_gemini[^>]+>\s*(?:dic[t]?|None):\n.*?def render_mermaid"
replacement = """NOTES_PROMPT = \"\"\"You are an expert academic note-taker.
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
- Use visual elements (mermaid or tables) to make it easy to digest.
- Generate additional study materials/notes related to the discussed topics.
- Keep mermaid diagrams small (<=10 nodes) and syntactically valid.
- Output JSON only. No prose, no code fences.

TRANSCRIPT:
\"\"\"
__TRANSCRIPT__
\"\"\"
\"\"\"

def summarize_with_gemini(transcript: str, api_key: str, model_name: str) -> dict:
    import urllib.request
    import urllib.error
    
    # Always use the GEMINI_API_KEY constant defined at the top of the app
    key = GEMINI_API_KEY
    if not key:
        raise ValueError("GEMINI_API_KEY is missing. Please set it at the top of app.py.")
    
    prompt = NOTES_PROMPT.replace("__TRANSCRIPT__", transcript[:120_000])
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
    
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "responseMimeType": "application/json"
        }
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as he:
        msg = he.read().decode("utf-8")
        raise RuntimeError(f"Gemini API Error {he.code}: {msg}")
    except Exception as e:
        raise RuntimeError(f"Failed to call Gemini API: {e}")
        
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

def render_mermaid"""

new_code = re.sub(pattern, replacement, code, flags=re.DOTALL)
if new_code == code:
    print("WARNING: First regex failed")

# Replace render_notes insertions
render_pattern = r"(st\.markdown\(f\"- \*\*\{t\.get\('term',''\)\}\*\* — \{t\.get\('definition',''\)\}\"\)\n\n)\s*qs = notes\.get\(\"questions\""

render_replacement = r"""\1    materials = notes.get("study_materials", [])
    if materials:
        st.markdown("### 📚 Additional Study Materials")
        for m in materials:
            st.markdown(f"- **{m.get('resource','')}**: {m.get('description','')}")
            
    qs = notes.get("questions\""""

new_code = re.sub(render_pattern, render_replacement, new_code)

if "Additional Study Materials" not in new_code:
    print("WARNING: Second regex failed")

# Add study_materials to notes_to_markdown
md_pattern = r"(lines \+= \[f\"- \*\*\{t\.get\('term',''\)\}\*\* — \{t\.get\('definition',''\)\}\"[\s\n]*for t in notes\[\"key_terms\"\]\]\n)\s*if notes\.get\(\"questions\"\):"

md_replacement = r"""\1    if notes.get("study_materials"):
        lines += ["", "## Additional Study Materials"]
        lines += [f"- **{m.get('resource','')}**: {m.get('description','')}"
                  for m in notes["study_materials"]]

    if notes.get("questions"):\n"""

new_code = re.sub(md_pattern, md_replacement, new_code, flags=re.DOTALL)


with open("app.py", "w") as f:
    f.write(new_code)
print("done")
