"""FastAPI wrapper around studybuddy/ + the existing LangGraph agents.

Run:  uvicorn api.main:app --reload --port 8000
No business logic lives here: it adapts HTTP <-> the same functions the Streamlit app uses.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel

from api import jobs
from studybuddy import store, tasks
from studybuddy.llm import status as llm_status
from studybuddy.sources import extract_file, fetch_url, fetch_youtube, make_source, youtube_id
from studybuddy.studio import (
    DEFAULT_TITLES, STUDIO, ask, enabled_sources, generate, make_audio, suggest_questions, suggest_title,
)

MAX_UPLOAD = 50 * 1024 * 1024
EMOJIS = ["📘", "🧬", "🧠", "🔭", "📐", "🏛️", "💡", "🌍", "⚗️", "📊", "🎨", "⚖️"]
JOB_KINDS = tasks.JOB_KINDS

app = FastAPI(title="AI Study Buddy API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()],
    allow_origin_regex=os.getenv("CORS_ORIGIN_REGEX") or None,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------- errors
class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, retryable: bool = False, **extra):
        self.status, self.code, self.message, self.retryable, self.extra = status, code, message, retryable, extra


def _err(status, code, message, retryable=False, **extra):
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "retryable": retryable, **extra}},
    )


@app.exception_handler(ApiError)
async def _api_error(_: Request, e: ApiError):
    return _err(e.status, e.code, e.message, e.retryable, **e.extra)


@app.exception_handler(jobs.NotFound)
async def _not_found(_: Request, e: jobs.NotFound):
    return _err(404, "not_found", "Not found")


@app.exception_handler(jobs.Busy)
async def _busy(_: Request, e: jobs.Busy):
    return _err(409, "job_active", f"{e.job.label} is still running. Stop it or wait.", True, active_job=e.job.public())


def _busy_guard(nb_id: str):
    """Mutations that change the context (sources) are refused while a job runs."""
    j = jobs.active(nb_id)
    if j:
        raise jobs.Busy(j)


# ---------------------------------------------------------------- serialisers
def emoji_for(nb: dict) -> str:
    return nb.get("emoji") or EMOJIS[sum(map(ord, nb["id"])) % len(EMOJIS)]


def source_public(s: dict, full: bool = False) -> dict:
    out = {k: s.get(k) for k in ("id", "name", "kind", "url", "chars", "enabled", "added")}
    out["status"] = "ready"
    if full:
        out["text"] = s["text"]
    return out


def output_public(oid: str, o: dict, full: bool = False) -> dict:
    base = {"id": oid, "kind": o.get("kind", oid), "title": o.get("title", oid), "created": o.get("created")}
    if o.get("audio_ready"):
        base["audio_ready"] = True
    if full:
        base.update({k: v for k, v in o.items() if k not in base})
    return base


def track_public(t: dict, full: bool = False) -> dict:
    base = {"id": t["id"], "topic": t.get("topic"), "grounded": t.get("grounded", False),
            "has_quiz": bool(t.get("quiz_questions")), "quiz_score": t.get("quiz_score")}
    if full:
        base.update({k: t.get(k) for k in (
            "subtopics", "study_notes", "quiz_questions", "user_answers", "weak_topics", "analysis",
            "suggestions", "quiz_round")})
        # never leak answers before the quiz is submitted
        if t.get("quiz_score") is None and base.get("quiz_questions"):
            base["quiz_questions"] = [{k: v for k, v in q.items() if k != "answer"} for q in base["quiz_questions"]]
    return base


def notebook_public(nb: dict) -> dict:
    j = jobs.active(nb["id"])
    return {
        "id": nb["id"], "title": nb["title"], "emoji": emoji_for(nb), "created": nb["created"],
        "modified": nb["modified"],
        "sources": [source_public(s) for s in nb["sources"]],
        "messages": nb["messages"], "notes": nb["notes"],
        "outputs": [output_public(k, v) for k, v in nb["outputs"].items() if isinstance(v, dict)],
        "study": [track_public(t) for t in nb["study"]],
        "active_job": j.public() if j else None,
    }


# --------------------------------------------------------------------- health
@app.get("/api/health")
def health():
    return {"ok": True, "model": llm_status(), "time": datetime.now().isoformat(timespec="seconds")}


# ------------------------------------------------------------------ notebooks
class NotebookIn(BaseModel):
    title: str | None = None
    emoji: str | None = None


@app.get("/api/notebooks")
def list_notebooks(q: str = "", sort: str = "recent"):
    items = store.list_notebooks()
    out = []
    for i in items:
        nb = store.load(i["id"])
        out.append({"id": i["id"], "title": i["title"], "emoji": emoji_for(nb), "modified": i["modified"],
                    "source_count": i["n_sources"]})
    if q:
        out = [n for n in out if q.lower() in n["title"].lower()]
    if sort == "title":
        out.sort(key=lambda n: n["title"].lower())
    return out


@app.post("/api/notebooks", status_code=201)
def create_notebook(body: NotebookIn):
    nb = store.new_notebook(body.title or "Untitled notebook")
    if body.emoji:
        nb["emoji"] = body.emoji
    store.save(nb)
    return notebook_public(nb)


@app.get("/api/notebooks/{nid}")
def get_notebook(nid: str):
    return notebook_public(jobs.read(nid))


@app.patch("/api/notebooks/{nid}")
def patch_notebook(nid: str, body: NotebookIn):
    with jobs.edit(nid) as nb:
        if body.title is not None and body.title.strip():
            nb["title"] = body.title.strip()[:120]
        if body.emoji:
            nb["emoji"] = body.emoji
    return notebook_public(jobs.read(nid))


@app.delete("/api/notebooks/{nid}", status_code=204)
def delete_notebook(nid: str):
    jobs.read(nid)
    _busy_guard(nid)
    store.delete(nid)
    return Response(status_code=204)


@app.delete("/api/notebooks/{nid}/messages", status_code=204)
def clear_messages(nid: str):
    _busy_guard(nid)
    with jobs.edit(nid) as nb:
        nb["messages"] = []
    return Response(status_code=204)


# -------------------------------------------------------------------- sources
class UrlIn(BaseModel):
    url: str


class TextIn(BaseModel):
    title: str = "Pasted text"
    text: str


class SourcePatch(BaseModel):
    name: str | None = None
    enabled: bool | None = None


class EnabledIn(BaseModel):
    ids: list[str] | str  # list of ids, or "all" / "none"


def _add_source(nid: str, src: dict) -> dict:
    if len(src["text"]) < 20:
        raise ApiError(422, "no_text", "No readable text was found in that source (scanned PDF?).")
    with jobs.edit(nid) as nb:
        nb["sources"].append(src)
        if nb["title"] in DEFAULT_TITLES:  # auto-name from the first source
            nb["title"] = suggest_title(nb) or src["name"].rsplit(".", 1)[0][:50]
    return source_public(src)


@app.post("/api/notebooks/{nid}/sources", status_code=201)
async def upload_source(nid: str, file: UploadFile = File(...)):
    jobs.read(nid)
    _busy_guard(nid)
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise ApiError(413, "too_large", "File is larger than 50 MB.")
    name = file.filename or "upload"
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in {"pdf", "docx", "txt", "md", "csv"}:
        raise ApiError(415, "unsupported", "Supported types: PDF, DOCX, TXT, MD, CSV.")
    try:
        text = extract_file(name, data)
    except Exception as e:
        raise ApiError(422, "extract_failed", f"Couldn't read {name}: {e}")
    return _add_source(nid, make_source(name, ext if ext in ("pdf", "docx") else "text", text))


@app.post("/api/notebooks/{nid}/sources/url", status_code=201)
def add_url(nid: str, body: UrlIn):
    jobs.read(nid)
    _busy_guard(nid)
    url = body.url.strip()
    try:
        if youtube_id(url):
            title, text = fetch_youtube(url)
            return _add_source(nid, make_source(title[:80], "youtube", text, url=url))
        title, text = fetch_url(url)
    except ValueError as e:
        raise ApiError(422, "fetch_failed", str(e))
    except Exception as e:
        raise ApiError(422, "fetch_failed", f"Couldn't fetch that URL: {e}")
    return _add_source(nid, make_source(title[:80], "url", text, url=url))


@app.post("/api/notebooks/{nid}/sources/text", status_code=201)
def add_text(nid: str, body: TextIn):
    jobs.read(nid)
    _busy_guard(nid)
    return _add_source(nid, make_source(body.title.strip() or "Pasted text", "text", body.text))


@app.put("/api/notebooks/{nid}/sources/enabled", status_code=204)
def set_enabled(nid: str, body: EnabledIn):
    _busy_guard(nid)
    with jobs.edit(nid) as nb:
        for s in nb["sources"]:
            if body.ids == "all":
                s["enabled"] = True
            elif body.ids == "none":
                s["enabled"] = False
            else:
                s["enabled"] = s["id"] in body.ids
    return Response(status_code=204)


@app.get("/api/notebooks/{nid}/sources/{sid}")
def get_source(nid: str, sid: str):
    nb = jobs.read(nid)
    for s in nb["sources"]:
        if s["id"] == sid:
            return source_public(s, full=True)
    raise jobs.NotFound(sid)


@app.patch("/api/notebooks/{nid}/sources/{sid}")
def patch_source(nid: str, sid: str, body: SourcePatch):
    if body.enabled is not None:  # changes the chat context
        _busy_guard(nid)
    with jobs.edit(nid) as nb:
        for s in nb["sources"]:
            if s["id"] == sid:
                if body.name and body.name.strip():
                    s["name"] = body.name.strip()[:120]
                if body.enabled is not None:
                    s["enabled"] = body.enabled
                return source_public(s)
    raise jobs.NotFound(sid)


@app.delete("/api/notebooks/{nid}/sources/{sid}", status_code=204)
def delete_source(nid: str, sid: str):
    _busy_guard(nid)
    with jobs.edit(nid) as nb:
        nb["sources"] = [s for s in nb["sources"] if s["id"] != sid]
    return Response(status_code=204)


# ----------------------------------------------------------------------- chat
class ChatIn(BaseModel):
    message: str
    style: str = "default"  # default | concise | detailed


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/api/notebooks/{nid}/chat")
def chat(nid: str, body: ChatIn):
    msg = body.message.strip()
    if not msg:
        raise ApiError(422, "empty", "Message is empty.")
    jobs.read(nid)
    job = jobs.begin(nid, "chat", "Answering")  # 409 if anything else is running
    try:
        with jobs.edit(nid) as nb:
            nb["messages"].append({"id": "m" + uuid.uuid4().hex[:8], "role": "user", "content": msg})
            if nb["title"] in DEFAULT_TITLES:
                nb["title"] = msg[:40]
        nb_snapshot = jobs.read(nid)
    except BaseException:
        jobs.finish(job, "failed", "setup failed")
        raise
    mid = "m" + uuid.uuid4().hex[:8]

    def gen():
        text, cites, stopped, error, stream = "", [], False, None, None
        try:
            stream, cites = ask(nb_snapshot, msg, style=body.style)
            yield _sse("start", {"message_id": mid, "job_id": job.id, "citations": [
                {"n": c["n"], "source": c["source"], "text": c["text"]} for c in cites]})
            for tok in stream:
                if job.cancel.is_set():
                    stopped = True
                    break
                text += tok
                yield _sse("token", {"t": tok})
        except GeneratorExit:  # client disconnected -> cancel server-side
            stopped = True
            raise
        except Exception as e:  # noqa: BLE001
            error = str(e) or type(e).__name__
        finally:
            if stream is not None and hasattr(stream, "close"):
                stream.close()  # closes the upstream LLM request
            try:
                if text or error:
                    with jobs.edit(nid) as nb:
                        m = {"id": mid, "role": "assistant", "content": text or f"⚠️ {error}",
                             "savable": bool(text), "stopped": stopped}
                        if cites:
                            m["citations"] = [{"n": c["n"], "source": c["source"], "text": c["text"]} for c in cites]
                        nb["messages"].append(m)
            except jobs.NotFound:
                pass
            jobs.finish(job, "failed" if error else ("cancelled" if stopped else "done"), error)
        if error:
            yield _sse("error", {"message": error, "retryable": True})
        elif not stopped:
            yield _sse("done", {"message_id": mid})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


class FeedbackIn(BaseModel):
    value: str | None = None  # up | down | null


@app.post("/api/notebooks/{nid}/messages/{mid}/feedback", status_code=204)
def feedback(nid: str, mid: str, body: FeedbackIn):
    if body.value not in (None, "up", "down"):
        raise ApiError(422, "bad_value", "value must be 'up', 'down' or null")
    with jobs.edit(nid) as nb:
        for m in nb["messages"]:
            if m["id"] == mid:
                m["feedback"] = body.value
                return Response(status_code=204)
    raise jobs.NotFound(mid)


@app.post("/api/notebooks/{nid}/messages/{mid}/save-note", status_code=201)
def save_note(nid: str, mid: str):
    with jobs.edit(nid) as nb:
        for m in nb["messages"]:
            if m["id"] == mid:
                title = (m["content"].strip().splitlines() or ["Note"])[0].strip("#*_` ")[:50] or "Note"
                note = {"id": "n" + uuid.uuid4().hex[:8], "title": title, "content": m["content"]}
                nb["notes"].append(note)
                return note
    raise jobs.NotFound(mid)


@app.get("/api/notebooks/{nid}/suggestions")
def suggestions(nid: str):
    nb = jobs.read(nid)
    cached = nb.get("suggested")
    if cached and cached.get("n_sources") == len(enabled_sources(nb)):
        return {"questions": cached["questions"]}
    if jobs.active(nid) or not enabled_sources(nb):
        return {"questions": (cached or {}).get("questions", [])}
    try:
        qs = suggest_questions(nb)
    except Exception:
        qs = []
    with jobs.edit(nid) as nb2:
        nb2["suggested"] = {"n_sources": len(enabled_sources(nb2)), "questions": qs}
    return {"questions": qs}


# ----------------------------------------------------------------------- jobs
class JobIn(BaseModel):
    kind: str
    options: dict | None = None


def _find_track(nb: dict, tid: str) -> dict:
    for t in nb["study"]:
        if t["id"] == tid:
            return t
    raise ApiError(404, "track_not_found", "Study path not found.")


def _make_work(nb: dict, kind: str, o: dict):
    try:
        return tasks.make_work(nb, kind, o)
    except tasks.TaskError as e:
        raise ApiError(404 if e.code == "track_not_found" else 422, e.code, e.message)


@app.post("/api/notebooks/{nid}/jobs", status_code=202)
def start_job(nid: str, body: JobIn):
    if body.kind not in JOB_KINDS:
        raise ApiError(422, "bad_kind", f"Unknown job kind '{body.kind}'.")
    nb = jobs.read(nid)
    o = body.options or {}
    work = _make_work(nb, body.kind, o)  # validates before taking the lock
    job = jobs.begin(nid, body.kind, tasks.label(body.kind))
    jobs.run_in_thread(job, work)
    return job.public()


@app.get("/api/notebooks/{nid}/jobs/active")
def active_job(nid: str):
    jobs.read(nid)
    j = jobs.active(nid)
    return j.public() if j else None


@app.get("/api/notebooks/{nid}/jobs/{jid}")
def job_status(nid: str, jid: str):
    return jobs.get(nid, jid).public()


@app.post("/api/notebooks/{nid}/jobs/{jid}/cancel")
def cancel_job(nid: str, jid: str):
    return jobs.cancel(nid, jid).public()


# -------------------------------------------------------------------- outputs
class TitleIn(BaseModel):
    title: str


@app.get("/api/notebooks/{nid}/outputs/{oid}")
def get_output(nid: str, oid: str):
    nb = jobs.read(nid)
    o = nb["outputs"].get(oid)
    if not isinstance(o, dict):
        raise jobs.NotFound(oid)
    return output_public(oid, o, full=True)


@app.patch("/api/notebooks/{nid}/outputs/{oid}")
def rename_output(nid: str, oid: str, body: TitleIn):
    with jobs.edit(nid) as nb:
        if oid not in nb["outputs"]:
            raise jobs.NotFound(oid)
        nb["outputs"][oid]["title"] = body.title.strip()[:120] or nb["outputs"][oid].get("title", oid)
        return output_public(oid, nb["outputs"][oid])


@app.delete("/api/notebooks/{nid}/outputs/{oid}", status_code=204)
def delete_output(nid: str, oid: str):
    with jobs.edit(nid) as nb:
        nb["outputs"].pop(oid, None)
    return Response(status_code=204)


@app.get("/api/notebooks/{nid}/outputs/{oid}/audio.mp3")
def get_audio(nid: str, oid: str):
    p = os.path.join(store.DIR, "..", "audio", nid, f"{oid}.mp3")
    if not os.path.exists(p):
        raise jobs.NotFound(oid)
    return FileResponse(p, media_type="audio/mpeg")


# ---------------------------------------------------------------------- notes
class NoteIn(BaseModel):
    title: str = ""
    content: str


@app.post("/api/notebooks/{nid}/notes", status_code=201)
def add_note(nid: str, body: NoteIn):
    with jobs.edit(nid) as nb:
        note = {"id": "n" + uuid.uuid4().hex[:8], "title": body.title.strip() or body.content[:40], "content": body.content}
        nb["notes"].append(note)
        return note


@app.patch("/api/notebooks/{nid}/notes/{note_id}")
def patch_note(nid: str, note_id: str, body: NoteIn):
    with jobs.edit(nid) as nb:
        for n in nb["notes"]:
            if n["id"] == note_id:
                n["title"] = body.title.strip() or n["title"]
                n["content"] = body.content
                return n
    raise jobs.NotFound(note_id)


@app.delete("/api/notebooks/{nid}/notes/{note_id}", status_code=204)
def delete_note(nid: str, note_id: str):
    with jobs.edit(nid) as nb:
        nb["notes"] = [n for n in nb["notes"] if n["id"] != note_id]
    return Response(status_code=204)


# ---------------------------------------------------------------- study paths
@app.get("/api/notebooks/{nid}/study/{tid}")
def get_track(nid: str, tid: str):
    return track_public(_find_track(jobs.read(nid), tid), full=True)


@app.delete("/api/notebooks/{nid}/study/{tid}", status_code=204)
def delete_track(nid: str, tid: str):
    with jobs.edit(nid) as nb:
        nb["study"] = [t for t in nb["study"] if t["id"] != tid]
    return Response(status_code=204)
