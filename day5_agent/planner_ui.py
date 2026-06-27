import json
import os

import streamlit as st
from langchain_ollama import ChatOllama


# ==========================================
# PAGE CONFIG
# ==========================================

st.set_page_config(
    page_title="Study Planner",
    page_icon="🎓",
    layout="centered"
)

st.title("AI Study Planner")
st.caption("Generate structured 5-day learning plans")


# ==========================================
# MODEL
# ==========================================

@st.cache_resource
def load_model():

    return ChatOllama(
        model="mistral",
        temperature=0.1
    )


llm = load_model()


# ==========================================
# SAVE PLAN
# ==========================================

def save_plan(plan):

    filename = "day5_agent/study_plans.json"

    if os.path.exists(filename):

        with open(filename, "r") as f:

            try:
                plans = json.load(f)

            except json.JSONDecodeError:
                plans = []

    else:

        plans = []

    plans.append(plan)

    with open(filename, "w") as f:
        json.dump(plans, f, indent=4)


# ==========================================
# SYSTEM PROMPT
# ==========================================

SYSTEM_PROMPT = """
You are an accurate study planner.

Given a study topic, create a 5-day learning plan.

Before generating the plan:

1. Identify prerequisite knowledge.
2. Identify beginner concepts.
3. Identify intermediate concepts.
4. Identify practical applications.
5. Arrange concepts from easiest to hardest.
6. Ensure exactly 5 learning stages.

Return ONLY valid JSON.

Format:

{
    "topic": "<topic>",
    "subtopics": [
        "Topic 1",
        "Topic 2",
        "Topic 3",
        "Topic 4",
        "Topic 5"
    ]
}
"""


# ==========================================
# INPUT
# ==========================================

topic = st.text_input(
    "Enter Study Topic",
    placeholder="Example: LangGraph"
)


# ==========================================
# GENERATE BUTTON
# ==========================================

if st.button("Generate Study Plan"):

    if not topic.strip():

        st.warning("Please enter a topic.")

    else:

        prompt = f"Topic: {topic}"

        try:

            with st.spinner("Generating plan..."):

                plan = None

                for attempt in range(3):

                    response = llm.invoke(
                        [
                            {
                                "role": "system",
                                "content": SYSTEM_PROMPT
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ]
                    )

                    try:

                        plan = json.loads(
                            response.content
                        )

                        break

                    except json.JSONDecodeError:

                        if attempt == 2:
                            raise

            if plan:

                st.success("Plan Generated!")

                st.divider()

                st.subheader(
                    f"📚 {plan['topic']}"
                )

                for i, item in enumerate(
                    plan["subtopics"],
                    start=1
                ):

                    st.markdown(
                        f"""
### Day {i}

{item}
"""
                    )

                st.divider()

                if st.button("Save Plan"):

                    save_plan(plan)

                    st.success(
                        "Plan saved successfully!"
                    )

        except json.JSONDecodeError:

            st.error(
                "Model returned invalid JSON."
            )

        except Exception as e:

            st.error(str(e))