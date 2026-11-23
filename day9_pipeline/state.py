from typing import TypedDict


class AgentState(TypedDict):

    # ----------------------------------------------------
    # User Input
    # ----------------------------------------------------

    topic: str

    # Uploaded / enabled notebook sources: [{id, name, text}]
    # When present, planner + researcher are grounded in them.
    sources: list

    # ----------------------------------------------------
    # Planner Output
    # ----------------------------------------------------

    subtopics: list[str]

    # ----------------------------------------------------
    # Researcher Output
    # ----------------------------------------------------

    study_notes: list

    # ----------------------------------------------------
    # Quiz Output
    # ----------------------------------------------------

    quiz_questions: list

    # ----------------------------------------------------
    # Evaluator Input
    # ----------------------------------------------------

    user_answers: list[str]

    # ----------------------------------------------------
    # Evaluator Output
    # ----------------------------------------------------

    quiz_score: float | None

    weak_topics: list[str]

    retry_count: int

    # ----------------------------------------------------
    # NEW FEEDBACK FIELDS
    # ----------------------------------------------------

    analysis: str

    suggestions: str