from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from backend.graph.state import CareerState
from backend.nodes.validate_input import validate_input
from backend.nodes.match_node import match_node
from backend.nodes.interview_node import interview_node
from backend.nodes.advice_node import advice_node
from backend.nodes.finalize_node import finalize_node
from backend.nodes.failure_node import failure_node


def input_router(state: CareerState):
    """Router: يوجّه الطلب حسب task_type."""
    if state.get("workflow_status") != "input_valid":
        return "failure"
    return state["task_type"]  # match | interview | advice


def agent_router(state: CareerState):
    """بعد الـ Agent: إذا في خطأ نروح للـ failure، وإلا للـ finalize."""
    if state.get("workflow_status") == "agent_failed" or state.get("error"):
        return "failure"
    return "finalize"


builder = StateGraph(CareerState)

builder.add_node("validate_input", validate_input)
builder.add_node("match_node", match_node)
builder.add_node("interview_node", interview_node)
builder.add_node("advice_node", advice_node)
builder.add_node("finalize", finalize_node)
builder.add_node("failure", failure_node)

builder.add_edge(START, "validate_input")

builder.add_conditional_edges(
    "validate_input",
    input_router,
    {
        "match": "match_node",
        "interview": "interview_node",
        "advice": "advice_node",
        "failure": "failure",
    },
)

for node_name in ("match_node", "interview_node", "advice_node"):
    builder.add_conditional_edges(
        node_name,
        agent_router,
        {"finalize": "finalize", "failure": "failure"},
    )

builder.add_edge("finalize", END)
builder.add_edge("failure", END)

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)