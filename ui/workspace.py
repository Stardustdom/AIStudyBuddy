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


def render_workspace():

    if len(st.session_state.workspace) == 0:
        return

    st.divider()
    st.header("📚 Study Workspace")

    for idx, result in enumerate(st.session_state.workspace):

        topic = result.get("topic", f"Topic {idx+1}")

        with st.expander(f"📘 {topic}", expanded=False):

            tab1, tab2 = st.tabs(
                [
                    "📝 Notes",
                    "🧠 Quiz"
                ]
            )

            # =====================================
            # NOTES
            # =====================================

            with tab1:

                if result.get("subtopics"):

                    st.subheader("Study Plan")

                    for i, sub in enumerate(
                        result["subtopics"],
                        start=1
                    ):

                        st.markdown(
                            f"**Day {i}**"
                        )

                        st.write(sub)

                if result.get("study_notes"):

                    st.subheader("Study Notes")

                    for note in result["study_notes"]:

                        with st.expander(
                            note["topic"]
                        ):

                            st.markdown(
                                note["notes"]
                            )

            # =====================================
            # QUIZ
            # =====================================

            with tab2:

                quiz = result.get(
                    "quiz_questions",
                    []
                )

                if len(quiz) == 0:

                    if st.button(
                        "Generate Quiz",
                        key=f"quiz_{idx}"
                    ):

                        with st.spinner(
                            "Generating..."
                        ):

                            st.session_state.workspace[idx] = (
                                quiz_graph.invoke(result)
                            )

                        save_chat()

                        st.rerun()

                else:

                    answers = []

                    for qno, question in enumerate(
                        quiz,
                        start=1
                    ):

                        st.markdown(
                            f"### Question {qno}"
                        )

                        ans = st.radio(

                            question["question"],

                            question["options"],

                            index=None,

                            key=f"{idx}_{qno}"

                        )

                        answers.append(ans)

                    if st.button(
                        "Submit Quiz",
                        key=f"submit_{idx}"
                    ):

                        if None in answers:

                            st.warning(
                                "Answer every question."
                            )

                        else:

                            score = sum(

                                1

                                for q, a in zip(
                                    quiz,
                                    answers
                                )

                                if q["answer"] == a

                            )

                            percentage = (
                                score / len(quiz)
                            ) * 100

                            result["user_answers"] = answers

                            result["quiz_score"] = percentage

                            feedback = evaluation_graph.invoke(
                                result
                            )

                            st.success(
                                f"Score: {score}/{len(quiz)}"
                            )

                            st.progress(
                                percentage / 100
                            )

                            st.subheader(
                                "Analysis"
                            )

                            st.write(
                                feedback["analysis"]
                            )

                            st.subheader(
                                "Weak Topics"
                            )

                            if feedback["weak_topics"]:

                                for topic in feedback[
                                    "weak_topics"
                                ]:

                                    st.write(
                                        "•",
                                        topic
                                    )

                            else:

                                st.success(
                                    "No weak topics!"
                                )

                            st.subheader(
                                "Suggestions"
                            )

                            st.write(
                                feedback["suggestions"]
                            )

                            # Retry

                            if percentage < 60:

                                if st.button(

                                    "Revise & Retry",

                                    key=f"retry_{idx}"

                                ):

                                    with st.spinner(
                                        "Preparing..."
                                    ):

                                        st.session_state.workspace[idx] = (
                                            retry_graph.invoke(
                                                feedback
                                            )
                                        )

                                    save_chat()

                                    st.rerun()

                            else:

                                if st.button(

                                    "Generate Another Quiz",

                                    key=f"again_{idx}"

                                ):

                                    with st.spinner(
                                        "Generating..."
                                    ):

                                        st.session_state.workspace[idx] = (
                                            quiz_graph.invoke(result)
                                        )

                                    save_chat()

                                    st.rerun()