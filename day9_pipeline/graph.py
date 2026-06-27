from langgraph.graph import StateGraph, END

from state import AgentState
from nodes import planner_node, researcher_node


builder = StateGraph(AgentState)

builder.add_node(
    "planner",
    planner_node
)

builder.add_node(
    "researcher",
    researcher_node
)

builder.set_entry_point("planner")

builder.add_edge(
    "planner",
    "researcher"
)

builder.add_edge(
    "researcher",
    END
)

graph = builder.compile()