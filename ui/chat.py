import re
import uuid

import streamlit as st

from api import jobs
from day9_pipeline.intent_router import GENERAL_CHAT, NEW_STUDY_KEYWORDS, QUIZ_KEYWORDS
from studybuddy import store
from studybuddy.studio import DEFAULT_TITLES, ask, enabled_sources, suggest_questions
from ui.jobs_ui import lock_hint, start


def route(prompt: str, has_sources: bool) -> str:
    """Intent routing. With sources, a question is grounded Q&A by default (NotebookLM behaviour)."""
    text = prompt.strip().lower()
    if text in GENERAL_CHAT:
        return "GENERAL_CHAT"
    if any(k in text for k in QUIZ_KEYWORDS):
        return "QUIZ"
    if any(text.startswith(k) for k in NEW_STUDY_KEYWORDS) and re.search(r"plan|path|roadmap|teach|notes|course", text):
        return "NEW_STUDY"
    if has_sources:
        return "CONTEXT_QA"
    from day9_pipeline.intent_router import detect_intent

    return detect_intent(prompt)


def _citations(cites):
    if not cites:
        return
    with st.expander(f"📎 {len(cites)} source excerpt(s)"):
        for c in cites:
            st.markdown(f"**[{c['n']}] {c['source']}**")
            st.caption(c["text"][:600] + ("…" if len(c["text"]) > 600 else ""))


def _save_note(nb, content):
    title = re.sub(r"[#*_`>\[\]]", "", content).strip().split("\n")[0][:50] or "Note"
    with jobs.edit(nb["id"]) as n:
        n["notes"].append({"title": title, "content": content})
    st.toast("Saved to Notes 📌")


def _append(nid, msg):
    with jobs.edit(nid) as n:
        n["messages"].append({"id": "m" + uuid.uuid4().hex[:8], **msg})


def render_chat(nb, locked=False):
    srcs = enabled_sources(nb)

    # ------------------------------------------------------------ history
    for i, m in enumerate(nb["messages"]):
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m["role"] == "assistant":
                _citations(m.get("citations"))
                if m.get("stopped"):
                    st.caption("⏹ Response stopped")
                    prev = nb["messages"][i - 1]["content"] if i and nb["messages"][i - 1]["role"] == "user" else None
                    if prev and st.button("↻ Retry", key=f"retry_{nb['id']}_{i}", disabled=locked, help=lock_hint(nb)):
                        st.session_state.pending_prompt = prev
                        st.rerun()
                if m.get("savable", True) and st.button("📌 Save to notes", key=f"save_{nb['id']}_{i}"):
                    _save_note(nb, m["content"])

    # --------------------------------------------------------- empty state
    if not nb["messages"]:
        if not srcs:
            st.markdown(
                "#### Start by adding a source\n"
                "Upload a PDF or Word file, add a website or paste text in the **Sources** panel on the left. "
                "I'll answer questions with citations from them, and you can turn them into study guides, "
                "flashcards, quizzes, mind maps and audio overviews in the **Studio**.\n\n"
                "No documents? Ask me to *teach you a topic* and I'll build a study path from the web."
            )
        else:
            st.markdown(f"#### Ask about your {len(srcs)} source(s)")
            key = f"sugg_{nb['id']}"
            if key not in st.session_state:
                if st.button("💡 Suggest questions", width="stretch", disabled=locked, help=lock_hint(nb)):
                    with st.spinner("Reading your sources…"):
                        try:
                            st.session_state[key] = suggest_questions(nb)
                        except Exception as e:
                            st.error(str(e))
                    st.rerun()
            else:
                for j, q in enumerate(st.session_state[key]):
                    if st.button(q, key=f"sq_{j}", width="stretch", disabled=locked):
                        st.session_state.pending_prompt = q
                        st.rerun()

    typed = st.chat_input(
        "Ask about your sources…" if srcs else "Add a source, or ask me to teach a topic…",
        disabled=locked,
    )
    prompt = typed or (None if locked else st.session_state.pop("pending_prompt", None))
    if not prompt:
        return

    # One job at a time: chat takes the same notebook lock as the Studio tools.
    try:
        job = jobs.begin(nb["id"], "chat", "Answering")
    except jobs.Busy as b:
        st.toast(f"{b.job.label} is still running. Stop it or wait.", icon="⏳")
        return

    nid = nb["id"]
    text, error, cites, stream, intent, completed = "", None, [], None, None, False
    try:
        with jobs.edit(nid) as n:
            n["messages"].append({"id": "m" + uuid.uuid4().hex[:8], "role": "user", "content": prompt})
            if n["title"] in DEFAULT_TITLES:
                n["title"] = prompt[:40]
        nb = store.load(nid)
        with st.chat_message("user"):
            st.markdown(prompt)

        intent = route(prompt, bool(srcs))
        with st.chat_message("assistant"):
            if intent == "CONTEXT_QA":
                st.button("■ Stop", key="stop_chat", help="Stop generating (keeps the text so far)")
                stream, cites = ask(nb, prompt)

                def tracked():
                    nonlocal text
                    for tok in stream:  # a click on Stop reruns the script and ends this loop
                        text += tok
                        yield tok

                st.write_stream(tracked())
                _citations(cites)
            if intent != "CONTEXT_QA":
                if intent == "NEW_STUDY":
                    # study path is a background job: finish this chat job first, then start it
                    text = (f"Building a study path for **{prompt}**{' from your sources' if srcs else ''}. "
                            "Watch the progress bar above; the path will appear in the **🎓 Study path** tab.")
                elif intent == "QUIZ":
                    text = ("Open the **🧠 Quiz** tab to take or generate a quiz." if nb["study"] else
                            "Quizzes are built from a study path. Use **Build study path** in the "
                            "**🎓 Study path** tab first.")
                else:
                    text = ("👋 I'm your Study Buddy. Add sources on the left and ask me anything about them — "
                            "or open the Studio to generate a guide, flashcards, quiz, mind map or audio overview.")
                st.markdown(text)
        completed = True
    except Exception as e:  # noqa: BLE001
        error = str(e) or type(e).__name__
        st.error(f"⚠️ {error}")
    finally:
        # No st.* calls here: this also runs when Stop interrupts the script mid-stream.
        if stream is not None and hasattr(stream, "close"):
            stream.close()  # closes the upstream LLM request
        stopped = (not completed) and error is None and bool(text)  # Stop (or a rerun) cut the stream
        try:
            if text or error:
                msg = {"role": "assistant", "content": text or f"⚠️ {error}", "savable": bool(text) and not error and intent == "CONTEXT_QA",
                       "stopped": stopped}
                if cites:
                    msg["citations"] = [{"n": c["n"], "source": c["source"], "text": c["text"]} for c in cites]
                _append(nid, msg)
        except jobs.NotFound:
            pass
        jobs.finish(job, "failed" if error else "done", error)

    # (NEW_STUDY) the chat job has released the lock, so the background job can take it
    if intent == "NEW_STUDY":
        start(store.load(nid), "study_path", {"topic": prompt})
    st.rerun()

