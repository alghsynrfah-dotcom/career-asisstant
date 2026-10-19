from langchain_core.tools import tool

from backend.services.llm_service import ask_llm


@tool
def create_interview_questions(job_text: str, cv_text: str = "") -> str:
    """Generate interview questions for a job posting."""
    data = "<job>\n" + job_text + "\n</job>"

    if cv_text:
        data += "\n\n<cv>\n" + cv_text + "\n</cv>"

    try:
        return ask_llm(
            "Write 5 technical and 3 behavioral interview questions for "
            "this job (tailor them to the CV if one is given). After each "
            "question add one line on what a good answer should include. "
            "Never assume the candidate has a skill that is not written in the CV.",
            data,
        )
    except Exception as exc:
        return f"Error generating questions: {exc}"
