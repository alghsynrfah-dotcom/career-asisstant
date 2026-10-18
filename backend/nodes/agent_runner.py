from langgraph.config import get_stream_writer

from backend.agent.agent import agent


def run_agent(prompt, state):
    """يشغّل الـ agent وبيرجّع تحديث للـ State (نجاح أو فشل)."""
    try:
        writer = get_stream_writer()
    except Exception:
        writer = None

    try:
        result = agent(
            prompt,
            {
                "cv_text": state.get("cv_text", ""),
                "job_text": state.get("job_text", ""),
            },
            writer,
        )
    except Exception as exc:
        print(f"[AGENT] unexpected failure: {type(exc).__name__}", flush=True)
        return {
            "workflow_status": "agent_failed",
            "error": "حدث خطأ غير متوقع أثناء تشغيل الوكيل.",
            "tools_used": [],
            "agent_steps": 0,
        }

    if result.get("error"):
        return {
            "workflow_status": "agent_failed",
            "error": result["error"],
            "tools_used": result.get("tools_used", []),
            "agent_steps": result.get("agent_steps", 0),
        }

    return {
        "agent_answer": result.get("answer", ""),
        "tools_used": result.get("tools_used", []),
        "agent_steps": result.get("agent_steps", 0),
        "workflow_status": "agent_done",
        "error": "",
    }
