import json

from langchain_core.tools import tool

from backend.services.rag_service import save_note as rag_save_note


@tool
def store_note(note: str) -> str:
    """Save a short user note."""
    try:
        return json.dumps(rag_save_note(note), ensure_ascii=False)
    except Exception as exc:
        return f"Error saving note: {exc}"
