import json

from langchain_ollama import ChatOllama
import os

def save_plan(plan):

    filename = "day5 agent/study_plans.json"

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

    print(f"\nPlan saved to {filename}")


llm = ChatOllama(
    model="mistral",
    temperature=0.1
)


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

Think through these steps internally before producing the final answer.

Return ONLY valid JSON.

No markdown.
No explanation.
No reasoning.
No code fences.
No backticks.

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

Example 1:

Input:
PHP

Output:
{
    "topic": "PHP",
    "subtopics": [
        "PHP Introduction, Installation and Setup",
        "Variables, Data Types and Operators",
        "Control Structures",
        "Loops",
        "Functions, Arrays and File Handling"
    ]
}

Example 2:

Input:
Antigravity

Output:
{
    "topic": "Antigravity",
    "subtopics": [
        "Introduction to Antigravity and its Theories",
        "Magnetic Levitation and its Relation to Antigravity",
        "Modern Research and Experiments",
        "Major Theories and Contributors",
        "Future Applications of Antigravity Technology"
    ]
}
"""


while True:

    topic = input("\nEnter study topic (or exit): ")

    if topic.lower() == "exit":
        break

    prompt = f"Topic: {topic}"

    plan = None

    try:

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
                plan = json.loads(response.content)
                break

            except json.JSONDecodeError:

                if attempt == 2:
                    raise

                print(f"Retrying... ({attempt + 1}/3)")

        if plan:
            save_plan(plan)

            print("\n===== STUDY PLAN =====")
            print(f"\nTopic: {plan['topic']}\n")

            for i, item in enumerate(plan["subtopics"], start=1):
                print(f"Day {i}: {item}")

    except json.JSONDecodeError:

        print("\nInvalid JSON received from model.")

    except Exception as e:

        print(f"\nError: {e}")