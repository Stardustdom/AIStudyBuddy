from typing import TypedDict


class AgentState(TypedDict):

    topic: str

    subtopics: list[str]

    study_notes: list[str]