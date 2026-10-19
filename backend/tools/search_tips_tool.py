import json

from langchain_core.tools import tool

from backend.services.rag_service import search_tips as rag_search_tips


@tool
def find_career_tips(query: str, n_results: int = 5) -> str:
    """Search the career tips knowledge base."""
    try:
        result = rag_search_tips(query=query, n_results=n_results)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as exc:
        return f"Error searching tips: {exc}"
