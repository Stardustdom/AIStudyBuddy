import sys
import os

# Get the project root (AI STUDY BUDDY)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

sys.path.append(PROJECT_ROOT)

from state import AgentState

from day5_agent.plannerAgent import generate_plan
from day8_agent.researcher_agent import researcher
from memory.long_term import LongTermMemory

ltm = LongTermMemory()

def planner_node(state: AgentState):

    print("\n==============================")
    print(" Running Planner Agent")
    print("==============================")

    plan = generate_plan(state["topic"])

    state["subtopics"] = plan["subtopics"]

    return state


def researcher_node(state: AgentState):

    print("\n==============================")
    print(" Running Researcher Agent")
    print("==============================")

    notes = []

    for subtopic in state["subtopics"]:

        print(f"\nResearching: {subtopic}")

        # Check if we already have similar notes
        results = ltm.search(subtopic)

        if results["documents"] and results["documents"][0]:

            print("✓ Found existing notes in ChromaDB")

            notes.append({
                "topic": subtopic,
                "notes": results["documents"][0][0]
            })

        else:

            print("✗ No notes found. Researching...")

            result = researcher.invoke(
                {
                    "subtopic": subtopic
                }
            )

            notes.append(result)

    state["study_notes"] = notes

    return state