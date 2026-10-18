from backend.nodes.agent_runner import run_agent


def interview_node(state):
    """تحضير أسئلة المقابلة."""
    prompt = (
        "TASK: Prepare the user for an interview for this job.\n"
        "The job text (and the CV, if given) are provided to the tools "
        "automatically, so use Action Input: use_context.\n"
        "Call generate_interview_questions, and search_tips if useful.\n\n"
        "Write the final answer with exactly these sections:\n"
        "## Technical Questions\n"
        "## Behavioral Questions\n"
        "## Preparation Tips\n"
        "Base the answer only on the tool results."
    )
    return run_agent(prompt, state)
