# 📚 AI Study Buddy — a NotebookLM-style study workspace

Upload your own material, chat with it (with citations), and turn it into study tools.

## What you can do
| Area | Features |
|---|---|
| **Sources** (left) | Upload PDF / DOCX / TXT / MD / CSV · add a website or PDF URL · paste text · 🔎 *Discover* web sources (Tavily) · tick sources on/off · preview · remove |
| **Chat** (centre) | Answers grounded **only** in the ticked sources, with `[1] [2]` citations and the exact excerpts · suggested questions · 📌 save any answer to Notes |
| **Studio** (right) | Overview · Study guide · Briefing doc · FAQ · Timeline · Mind map · Flashcards · Audio overview (two-host script + gTTS audio) · download / pin to notes |
| **Study path** | Planner agent → Researcher agent. With sources, the plan and the notes come from *your documents*; without, from the web |
| **Quiz** | Quiz agent → you answer → Evaluator agent (score, weak topics, suggestions) → Retry agent on weak topics |
| **Notebooks** | Many notebooks, each with its own sources/chat/notes/outputs · Markdown export · JSON backup & restore |

Agent flow (LangGraph) is unchanged: `Planner → Researcher → Quiz → Evaluator → (Retry)`; the Context agent answers questions.

## Run locally
```bash
pip install -r requirements.txt
# pick ONE model backend:
set GEMINI_API_KEY=...        # or GROQ_API_KEY=...   (or just run Ollama with `mistral`)
streamlit run app.py
```
You can also paste keys in the app: sidebar → 🔑 Model & API keys (kept per browser session).

## Deploy on Streamlit Community Cloud
1. Push this repo to GitHub.
2. https://share.streamlit.io → **New app** → pick the repo, branch, main file `app.py`.
3. **Advanced settings → Secrets**: paste the contents of `.streamlit/secrets.toml.example` with your real key.
4. Deploy.

Notes: Ollama can't run on Streamlit Cloud, so use Gemini or Groq there. The cloud disk is
ephemeral — use sidebar → *Backup (JSON)* to keep a notebook; *Restore backup* brings it back.

## API (for the upcoming React frontend)
`api/` is a FastAPI wrapper over the same `studybuddy/` code (the Streamlit app is unchanged).
```bash
pip install -r api/requirements.txt
uvicorn api.main:app --reload --port 8000     # docs at http://localhost:8000/docs
```
One job per notebook (chat answer or studio tool) is enforced server-side (`409 job_active`); chat streams over SSE
and is cancelled when the client disconnects; studio jobs are started/polled/cancelled under `/api/notebooks/{id}/jobs`.
Deploy with `render.yaml` (set `GEMINI_API_KEY`, `CORS_ORIGINS`; attach the disk for persistence).
