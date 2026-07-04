import streamlit as st

from day9_pipeline.quiz_graph import quiz_graph
from day9_pipeline.retry_graph import retry_graph
from day9_pipeline.evaluator_graph import evaluation_graph

from memory.chat_history import ChatHistory

history = ChatHistory()


def save_chat():
    history.save_state(
        st.session_state.current_chat,
        {
            "messages": st.session_state.messages,
            "workspace": st.session_state.workspace
        }
    )


def render_study_page():
    if "retry_generating" not in st.session_state:
        st.session_state.retry_generating = False

    if "quiz_generating" not in st.session_state:
        st.session_state.quiz_generating = False

    if "quiz_submitting" not in st.session_state:
        st.session_state.quiz_submitting = False
    
    idx = st.session_state.selected_workspace

    result = st.session_state.workspace[idx]

    # ==========================
    # Back Button
    # ==========================

    if st.button("⬅ Back to Chat"):

        st.session_state.selected_workspace = None

        st.rerun()

    st.title(f"📚 {result.get('topic','Study Topic')}")

    tab1, tab2 = st.tabs(
        [
            "📝 Notes",
            "🧠 Quiz"
        ]
    )

    # =====================================================
    # NOTES
    # =====================================================

    with tab1:

        if result.get("subtopics"):

            st.subheader("Study Plan")

            for i, sub in enumerate(
                result["subtopics"],
                start=1
            ):

                st.markdown(f"### Day {i}")

                st.write(sub)

        if result.get("study_notes"):

            st.subheader("Study Notes")

            for note in result["study_notes"]:

                with st.expander(
                    note["topic"],
                    expanded=True
                ):

                    st.markdown(note["notes"])

    # =====================================================
    # QUIZ
    # =====================================================

    with tab2:


        quiz = result.get("quiz_questions", [])

        # =================================================
        # Generate Quiz
        # =================================================

        if len(quiz) == 0:

            # Step 1: User clicks button
            if (
                st.button(
                    "🧠 Generate Quiz",
                    disabled=st.session_state.quiz_generating,
                    use_container_width=True,
                )
                and not st.session_state.quiz_generating
            ):

                st.session_state.quiz_generating = True
                st.rerun()

            # Step 2: Next rerun performs generation
            if st.session_state.quiz_generating:

                with st.spinner("Generating Quiz..."):

                    updated = quiz_graph.invoke(result)

                    st.session_state.workspace[idx] = updated

                    save_chat()

                st.session_state.quiz_generating = False

                st.rerun()

        # =================================================
        # Quiz Already Exists
        # =================================================

        else:

            answers = []

            for qno, question in enumerate(quiz, start=1):

                st.markdown(f"### Question {qno}")

                quiz_evaluated = result.get("quiz_score") is not None

                saved_answer = None
                if quiz_evaluated and len(result.get("user_answers", [])) >= qno:
                    saved_answer = result["user_answers"][qno - 1]

                ans = st.radio(
                    question["question"],
                    question["options"],
                    index=question["options"].index(saved_answer) if saved_answer in question["options"] else None,
                    key=f"study_{idx}_{qno}",
                    disabled=quiz_evaluated
                )

                answers.append(ans)

            # =============================================
            # Already Evaluated
            # =============================================

            quiz_evaluated = result.get("quiz_score") is not None

            if quiz_evaluated:

                st.success(
                    f"Score: {result['quiz_score']:.1f}%"
                )

                st.progress(result["quiz_score"] / 100)

                st.subheader("Analysis")
                st.write(result["analysis"])

                st.subheader("Weak Topics")

                if result["weak_topics"]:

                    for topic in result["weak_topics"]:
                        st.write("•", topic)

                else:
                    st.success("Excellent! No weak topics.")

                st.subheader("Suggestions")
                st.write(result["suggestions"])
                # ------------------------
                # Retry
                # ------------------------

                if result["quiz_score"] < 60:

    # Click
                    if (
                        st.button(
                            "Revise & Retry",
                            disabled=st.session_state.retry_generating,
                            use_container_width=True
                        )
                        and not st.session_state.retry_generating
                    ):

                        st.session_state.retry_generating = True
                        st.rerun()

                    # Generate
                    if st.session_state.retry_generating:

                        try:

                            with st.spinner("Generating quiz from weak topics..."):

                                updated = retry_graph.invoke(result)

                # Reset evaluation
                                updated["quiz_score"] = None
                                updated["analysis"] = ""
                                updated["suggestions"] = ""
                                updated["user_answers"] = []

                # IMPORTANT:
                # Keep weak_topics until quiz generation finishes.
                # Do NOT clear it before retry_graph.invoke().
                                

                                st.session_state.workspace[idx] = updated

                                save_chat()

                        finally:

                            st.session_state.retry_generating = False

                        st.rerun()

                else:

                    if st.button(
                        "Generate Another Quiz",
                        use_container_width=True
                    ):

                        with st.spinner("Generating..."):

                            updated = quiz_graph.invoke(result)

                            # Reset previous evaluation
                            updated["quiz_score"] = None
                            updated["analysis"] = ""
                            updated["suggestions"] = ""
                            updated["weak_topics"] = []
                            updated["user_answers"] = []

                            st.session_state.workspace[idx] = updated

                            save_chat()

                            st.rerun()

            # =============================================
            # Submit Quiz
            # =============================================

            else:

                # Step 1: User clicks
                if (
                    st.button(
                        "Submit Quiz",
                        disabled=st.session_state.quiz_submitting,
                        use_container_width=True,
                    )
                    and not st.session_state.quiz_submitting
                ):

                    if None in answers:
                        st.warning("Please answer all questions.")
                    else:
                        st.session_state.pending_answers = answers
                        st.session_state.quiz_submitting = True
                        st.rerun()

                # Step 2: Next rerun performs evaluation
                if st.session_state.quiz_submitting:
                  try:
                    with st.spinner("Evaluating Quiz..."):

                        answers = st.session_state.pending_answers

                        score = sum(
                            1
                            for q, a in zip(quiz, answers)
                            if q["answer"] == a
                        )

                        percentage = (score / len(quiz)) * 100

                        result["user_answers"] = answers

                        
                        result["quiz_score"] = percentage

                        feedback = evaluation_graph.invoke(result)

                        result["analysis"] = feedback["analysis"]
                        result["weak_topics"] = feedback["weak_topics"]
                        result["suggestions"] = feedback["suggestions"]

                        st.session_state.workspace[idx] = result

                        save_chat()
                  finally:
                    st.session_state.pop("pending_answers", None)
                    st.session_state.quiz_submitting = False

                  st.rerun()

                    