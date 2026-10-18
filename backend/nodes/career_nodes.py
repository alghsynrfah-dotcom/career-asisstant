from langgraph.config import get_stream_writer

from backend.agent.agent import agent

MAX_CV_CHARS = 3500
MAX_JOB_CHARS = 2500
MAX_QUESTION_CHARS = 1000

VALID_TASKS = {"match", "interview", "advice"}

REQUIRED_SECTIONS = {
    "match": [
        "match score",
        "strengths",
        "gaps",
        "suggested cv improvements",
    ],
    "interview": [
        "technical questions",
        "behavioral questions",
        "preparation tips",
    ],
    "advice": [],
}

DISCLAIMER = (
    "ملاحظة: هذه النتيجة مساعدة إرشادية فقط وليست قرار توظيف "
    "ولا ضماناً للحصول على الوظيفة. راجعي الاقتراحات قبل اعتمادها."
)


# ---------- 1) التحقق من المدخلات ----------
def validate_input(state):
    task = str(state.get("task_type", "")).strip().lower()
    cv = str(state.get("cv_text", "")).strip()
    job = str(state.get("job_text", "")).strip()
    question = str(state.get("user_question", "")).strip()

    errors = []

    if task not in VALID_TASKS:
        errors.append("نوع الطلب غير صحيح.")

    if task == "match" and (not cv or not job):
        errors.append("تحليل التوافق يحتاج السيرة الذاتية وإعلان الوظيفة.")

    if task == "interview" and not job:
        errors.append("أسئلة المقابلة تحتاج إعلان الوظيفة.")

    if task == "advice" and not question:
        errors.append("اكتبي سؤالك.")

    if len(cv) > MAX_CV_CHARS:
        errors.append("السيرة الذاتية طويلة جداً.")
    if len(job) > MAX_JOB_CHARS:
        errors.append("إعلان الوظيفة طويل جداً.")
    if len(question) > MAX_QUESTION_CHARS:
        errors.append("السؤال طويل جداً.")

    # نصفّر نتائج الطلب السابق حتى ما تختلط مع الجديد
    reset = {
        "agent_answer": "",
        "final_response": "",
        "tools_used": [],
        "agent_steps": 0,
    }

    if errors:
        return {
            **reset,
            "task_type": task,
            "workflow_status": "input_invalid",
            "error": " | ".join(errors),
        }

    return {
        **reset,
        "task_type": task,
        "cv_text": cv,
        "job_text": job,
        "user_question": question,
        "workflow_status": "input_valid",
        "error": "",
    }


# ---------- 2) استدعاء الـ Agent ----------
def _run_agent(prompt, state):
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


def match_node(state):
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
    return _run_agent(prompt, state)


def interview_node(state):
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
    return _run_agent(prompt, state)


def advice_node(state):
    prompt = (
        "TASK: Answer the user's career question.\n"
        "Use the tool search_tips first and base your answer on its "
        "results. Do not invent advice that is not supported.\n\n"
        "<question>\n" + state["user_question"] + "\n</question>"
    )
    return _run_agent(prompt, state)


# ---------- 3) المراجعة والإخراج ----------
def finalize_node(state):
    answer = str(state.get("agent_answer", "")).strip()

    if not answer:
        return {
            "final_response": "تعذر إكمال الطلب: لم يرجع الوكيل أي جواب.",
            "workflow_status": "failed",
            "error": "لم يرجع الـ Agent أي جواب.",
        }

    task = state.get("task_type", "")
    lowered = answer.lower()
    missing = [
        section
        for section in REQUIRED_SECTIONS.get(task, [])
        if section not in lowered
    ]

    final = answer
    status = "completed"

    if missing:
        status = "completed_with_warnings"
        final += "\n\n(تنبيه: بعض الأقسام المتوقعة غير موجودة: " + ", ".join(missing) + ")"

    final += "\n\n---\n" + DISCLAIMER

    return {
        "final_response": final,
        "workflow_status": status,
        "history": [
            {"task_type": task, "answer": answer[:1500]}
        ],
    }


def failure_node(state):
    message = state.get("error") or "حدث خطأ غير متوقع."
    return {
        "final_response": "تعذر إكمال الطلب: " + message,
        "workflow_status": "failed",
    }