import sys
import os

# Get the project root (AI STUDY BUDDY)
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

sys.path.append(PROJECT_ROOT)

from day9_pipeline.state import AgentState
from day9_pipeline.subtopic_router import extract_subtopic
from day5_agent.plannerAgent import generate_plan
from day8_agent.researcher_agent import researcher
from day12.quiz import quiz_generator
from day9_pipeline.day13.evaluator import evaluator
from memory.long_term import LongTermMemory

ltm = LongTermMemory()


# ==========================================================
# Planner Node
# ==========================================================

def planner_node(state: AgentState):

    print("\n==============================")
    print(" Running Planner Agent")
    print("==============================")

    plan = generate_plan(state["topic"])

    state["subtopics"] = plan["subtopics"]

    return state


# ==========================================================
# Researcher Node
# ==========================================================

def researcher_node(state: AgentState):

    print("\n==============================")
    print(" Running Researcher Agent")
    print("==============================")

    notes = []

    # If the evaluator has identified weak topics,
    # only research those topics.
    topics_to_research = (
        state["weak_topics"]
        if state["weak_topics"]
        else state["subtopics"]
    )

    for subtopic in topics_to_research:

        print(f"\nResearching: {subtopic}")

        results = ltm.get_note(subtopic)

        if results["documents"]:

            print("✓ Found existing notes in ChromaDB")

            notes.append(
                {
                    "topic": subtopic,
                    "notes": results["documents"][0]
                }
            )

        else:

            print("✗ No notes found. Researching online...")

            result = researcher.invoke(
                {
                    "subtopic": subtopic
                }
            )

            notes.append(result)

    state["study_notes"] = notes

    return state


# ==========================================================
# Quiz Node
# ==========================================================

def quiz_node(state: AgentState):

    print("\n==============================")
    print(" Running Quiz Agent")
    print("==============================")

    combined_notes = ""

    for note in state["study_notes"]:

        combined_notes += (
            f"\n\n### {note['topic']}\n"
            f"{note['notes']}"
        )

    print("Generating comprehensive 15-question quiz...")

    state["quiz_questions"] = quiz_generator(combined_notes)

    return state


# ==========================================================
# Evaluator Node
# ==========================================================

def evaluator_node(state: AgentState):

    print("\n==============================")
    print(" Running Evaluator Agent")
    print("==============================")

    updated_state = evaluator(state)  # evaluator already returns state

    return updated_state
def find_subtopic_in_notes(state, subtopic: str):

    if not state.get("study_notes"):
        return None

    subtopic = subtopic.lower()

    for note in state["study_notes"]:
        topic = note.get("topic", "").lower()
        content = note.get("notes", "")

        if subtopic in topic or subtopic in content.lower():
            return note

    return None
def subtopic_explain_node(state: AgentState):

    print("\n==============================")
    print(" Running Subtopic Explainer")
    print("==============================")

    prompt = state["topic"]

    subtopic = extract_subtopic(prompt)

    if not subtopic:
        state["analysis"] = "No subtopic detected"
        return state

    # Step 1: try to find in existing notes
    existing = find_subtopic_in_notes(state, subtopic)

    if existing:
        explanation = existing["notes"]

    else:
        # Step 2: fallback to researcher
        result = researcher.invoke({
            "subtopic": subtopic
        })

        explanation = result.get("notes", "No explanation found")

    state["analysis"] = explanation
    state["subtopic_used"] = subtopic

    return state