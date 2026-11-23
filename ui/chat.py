import re

import streamlit as st

from day9_pipeline.intent_router import QUIZ_KEYWORDS, NEW_STUDY_KEYWORDS, GENERAL_CHAT
from studybuddy import store
from studybuddy.studio import ask, enabled_sources, suggest_questions
from ui.study_page import build_study_track


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
    nb["notes"].append({"title": title, "content": content})
    store.save(nb)
    st.toast("Saved to Notes 📌")


def render_chat(nb):
    srcs = enabled_sources(nb)

    # ------------------------------------------------------------ history
    for i, m in enumerate(nb["messages"]):
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m["role"] == "assistant":
                _citations(m.get("citations"))
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
                if st.button("💡 Suggest questions", width="stretch"):
                    with st.spinner("Reading your sources…"):
                        try:
                            st.session_state[key] = suggest_questions(nb)
                        except Exception as e:
                            st.error(str(e))
                    st.rerun()
            else:
                for j, q in enumerate(st.session_state[key]):
                    if st.button(q, key=f"sq_{j}", width="stretch"):
                        st.session_state.pending_prompt = q
                        st.rerun()

    prompt = st.chat_input("Ask about your sources…" if srcs else "Add a source, or ask me to teach a topic…")
    prompt = prompt or st.session_state.pop("pending_prompt", None)
    if not prompt:
        return

    nb["messages"].append({"role": "user", "content": prompt})
    if nb["title"] == "Untitled notebook":
        nb["title"] = prompt[:40]
    with st.chat_message("user"):
        st.markdown(prompt)

    intent = route(prompt, bool(srcs))

    with st.chat_message("assistant"):
        cites, savable = None, True
        try:
            if intent == "CONTEXT_QA":
                stream, cites = ask(nb, prompt)
                reply = st.write_stream(c for c in stream)
                _citations(cites)
            elif intent == "NEW_STUDY":
                with st.spinner("Planner → Researcher agents are building your study path…"):
                    build_study_track(nb, prompt)
                reply = (
                    f"✅ Study path for **{prompt}** is ready"
                    f"{' from your sources' if srcs else ''}. Open the **🎓 Study path** tab — "
                    "then take the quiz in **🧠 Quiz**."
                )
                st.markdown(reply)
                savable = False
            elif intent == "QUIZ":
                if nb["study"]:
                    reply = "Open the **🧠 Quiz** tab to take or generate a quiz."
                else:
                    reply = ("Quizzes are built from a study path. Click **Build study path** in the "
                             "**🎓 Study path** tab first (it uses your sources).")
                st.markdown(reply)
                savable = False
            else:
                reply = ("👋 I'm your Study Buddy. Add sources on the left and ask me anything about them — "
                         "or open the Studio to generate a study guide, flashcards, quiz, mind map or audio overview.")
                st.markdown(reply)
                savable = False
        except Exception as e:
            reply = f"⚠️ {e}"
            st.error(reply)
            savable = False

    msg = {"role": "assistant", "content": reply, "savable": savable}
    if cites:
        msg["citations"] = cites
    nb["messages"].append(msg)
    store.save(nb)
    st.rerun()
