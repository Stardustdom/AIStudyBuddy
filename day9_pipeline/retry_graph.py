from langgraph.graph import StateGraph, END
import os
import sys

# -------------------------------------------------------
# Project Path
# -------------------------------------------------------

PROJECT_ROOT = os.path.abspath(
    os.path.dirname(__file__)
)

sys.path.append(PROJECT_ROOT)

from state import AgentState
from nodes import quiz_node

# -------------------------------------------------------
# Build Graph
# -------------------------------------------------------

builder = StateGraph(AgentState)

# -------------------------------------------------------
# Nodes
# -------------------------------------------------------

builder.add_node(
    "quiz",
    quiz_node
)

# -------------------------------------------------------
# Entry Point
# -------------------------------------------------------

builder.set_entry_point("quiz")

# -------------------------------------------------------
# Flow
# -------------------------------------------------------

builder.add_edge(
    "quiz",
    END
)

# -------------------------------------------------------
# Compile
# -------------------------------------------------------

retry_graph = builder.compile()