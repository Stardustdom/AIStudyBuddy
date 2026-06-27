from graph import graph


print("===================================")
print("      AI Study Buddy Pipeline")
print("===================================")

topic = input("\nEnter study topic: ")

initial_state = {
    "topic": topic,
    "subtopics": [],
    "study_notes": []
}


print("\nStarting LangGraph Pipeline...\n")

final_state = graph.invoke(initial_state)


print("\n===================================")
print("        STUDY PLAN")
print("===================================\n")

for i, subtopic in enumerate(final_state["subtopics"], start=1):

    print(f"Day {i}: {subtopic}")


print("\n===================================")
print("        STUDY NOTES")
print("===================================\n")

for note in final_state["study_notes"]:

    print("=" * 60)

    print(f"\nTopic: {note['topic']}\n")

    print(note["notes"])

    print("\n")