from typing import Annotated, TypedDict
import operator


class CareerState(TypedDict, total=False):
    # Input
    task_type: str        # match | interview | advice
    cv_text: str
    job_text: str
    user_question: str

    # Agent output
    agent_answer: str
    agent_steps: int
    tools_used: list

    # Final output
    final_response: str

    # Session memory (بتتراكم مع كل طلب بنفس الجلسة)
    history: Annotated[list, operator.add]

    # Workflow control
    workflow_status: str
    error: str