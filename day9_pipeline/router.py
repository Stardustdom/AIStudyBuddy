def route_query(prompt: str) -> str:
    p = prompt.lower()

    # 1. EXPLANATION INTENT
    if any(k in p for k in ["explain", "understand", "what is", "why", "how does"]):
        return "explain"

    # 2. QUIZ INTENT
    if any(k in p for k in ["quiz", "test", "mcq", "questions"]):
        return "quiz"

    # 3. NOTES INTENT
    if any(k in p for k in ["notes", "summary", "summarize", "short note"]):
        return "notes"

    # 4. ROADMAP / PLANNING
    if any(k in p for k in ["roadmap", "plan", "schedule"]):
        return "roadmap"

    return "general"