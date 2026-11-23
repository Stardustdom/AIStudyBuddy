from langgraph.graph import StateGraph, END
import sys
import os

PROJECT_ROOT = os.path.abspath(
    os.path.dirname(__file__)
)

sys.path.append(PROJECT_ROOT)

from day9_pipeline.state import AgentState
from day9_pipeline.nodes import quiz_node

builder = StateGraph(AgentState)

builder.add_node(
    "quiz",
    quiz_node
)

builder.set_entry_point("quiz")

builder.add_edge(
    "quiz",
    END
)

quiz_graph = builder.compile()