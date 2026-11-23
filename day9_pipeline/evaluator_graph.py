from langgraph.graph import StateGraph, END
import sys
import os

# -------------------------------------------------------
# Project Path
# -------------------------------------------------------

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

sys.path.append(PROJECT_ROOT)

from day9_pipeline.state import AgentState
from day9_pipeline.nodes import evaluator_node

# -------------------------------------------------------
# Build Graph
# -------------------------------------------------------

builder = StateGraph(AgentState)

# -------------------------------------------------------
# Nodes
# -------------------------------------------------------

builder.add_node(
    "evaluator",
    evaluator_node
)

# -------------------------------------------------------
# Entry Point
# -------------------------------------------------------

builder.set_entry_point("evaluator")

# -------------------------------------------------------
# Flow
# -------------------------------------------------------

builder.add_edge(
    "evaluator",
    END
)

# -------------------------------------------------------
# Compile
# -------------------------------------------------------

evaluation_graph = builder.compile()