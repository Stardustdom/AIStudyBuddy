"""Quiz tab: Quiz agent -> (user answers) -> Evaluator agent -> optional Retry on weak topics."""
import streamlit as st

from day9_pipeline.evaluator_graph import evaluation_graph
from day9_pipeline.quiz_graph import quiz_graph
from day9_pipeline.retry_graph import retry_graph
from studybuddy import store
from studybuddy.studio import enabled_sources
from ui.study_page import pick_track


def _with_sources(nb, track):
    srcs = [{"id": s["id"], "name": s["name"], "text": s["text"]} for s in enabled_sources(nb)]
    return {**track, "sources": srcs}


def _generate(nb, idx, graph_, reset_weak=True):
    out = graph_.invoke(_with_sources(nb, nb["study"][idx]))
    out.pop("sources", None)
    out.update(quiz_score=None, analysis="", suggestions="", user_answers=[])
    if reset_weak:
        out["weak_topics"] = []
    out["quiz_round"] = nb["study"][idx].get("quiz_round", 0) + 1
    nb["study"][idx] = out
    store.save(nb)


def render_quiz(nb: dict):
    idx = pick_track(nb, "Quiz for", "quiz_sel")
    if idx is None:
        st.info("Build a study path first (🎓 Study path tab) — the quiz is generated from its notes.")
        return
    track = nb["study"][idx]
    quiz = track.get("quiz_questions") or []

    # ------------------------------------------------------- no quiz yet
    if not quiz:
        if st.button("🧠 Generate quiz (15 questions)", type="primary", width="stretch"):
            with st.spinner("Quiz agent is writing questions…"):
                try:
                    _generate(nb, idx, quiz_graph)
                except Exception as e:
                    st.error(str(e))
                    return
            if not nb["study"][idx].get("quiz_questions"):
                st.error("The model returned no valid questions. Try again.")
            st.rerun()
        return

    done = track.get("quiz_score") is not None
    rnd = track.get("quiz_round", 0)

    # ------------------------------------------------------------- taking
    if not done:
        with st.form(f"quiz_{nb['id']}_{idx}_{rnd}"):
            answers = []
            for q_no, q in enumerate(quiz, 1):
                answers.append(st.radio(f"**{q_no}.** {q['question']}", q["options"], index=None,
                                        key=f"q_{nb['id']}_{idx}_{rnd}_{q_no}"))
                st.write("")
            submitted = st.form_submit_button("Submit quiz", type="primary", width="stretch")
        if submitted:
            if None in answers:
                st.warning(f"Please answer all questions ({answers.count(None)} left).")
                return
            with st.spinner("Evaluator agent is marking your quiz…"):
                state = {**track, "user_answers": answers}
                fb = evaluation_graph.invoke(state)
                fb.pop("sources", None)
                nb["study"][idx] = fb
                store.save(nb)
            st.rerun()
        return

    # ------------------------------------------------------------- results
    score = track["quiz_score"]
    st.metric("Score", f"{score:.0f}%")
    st.progress(min(score / 100, 1.0))
    t_ans = track.get("user_answers", [])
    with st.expander("Review answers"):
        for q_no, (q, a) in enumerate(zip(quiz, t_ans), 1):
            ok = a == q["answer"]
            st.markdown(f"{'✅' if ok else '❌'} **{q_no}. {q['question']}**")
            st.caption(f"Your answer: {a}" + ("" if ok else f" · Correct: {q['answer']}"))
    st.subheader("Analysis")
    st.write(track.get("analysis", ""))
    st.subheader("Weak topics")
    if track.get("weak_topics"):
        for t in track["weak_topics"]:
            st.write("•", t)
    else:
        st.success("Excellent! No weak topics.")
    st.subheader("Suggestions")
    st.write(track.get("suggestions", ""))

    c1, c2 = st.columns(2)
    if score < 60 and track.get("weak_topics"):
        if c1.button("🔁 Revise & retry weak topics", type="primary", width="stretch"):
            with st.spinner("Generating a quiz from your weak topics…"):
                _generate(nb, idx, retry_graph, reset_weak=True)
            st.rerun()
    if c2.button("🆕 New quiz", width="stretch"):
        with st.spinner("Generating a fresh quiz…"):
            _generate(nb, idx, quiz_graph)
        st.rerun()
