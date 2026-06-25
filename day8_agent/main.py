from researcher_agent import researcher

print("=== Researcher Agent ===")
print("Type 'exit' to quit.")

while True:

    topic = input("\nEnter subtopic (or exit): ")

    if topic.lower() == "exit":
        print("\nGoodbye!")
        break

    print("\nGenerating study notes...")

    notes = researcher.invoke(
        {"subtopic": topic}
    )

    print("\n===== STUDY NOTES =====\n")
    print(f"\nTopic: {notes['topic']}")
    print("\n===== STUDY NOTES =====\n")
    print(notes["notes"])