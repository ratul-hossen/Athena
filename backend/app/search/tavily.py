import os
from typing import Optional, Dict, Any, List
from backend.app.config import settings

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

async def search_tavily(query: str, max_results: int = 3) -> Optional[Dict[str, Any]]:
    """
    Executes a real-time web search via Tavily API for Athina.
    Returns: {"answer": str, "results": [{"title": ..., "url": ..., "content": ...}]}
    """
    api_key = settings.tavily_api_key or os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        return None

    if not HAS_HTTPX:
        return None

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "include_answer": True,
        "max_results": max_results
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, json=payload)
            if res.status_code == 200:
                data = res.json()
                return {
                    "answer": data.get("answer", ""),
                    "results": [
                        {
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "content": item.get("content", "")
                        }
                        for item in data.get("results", [])[:max_results]
                    ]
                }
    except Exception as e:
        return None

    return None

def format_search_context(search_data: Optional[Dict[str, Any]]) -> str:
    """Formats Tavily search output as ground-truth context for Athina system prompt."""
    if not search_data:
        return ""

    answer = search_data.get("answer", "")
    results = search_data.get("results", [])

    lines = ["\n[REAL-TIME WEB SEARCH KNOWLEDGE via Tavily]:"]
    if answer:
        lines.append(f"Direct Summary: {answer}")

    for idx, r in enumerate(results, 1):
        lines.append(f"{idx}. {r['title']} ({r['url']}): {r['content'][:250]}")

    return "\n".join(lines)
