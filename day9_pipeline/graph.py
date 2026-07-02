from langgraph.graph import StateGraph, END

from day9_pipeline.state import AgentState

from day9_pipeline.nodes import (
    planner_node,
    researcher_node,
    quiz_node,
    evaluator_node,
    subtopic_explain_node
)

builder = StateGraph(AgentState)

# Nodes
builder.add_node("planner", planner_node)
builder.add_node("researcher", researcher_node)
builder.add_node("quiz", quiz_node)
builder.add_node("evaluator", evaluator_node)
builder.add_node("subtopic_explainer", subtopic_explain_node)

# Entry
builder.set_entry_point("planner")

# Normal flow
builder.add_edge("planner", "researcher")

# After research → quiz
builder.add_edge("researcher", "quiz")

# quiz → evaluator
builder.add_edge("quiz", "evaluator")

# evaluator → end
builder.add_edge("evaluator", END)

# ================================
# SUBTOPIC ROUTING (NEW)
# ================================

def route_input(state):
    prompt = state["topic"].lower()

    if any(x in prompt for x in ["explain", "what is", "tell me about", "define"]):
        return "subtopic_explainer"

    return "planner"


builder.set_conditional_entry_point(
    route_input,
    {
        "subtopic_explainer": "subtopic_explainer",
        "planner": "planner"
    }
)

# subtopic explainer ends directly
builder.add_edge("subtopic_explainer", END)

graph = builder.compile()