import json
from dotenv import load_dotenv
from langchain_ollama import ChatOllama

load_dotenv()

llm = ChatOllama(
    model="mistral",
    temperature=0.2
)


def quiz_generator(notes: str) -> list:
    """
    Generate a comprehensive 15-question MCQ quiz
    covering all study notes.
    """

    prompt = f"""
You are an experienced university professor and exam setter.

Generate EXACTLY 15 multiple-choice questions from the study notes.

IMPORTANT RULES

1. Cover the ENTIRE study material.

2. Include easy, medium and difficult questions.

3. Test conceptual understanding rather than memorization.

4. Every question MUST belong to one of the study subtopics.

5. Every question MUST contain these fields:

- topic
- question
- options
- answer

6. "topic" should be the exact subtopic from which the question was generated.

7. Each question must have exactly four options.

8. The incorrect options should be believable.
Do NOT use unrelated options.

9. Shuffle the correct answer randomly.

10. The answer must exactly match one option.

11. Return ONLY valid JSON.

Example:

[
    {{
        "topic": "Newton's Law of Universal Gravitation",
        "question": "According to Newton's Law of Gravitation, what happens when the distance between two objects doubles?",
        "options": [
            "The force becomes one-fourth",
            "The force doubles",
            "The force remains unchanged",
            "The force becomes four times"
        ],
        "answer": "The force becomes one-fourth"
    }}
]

Study Notes:

{notes}
"""

    try:

        response = llm.invoke(prompt)

        response_text = response.content.strip()

        if response_text.startswith("```"):

            response_text = (
                response_text
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

        quiz = json.loads(response_text)

        if len(quiz) > 15:
            quiz = quiz[:15]

        return quiz

    except Exception as e:

        print("\nQuiz generation failed")
        print(e)

        return []