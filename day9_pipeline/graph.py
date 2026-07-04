from langgraph.graph import StateGraph, END

from day9_pipeline.state import AgentState
from day9_pipeline.nodes import (
    planner_node,
    researcher_node
)

builder = StateGraph(AgentState)

# ===========================
# Nodes
# ===========================

builder.add_node(
    "planner",
    planner_node
)

builder.add_node(
    "researcher",
    researcher_node
)

# ===========================
# Entry
# ===========================

builder.set_entry_point("planner")

# ===========================
# Flow
# ===========================

builder.add_edge(
    "planner",
    "researcher"
)

builder.add_edge(
    "researcher",
    END
)

graph = builder.compile()