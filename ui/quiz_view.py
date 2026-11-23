"""Quiz tab: Quiz agent -> (user answers) -> Evaluator agent -> optional Retry on weak topics.

Every agent call is a background job, so the global job lock applies (one at a time per notebook)."""
import streamlit as st

from ui.jobs_ui import lock_hint, start
from ui.study_page import pick_track


def render_quiz(nb: dict, locked: bool = False):
    idx = pick_track(nb, "Quiz for", "quiz_sel")
    if idx is None:
        st.info("Build a study path first (🎓 Study path tab) — the quiz is generated from its notes.")
        return
    track = nb["study"][idx]
    tid = track.get("id")
    quiz = track.get("quiz_questions") or []
    hint = lock_hint(nb)
    if locked:
        st.caption("⏳ " + (hint or "A job is running."))

    # ------------------------------------------------------- no quiz yet
    if not quiz:
        if st.button("🧠 Generate quiz (15 questions)", type="primary", width="stretch", disabled=locked, help=hint):
            if start(nb, "quiz", {"track_id": tid}):
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
                                        key=f"q_{nb['id']}_{idx}_{rnd}_{q_no}", disabled=locked))
                st.write("")
            submitted = st.form_submit_button("Submit quiz", type="primary", width="stretch", disabled=locked)
        if submitted:
            if None in answers:
                st.warning(f"Please answer all questions ({answers.count(None)} left).")
            elif start(nb, "quiz_submit", {"track_id": tid, "answers": answers}):
                st.rerun()
        return

    # ------------------------------------------------------------- results
    score = track["quiz_score"]
    st.metric("Score", f"{score:.0f}%")
    st.progress(min(score / 100, 1.0))
    with st.expander("Review answers"):
        for q_no, (q, a) in enumerate(zip(quiz, track.get("user_answers", [])), 1):
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
        if c1.button("🔁 Revise & retry weak topics", type="primary", width="stretch", disabled=locked, help=hint):
            if start(nb, "quiz_retry", {"track_id": tid}):
                st.rerun()
    if c2.button("🆕 New quiz", width="stretch", disabled=locked, help=hint):
        if start(nb, "quiz", {"track_id": tid}):
            st.rerun()
