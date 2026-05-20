# Lecture Notes Generator (Streamlit)

Turn a lecture recording into clean, structured study notes.

- **Speech-to-text:** Groq Whisper (free tier)
- **Summarization:** Google Gemini (free tier)
- **Output:** Title, TL;DR, key bullets, sectioned notes with visual aids (Mermaid diagrams / tables), key terms, and self-check questions. Downloadable as Markdown.

## 1. Run locally

```bash
streamlit run app.py
```

## 2. Deploy on Streamlit Community Cloud

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
