import json
import math
import re
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional, Tuple

try:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    from backend.app.db.models import MemoryFactRecord
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    AsyncSession = Any
    MemoryFactRecord = Any

from backend.app.config import settings

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "of", "to", "in", "on", "at",
    "for", "and", "or", "but", "with", "about", "what", "who", "which", "when", "where", "why",
    "how", "do", "does", "did", "can", "could", "would", "should", "i", "you", "he", "she", "it",
    "we", "they", "me", "my", "your", "his", "her", "our", "their", "this", "that", "these",
    "those", "tell", "please", "from", "has", "have", "had", "any", "all", "so", "more", "most",
    "also", "not", "no", "by", "as", "there", "here", "am", "will", "just", "only", "than", "then"
}

RRF_K = 60

def extract_keywords(text: str) -> List[str]:
    """Tokenizes text and removes common stopwords."""
    tokens = re.findall(r"[\w]+", text.lower())
    return [t for t in tokens if len(t) > 2 and t not in STOPWORDS]

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)

async def get_embedding(text: str) -> Optional[List[float]]:
    """Fetches text embedding from Gemini API using configured keys."""
    keys = settings.parsed_gemini_keys
    if not keys:
        return None

    model = settings.gemini_embedding_model or "gemini-embedding-001"
    for key in keys:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={key}"
        payload = {
            "model": f"models/{model}",
            "content": {"parts": [{"text": text[:2048]}]}
        }
        try:
            if HAS_HTTPX:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        values = data.get("embedding", {}).get("values")
                        if values:
                            return values
            else:
                data_bytes = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode())
                        values = data.get("embedding", {}).get("values")
                        if values:
                            return values
        except Exception:
            continue
    return None

async def retrieve_relevant_facts(
    db: Any,
    query_text: str,
    top_k: int = 5
) -> List[str]:
    """
    Hybrid Retrieval fusing Vector similarity and Keyword matching via
    Reciprocal Rank Fusion (RRF).
    """
    if not HAS_SQLALCHEMY:
        return []

    result = await db.execute(select(MemoryFactRecord))
    all_facts = result.scalars().all()
    if not all_facts:
        return []

    query_keywords = set(extract_keywords(query_text))
    query_vec = await get_embedding(query_text)

    # 1. Rank by Vector Similarity
    vec_scores: List[Tuple[float, Any]] = []
    if query_vec:
        for f in all_facts:
            if f.embedding_json:
                try:
                    f_vec = json.loads(f.embedding_json)
                    sim = cosine_similarity(query_vec, f_vec)
                    vec_scores.append((sim, f))
                except Exception:
                    vec_scores.append((0.0, f))
            else:
                vec_scores.append((0.0, f))
    vec_scores.sort(key=lambda x: x[0], reverse=True)
    vec_rank = {record.id: rank + 1 for rank, (_, record) in enumerate(vec_scores)}

    # 2. Rank by Keyword Overlap
    kw_scores: List[Tuple[float, Any]] = []
    for f in all_facts:
        f_kw = set(extract_keywords(f.fact))
        overlap = len(query_keywords.intersection(f_kw))
        score = float(overlap) * f.importance
        kw_scores.append((score, f))
    kw_scores.sort(key=lambda x: x[0], reverse=True)
    kw_rank = {record.id: rank + 1 for rank, (_, record) in enumerate(kw_scores)}

    # 3. Filter candidates: must have either vector similarity >= 0.32 or keyword overlap >= 1.0
    candidates = []
    for f in all_facts:
        f_vec_sim = next((s for s, r in vec_scores if r.id == f.id), 0.0)
        f_kw_score = next((s for s, r in kw_scores if r.id == f.id), 0.0)
        if f_vec_sim >= 0.32 or f_kw_score >= 1.0:
            candidates.append(f)

    if not candidates:
        return []

    # 4. Reciprocal Rank Fusion (RRF) on relevant candidates
    rrf_list: List[Tuple[float, Any]] = []
    for f in candidates:
        r_vec = vec_rank.get(f.id, 999)
        r_kw = kw_rank.get(f.id, 999)
        rrf_score = (1.0 / (RRF_K + r_vec)) + (1.0 / (RRF_K + r_kw))
        # Boost by importance
        rrf_score *= (0.7 + 0.3 * f.importance)
        rrf_list.append((rrf_score, f))

    rrf_list.sort(key=lambda x: x[0], reverse=True)

    # Return top-k fact strings
    top_facts = [record.fact for _, record in rrf_list[:top_k]]
    return top_facts
