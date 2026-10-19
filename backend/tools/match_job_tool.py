from langchain_core.tools import tool

from backend.services.llm_service import ask_llm


@tool
def compare_cv_with_job(cv_text: str, job_text: str) -> str:
    """Compare a CV with a job posting."""
    try:
        return ask_llm(
            "Compare the CV with the job posting. Return: "
            "1) Required skills found in the CV, "
            "2) Required skills missing from the CV, "
            "3) Experience level fit, "
            "4) A rough match percentage with a one or two sentence reason. "
            "Base everything only on the two texts. "
            "Only list a skill as found if it is explicitly written in the CV. "
            "Do not count a skill as a strength if the CV describes it as weak "
            "or average. If nothing matches, say so clearly.",
            "<cv>\n" + cv_text + "\n</cv>\n\n"
            "<job>\n" + job_text + "\n</job>",
        )
    except Exception as exc:
        return f"Error matching job: {exc}"
