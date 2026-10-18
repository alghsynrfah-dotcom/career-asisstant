from backend.nodes.agent_runner import run_agent


def match_node(state):
    """تحليل توافق الـ CV مع الوظيفة."""
    prompt = (
        "TASK: Analyze how well the user's CV matches the job posting.\n"
        "The CV and the job text are provided to the tools automatically, "
        "so use Action Input: use_context.\n"
        "Call parse_cv first, then match_job. "
        "Use search_tips only if it helps.\n\n"
        "Write the final answer with exactly these sections:\n"
        "## Match Score\n"
        "## Strengths\n"
        "## Gaps\n"
        "## Suggested CV Improvements\n"
        "Base the answer only on the tool results. "
        "Do not present the result as a hiring decision."
    )
    return run_agent(prompt, state)
