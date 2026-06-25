import streamlit as st

from researcher_agent import researcher


# ==================================
# PAGE CONFIG
# ==================================

st.set_page_config(
    page_title="Study Notes Generator",
    page_icon="📖",
    layout="wide"
)

st.title("📖 AI Study Notes Generator")



# ==================================
# INPUT
# ==================================

topic = st.text_input(
    "Enter Topic",
    placeholder="Example: LangGraph"
)


# ==================================
# GENERATE BUTTON
# ==================================

if st.button("Generate Notes"):

    if not topic.strip():

        st.warning("Please enter a topic.")

    else:

        with st.spinner(
            "Researching and generating notes..."
        ):

            result = researcher.invoke(
                {
                    "subtopic": topic
                }
            )

        if isinstance(result, dict):

            st.success("Notes Generated!")

            st.divider()

            st.subheader(
                f"📚 {result['topic']}"
            )

            st.markdown(
                result["notes"]
            )

            st.divider()

            st.download_button(
                label="📥 Download Notes",
                data=result["notes"],
                file_name=f"{topic}_notes.txt",
                mime="text/plain"
            )

        else:

            st.error(result)