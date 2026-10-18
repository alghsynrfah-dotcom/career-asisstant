MAX_CV_CHARS = 3500
MAX_JOB_CHARS = 2500
MAX_QUESTION_CHARS = 1000

VALID_TASKS = {"match", "interview", "advice"}


def validate_input(state):
    """التحقق من المدخلات + تصفير نتائج الطلب السابق."""
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
