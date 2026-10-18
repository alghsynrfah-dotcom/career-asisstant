from backend.nodes.agent_runner import run_agent


def advice_node(state):
    """الإجابة على سؤال مهني من قاعدة النصائح (RAG)."""
    prompt = (
        "TASK: Answer the user's career question.\n"
        "Use the tool search_tips first and base your answer on its "
        "results. Do not invent advice that is not supported.\n\n"
        "<question>\n" + state["user_question"] + "\n</question>"
    )
    return run_agent(prompt, state)
