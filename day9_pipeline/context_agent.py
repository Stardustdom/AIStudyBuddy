from langchain_ollama import ChatOllama
import re

llm = ChatOllama(
    model="mistral",
    temperature=0.1
)

SYSTEM_PROMPT = """
You are an expert study assistant.

Answer ONLY from the provided study note.

Rules:

1. Never use outside knowledge.
2. Never hallucinate.
3. If the answer isn't in the note, say:

"I couldn't find that in your current study material."

4. Keep answers concise unless the user asks for a detailed explanation.
5. Use markdown.
"""


# ==========================================
# Find matching note
# ==========================================

def find_best_note(question, study_notes):

    question = question.lower()

    import re

    # --------------------------
    # Day lookup
    # --------------------------

    match = re.search(r"day\s*(\d+)", question)

    if match:

        day = int(match.group(1))

        if 1 <= day <= len(study_notes):
            return study_notes[day-1]

    # --------------------------
    # Topic lookup
    # --------------------------

    best_note = None
    best_score = 0

    question_words = set(question.split())

    for note in study_notes:

        score = 0

        topic = note["topic"].lower()
        content = note["notes"].lower()

        for word in question_words:

            if len(word) < 3:
                continue

            if word in topic:
                score += 3

            if word in content:
                score += 1

        if score > best_score:
            best_score = score
            best_note = note

    return best_note

# ==========================================
# Answer
# ==========================================

from memory.long_term import LongTermMemory

ltm = LongTermMemory()


def answer_from_context(question, study_notes):

    note = find_best_note(
        question,
        study_notes
    )

    # ----------------------------
    # Current Workspace
    # ----------------------------

    if note:

        context = note["notes"]

    else:

        # ----------------------------
        # Long Term Memory
        # ----------------------------

        search = ltm.search(question)

        docs = search.get("documents", [])

        if docs and len(docs[0]) > 0:

            context = docs[0][0]

        else:

            return (
                "I couldn't find that in your current "
                "study material."
            )

    prompt = f"""
Study Material

{context}

Question:

{question}
"""

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

    return response.content
def stream_answer_from_context(question, study_notes):

    note = find_best_note(
        question,
        study_notes
    )

    if note:

        context = note["notes"]

    else:

        search = ltm.search(question)

        docs = search.get("documents", [])

        if docs and len(docs[0]) > 0:

            context = docs[0][0]

        else:

            yield (
                "I couldn't find that in your current "
                "study material."
            )
            return

    prompt = f"""
Study Material

{context}

Question:

{question}
"""

    stream = llm.stream(
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

    for chunk in stream:

        if chunk.content:
            yield chunk.content