import streamlit as st

from graph import graph


st.set_page_config(
    page_title="AI Study Buddy",
    page_icon="📚",
    layout="wide"
)

st.title("AI Study Buddy")
st.subheader("Planner + Researcher Agents")

topic = st.text_input(
    "Enter a study topic",
    placeholder="Example: JavaScript"
)

if st.button("Generate Study Notes"):

    if topic.strip() == "":
        st.warning("Please enter a topic.")
        st.stop()

    with st.spinner("Generating study plan..."):

        result = graph.invoke(
            {
                "topic": topic,
                "subtopics": [],
                "study_notes": [],
                "quiz_questions": [],
                "user_answers": [],
                "quiz_score": None,
                "weak_topics": [],
                "retry_count": 0
            }
        )

    st.success("Done!")

    st.divider()

    st.header("📅 Study Plan")

    for i, subtopic in enumerate(result["subtopics"], start=1):

        st.markdown(f"### Day {i}")

        st.write(subtopic)

    st.divider()

    st.header("📝 Study Notes")

    for i, note in enumerate(result["study_notes"], start=1):

        with st.expander(f"Day {i} - {note['topic']}", expanded=False):

            st.markdown(note["notes"])