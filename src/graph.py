from __future__ import annotations

from langgraph.graph import END, StateGraph

from nodes.evaluate_node import evaluate_node
from nodes.filter_node import filter_node
from nodes.report_node import report_node
from nodes.retrieve_node import retrieve_node
from state import AgentState


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("filter", filter_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("report", report_node)
    graph.set_entry_point("filter")
    graph.add_edge("filter", "retrieve")
    graph.add_edge("retrieve", "evaluate")
    graph.add_edge("evaluate", "report")
    graph.add_edge("report", END)
    return graph.compile()
