"""Background task definitions shared by the API and the Streamlit app.

make_work(nb, kind, options) validates up front and returns work(job) -> commit(nb) -> output_id.
Compute runs unlocked in a worker thread; commit() is applied under the notebook lock by api.jobs.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime

from studybuddy import store
from studybuddy.studio import STUDIO, enabled_sources, generate, make_audio

JOB_KINDS = set(STUDIO) | {"audio_render", "study_path", "quiz", "quiz_retry", "quiz_submit"}


class TaskError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def label(kind: str) -> str:
    if kind in STUDIO:
        return f"Generating {STUDIO[kind][1]}"
    return {"audio_render": "Rendering audio", "study_path": "Building study path",
            "quiz": "Generating quiz", "quiz_retry": "Generating retry quiz",
            "quiz_submit": "Marking quiz"}[kind]


def sources_for_agents(nb: dict) -> list[dict]:
    return [{"id": s["id"], "name": s["name"], "text": s["text"]} for s in enabled_sources(nb)]


def make_work(nb: dict, kind: str, o: dict | None = None):
    o = o or {}
    if kind in STUDIO:
        if not enabled_sources(nb):
            raise TaskError("no_sources", "Add and enable at least one source first.")

        def work(job):
            out = generate(kind, nb, o)

            def commit(n):
                oid = f"{kind}-{uuid.uuid4().hex[:6]}"
                out.update(id=oid, created=datetime.now().isoformat(timespec="seconds"))
                n["outputs"][oid] = out
                return oid
            return commit
        return work

    if kind == "audio_render":
        oid = o.get("output_id")
        out = nb["outputs"].get(oid)
        if not out or not out.get("segments"):
            raise TaskError("bad_output", "Pick an Audio overview output to render.")

        def work(job):
            data = make_audio(out["segments"])
            if not data:
                raise RuntimeError("Audio synthesis failed (gTTS needs internet access).")
            d = os.path.join(store.DIR, "..", "audio", nb["id"])
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, f"{oid}.mp3"), "wb") as f:
                f.write(data)

            def commit(n):
                n["outputs"][oid]["audio_ready"] = True
                return oid
            return commit
        return work

    # agent pipelines (imported lazily: they pull in langgraph)
    from day9_pipeline.evaluator_graph import evaluation_graph
    from day9_pipeline.graph import graph
    from day9_pipeline.quiz_graph import quiz_graph
    from day9_pipeline.retry_graph import retry_graph

    if kind == "study_path":
        topic = (o.get("topic") or "").strip()
        if not topic:
            raise TaskError("no_topic", "options.topic is required.")

        def work(job):
            srcs = sources_for_agents(nb)
            r = graph.invoke({"topic": topic, "sources": srcs, "subtopics": [], "study_notes": [],
                              "quiz_questions": [], "user_answers": [], "quiz_score": None, "weak_topics": [],
                              "retry_count": 0, "analysis": "", "suggestions": ""})
            r.pop("sources", None)
            r.update(id="t" + uuid.uuid4().hex[:8], grounded=bool(srcs))

            def commit(n):
                n["study"].append(r)
                return r["id"]
            return commit
        return work

    track = next((t for t in nb["study"] if t.get("id") == o.get("track_id")), None)
    if track is None:
        raise TaskError("track_not_found", "Study path not found.")
    tid = track["id"]

    def replace(n, new):
        new.pop("sources", None)
        # LangGraph drops keys outside AgentState, so re-attach the app-level fields
        new["id"] = tid
        new["grounded"] = track.get("grounded", False)
        new.setdefault("quiz_round", track.get("quiz_round", 0))
        for i, t in enumerate(n["study"]):
            if t["id"] == tid:
                n["study"][i] = new
        return tid

    if kind in ("quiz", "quiz_retry"):
        def work(job):
            g = quiz_graph if kind == "quiz" else retry_graph
            out = g.invoke({**track, "sources": sources_for_agents(nb)})
            out.update(quiz_score=None, analysis="", suggestions="", user_answers=[], weak_topics=[],
                       quiz_round=track.get("quiz_round", 0) + 1, id=tid)
            if not out.get("quiz_questions"):
                raise RuntimeError("The model returned no valid questions. Try again.")
            return lambda n: replace(n, out)
        return work

    if kind == "quiz_submit":
        answers = o.get("answers") or []
        if len(answers) != len(track.get("quiz_questions") or []) or None in answers:
            raise TaskError("incomplete", "Answer every question before submitting.")

        def work(job):
            out = evaluation_graph.invoke({**track, "user_answers": answers})
            return lambda n: replace(n, out)
        return work

    raise TaskError("bad_kind", f"Unknown job kind '{kind}'.")
