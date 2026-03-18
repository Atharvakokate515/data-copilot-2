# backend/graph/graph.py

from langgraph.graph import StateGraph, START, END

from core.state import AgentState
from graph.planner_node import plan_tools
from graph.execution_node import execute_tools
from graph.synthesis_node import synthesize_answer

# ── REASONING LAYER IMPORT (commented out) ───────────────────────
# Uncomment when upgrading to Claude or GPT-4.
# The reasoning node sits between execution and synthesis and does
# structured metric/threshold extraction before the final answer.
#
# from graph.reasoning_node import run_reasoning   # (file provided separately)
# ─────────────────────────────────────────────────────────────────


def build_graph():

    graph = StateGraph(AgentState)

    graph.add_node("plan_tools", plan_tools)
    graph.add_node("execute_tools", execute_tools)
    graph.add_node("synthesize_answer", synthesize_answer)

    # ── REASONING NODE (commented out) ───────────────────────────
    # Uncomment these 3 lines and remove the direct execute→synthesize
    # edge below to insert the reasoning layer into the pipeline.
    #
    # graph.add_node("run_reasoning", run_reasoning)
    # graph.add_edge("execute_tools", "run_reasoning")
    # graph.add_edge("run_reasoning", "synthesize_answer")
    # ─────────────────────────────────────────────────────────────

    graph.add_edge(START, "plan_tools")
    graph.add_edge("plan_tools", "execute_tools")
    graph.add_edge("execute_tools", "synthesize_answer")   # remove this line when enabling reasoning node
    graph.add_edge("synthesize_answer", END)

    return graph.compile()