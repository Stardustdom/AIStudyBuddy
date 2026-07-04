from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="mistral",
    temperature=0
)

# =========================================================
# Fast rule-based detection for obvious messages
# =========================================================

GENERAL_CHAT = {
    "ok", "okay", "okk", "okayy",
    "thanks", "thank you", "thankyou", "thx",
    "nice", "great", "awesome", "cool",
    "yes", "yep", "yeah",
    "no", "nope",
    "hi", "hello", "hey",
    "good morning", "good afternoon", "good evening",
    "bye", "see you", "good night"
}

QUIZ_KEYWORDS = [
    "quiz",
    "mcq",
    "mcqs",
    "test me",
    "practice quiz",
    "practice questions",
    "ask me questions"
]

NEW_STUDY_KEYWORDS = [
    "teach me",
    "study",
    "learn",
    "create notes",
    "make notes",
    "roadmap",
    "start learning"
]

CONTEXT_KEYWORDS = [
    "explain",
    "summarize",
    "summary",
    "revise",
    "again",
    "examples",
    "example",
    "define",
    "what is",
    "what are",
    "which",
    "compare",
    "difference",
    "tags",
    "used",
    "covered",
    "day",
    "topic",
    "section",
    "important points",
    "simplify"
]

SYSTEM_PROMPT = """
You are an intent classifier for an AI Study Buddy.

Return EXACTLY ONE of these:

NEW_STUDY
CONTEXT_QA
QUIZ
GENERAL_CHAT

Rules:

NEW_STUDY
The user wants to start learning a completely new subject.

CONTEXT_QA
The user is asking about notes that already exist.

QUIZ
The user wants to take or generate a quiz.

GENERAL_CHAT
Greetings, thanks, confirmations, casual conversation or anything unrelated.

Return ONLY the label.
"""


def detect_intent(prompt: str) -> str:

    text = prompt.strip().lower()

    # ==========================================
    # Rule-based (much more reliable)
    # ==========================================

    if text in GENERAL_CHAT:
        return "GENERAL_CHAT"

    if any(k in text for k in QUIZ_KEYWORDS):
        return "QUIZ"

    if any(text.startswith(k) for k in NEW_STUDY_KEYWORDS):
        return "NEW_STUDY"

    if any(k in text for k in CONTEXT_KEYWORDS):
        return "CONTEXT_QA"

    # Short questions are usually about existing notes
    if text.endswith("?") and len(text.split()) <= 8:
        return "CONTEXT_QA"

    # ==========================================
    # LLM fallback
    # ==========================================

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

    intent = response.content.strip().upper()

    allowed = {
        "NEW_STUDY",
        "CONTEXT_QA",
        "QUIZ",
        "GENERAL_CHAT"
    }

    if intent not in allowed:
        return "GENERAL_CHAT"

    return intent