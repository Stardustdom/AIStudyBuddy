import sys
import os

from langchain_ollama import ChatOllama

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

sys.path.append(PROJECT_ROOT)

from state import AgentState


llm = ChatOllama(
    model="mistral",
    temperature=0.2
)


def evaluator(state: AgentState):

    quiz = state["quiz_questions"]
    user_answers = state["user_answers"]

    score = 0
    total = len(quiz)

    weak_topics = []

    # -----------------------------
    # Calculate score
    # -----------------------------

    for question, answer in zip(quiz, user_answers):

        if answer == question["answer"]:
            score += 1

        else:
            weak_topics.append(question["topic"])

    percentage = (score / total) * 100 if total else 0

    state["quiz_score"] = percentage
    state["weak_topics"] = list(set(weak_topics))

    if percentage < 60:
        state["retry_count"] += 1

    # -----------------------------
    # AI Feedback
    # -----------------------------

    prompt = f"""
You are an expert study mentor.

The student scored {percentage:.1f}%.

Weak topics:
{', '.join(state["weak_topics"]) if state["weak_topics"] else "None"}

Write TWO sections.

1. analysis
Explain the student's overall performance in 3-5 sentences.

2. suggestions
Give 5 practical suggestions to improve.

Return ONLY in this format.

Analysis:
...

Suggestions:
...
"""

    response = llm.invoke(prompt)

    feedback = response.content.strip()

    if "Suggestions:" in feedback:

        analysis, suggestions = feedback.split("Suggestions:", 1)

        analysis = analysis.replace("Analysis:", "").strip()
        suggestions = suggestions.strip()

    else:

        analysis = feedback
        suggestions = "Keep revising the weak topics."

    state["analysis"] = analysis
    state["suggestions"] = suggestions

    return state