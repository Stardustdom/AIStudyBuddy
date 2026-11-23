import json
import re
from dotenv import load_dotenv
from studybuddy.llm import get_llm

load_dotenv()

llm = get_llm(0)


def clean_json(text: str):

    text = text.strip()

    # Remove markdown
    text = text.replace("```json", "").replace("```", "").strip()

    # Extract first JSON array
    match = re.search(r"\[[\s\S]*\]", text)

    if match:
        return match.group(0)

    return text


def quiz_generator(notes: str):

    prompt = f"""
Generate EXACTLY 15 MCQs from these notes.

Return ONLY a valid JSON array.

Each object MUST be:

{{
    "topic":"...",
    "question":"...",
    "options":[
        "...",
        "...",
        "...",
        "..."
    ],
    "answer":"..."
}}

Study Notes:

{notes}
"""

    for attempt in range(3):

        try:

            response = llm.invoke(prompt)

            text = clean_json(response.content)

            quiz = json.loads(text)

            return quiz[:15]

        except Exception as e:

            print(f"\nQuiz attempt {attempt+1} failed")
            print(e)

            print("\nModel Output:\n")
            print(response.content)

    return []