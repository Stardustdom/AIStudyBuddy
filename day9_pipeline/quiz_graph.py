from langgraph.graph import StateGraph, END
import sys
import os

PROJECT_ROOT = os.path.abspath(
    os.path.dirname(__file__)
)

sys.path.append(PROJECT_ROOT)

from state import AgentState
from nodes import quiz_node

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