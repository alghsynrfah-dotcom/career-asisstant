from langchain_core.tools import tool

from backend.services.llm_service import ask_llm


@tool
def extract_cv_info(cv_text: str) -> str:
    """Extract skills, experience, projects, education and languages from CV text."""
    try:
        return ask_llm(
            "Extract from the CV: Skills, Work Experience (title, company, "
            "duration), Projects (what was built and with which technologies), "
            "Education, Certifications, Languages. Use short bullet lists. "
            "Use only what is written in the CV; write 'Not mentioned' if "
            "something is missing. Do NOT include phone, email, or address.",
            cv_text,
        )
    except Exception as exc:
        return f"Error parsing CV: {exc}"
