import re

def extract_subtopic(prompt: str):
    """
    Detect if user is asking about a specific subtopic.
    """

    prompt_lower = prompt.lower()

    # Case 1: explicit "explain X"
    match = re.search(r"explain (.+)", prompt_lower)
    if match:
        return match.group(1).strip()

    # Case 2: "what is X", "tell me about X"
    match = re.search(r"(what is|tell me about|define) (.+)", prompt_lower)
    if match:
        return match.group(2).strip()

    return None