import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from memory.short_term import ShortTermMemory
from day5_agent.plannerAgent import generate_plan
from day8_agent.researcher_agent import researcher

memory = ShortTermMemory(max_len=5)

print("\n=== AI STUDY BUDDY (Day 10 Memory) ===")
print("Type 'exit' to quit\n")


def run_pipeline(topic):
    """
    Planner → Researcher pipeline
    """

    plan = generate_plan(topic)
    subtopics = plan["subtopics"]

    all_notes = []

    for sub in subtopics:
        notes = researcher.invoke({"subtopic": sub})
        all_notes.append(notes)

    return "\n\n".join(all_notes)


while True:

    user_input = input("You: ")

    if user_input.lower() == "exit":
        break

    # store user message
    memory.add("user", user_input)

    print("\nRunning pipeline...\n")

    # run full system
    result = run_pipeline(user_input)

    print("\n===== FINAL OUTPUT =====\n")
    print(result)

    # store assistant response
    memory.add("assistant", result)