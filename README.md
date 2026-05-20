# Lecture Notes Generator (Streamlit)

Turn a lecture recording into clean, structured study notes.

- **Speech-to-text:** Groq Whisper (free tier)
- **Summarization:** Google Gemini (free tier)
- **UI:** Navy-blue monochrome theme
- **Output:** Title, TL;DR, key bullets, sectioned notes with visual aids (Mermaid diagrams / tables), key terms, and self-check questions. Downloadable as Markdown.

## 1. Install

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Get free API keys

- **Groq:** https://console.groq.com/keys
- **Gemini:** https://aistudio.google.com/app/apikey

Paste them in the sidebar at runtime, or export them:

```bash
export GROQ_API_KEY=...
export GEMINI_API_KEY=...
```

## 3. Run locally

```bash
streamlit run app.py
```

## 4. Deploy on Streamlit Community Cloud

1. Push `app.py` and `requirements.txt` to a GitHub repo.
2. Go to https://share.streamlit.io, connect the repo, choose `app.py`.
3. In **App → Settings → Secrets**, add:
   ```toml
   GROQ_API_KEY = "your_key"
   GEMINI_API_KEY = "your_key"
   ```
4. Deploy.

## Notes & limits

- Groq's audio endpoint caps file size around **25 MB**. For larger lectures, extract the audio first:
  ```bash
  ffmpeg -i lecture.mp4 -vn -ac 1 -ar 16000 -b:a 64k lecture.m4a
  ```
- Transcripts beyond ~120k characters are trimmed before summarization. For multi-hour lectures, consider chunking.
- Mermaid diagrams render in the browser via CDN.
