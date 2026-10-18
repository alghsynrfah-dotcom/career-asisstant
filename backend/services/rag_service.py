import hashlib
import os

import requests
import re
from typing import Any

import psycopg
from dotenv import load_dotenv

load_dotenv()

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
DEFAULT_RESULTS = 5
MIN_SCORE = 0.0

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

_embeddings = None


def _connect():
    if DATABASE_URL:
        return psycopg.connect(DATABASE_URL)

    return psycopg.connect(
        dbname=os.getenv("PGDATABASE", "career_assistant"),
        user=os.getenv("PGUSER") or None,
        host=os.getenv("PGHOST", "/var/run/postgresql"),
    )


def init_rag_db() -> None:
    """ينشئ الجداول المطلوبة."""
    with _connect() as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS career_tips (
                tip_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS career_tip_chunks (
                chunk_id TEXT PRIMARY KEY,
                tip_id TEXT NOT NULL
                    REFERENCES career_tips(tip_id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                embedding vector,
                UNIQUE(tip_id, chunk_index)
            )
        """)

        # عمود البحث النصي (بديل لما الـ embeddings ما تكون متاحة)
        conn.execute("""
            ALTER TABLE career_tip_chunks
            ADD COLUMN IF NOT EXISTS search_vector tsvector
            GENERATED ALWAYS AS (to_tsvector('english', chunk_text)) STORED
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_notes (
                note_id SERIAL PRIMARY KEY,
                note TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        conn.commit()


def _clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _split_into_chunks(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    text = _clean_text(text)

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - overlap

    return chunks


def _get_embeddings():
    global _embeddings

    if _embeddings is None:
        from langchain_openai import OpenAIEmbeddings

        api_url = (os.getenv("VLLM_API_URL") or "").strip()
        api_key = (os.getenv("VLLM_API_KEY") or "").strip()
        model_name = (
            os.getenv("EMBEDDING_MODEL") or os.getenv("MODEL_NAME") or ""
        ).strip()

        if not api_url or not api_key or not model_name:
            raise ValueError(
                "VLLM_API_URL, VLLM_API_KEY and MODEL_NAME (or "
                "EMBEDDING_MODEL) are required in .env"
            )

        _embeddings = OpenAIEmbeddings(
            model=model_name,
            api_key=api_key,
            base_url=api_url,
            timeout=120,
            chunk_size=16,
            check_embedding_ctx_length=False,
        )

    return _embeddings


def _embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    url = (os.getenv("EMBEDDING_API_URL") or "").strip()
    key = (os.getenv("EMBEDDING_API_KEY") or "").strip()
    model = (os.getenv("EMBEDDING_MODEL") or "BAAI/bge-large-en-v1.5").strip()

    if not url:
        raise ValueError("EMBEDDING_API_URL is required in .env")

    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    vectors = []
    for i in range(0, len(texts), 16):
        batch = texts[i:i + 16]
        r = requests.post(
            url,
            headers=headers,
            json={"model": model, "input": batch},
            timeout=120,
        )
        r.raise_for_status()
        data = sorted(r.json()["data"], key=lambda d: d["index"])
        vectors.extend(d["embedding"] for d in data)

    return vectors


def _embed_query(text: str) -> list[float]:
    return _embed_texts([text])[0]


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.6f}" for value in vector) + "]"


def save_tip(title: str, text: str, category: str = "general") -> dict:
    """يحفظ نصيحة: chunking ثم embedding (إذا متاح) ثم تخزين."""
    title = _clean_text(title) or "Untitled tip"
    category = _clean_text(category) or "general"
    content = _clean_text(text)

    if not content:
        raise ValueError("Tip text is empty.")

    tip_id = hashlib.sha256(title.encode("utf-8")).hexdigest()
    chunks = _split_into_chunks(content)

    # إذا السيرفر ما بيدعم embeddings منحفظ النص بدون vectors
    try:
        vectors = _embed_texts(chunks)
        if len(vectors) != len(chunks):
            raise ValueError("Embedding count does not match chunk count.")
    except Exception as exc:
        print(
            f"[RAG] embeddings unavailable, saving without vectors: "
            f"{type(exc).__name__}",
            flush=True,
        )
        vectors = [None] * len(chunks)

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO career_tips (tip_id, title, category)
            VALUES (%s, %s, %s)
            ON CONFLICT (tip_id) DO UPDATE SET
                title = EXCLUDED.title,
                category = EXCLUDED.category
            """,
            (tip_id, title, category),
        )

        conn.execute(
            "DELETE FROM career_tip_chunks WHERE tip_id = %s",
            (tip_id,),
        )

        for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
            chunk_id = hashlib.sha256(
                f"{tip_id}:{index}".encode("utf-8")
            ).hexdigest()

            conn.execute(
                """
                INSERT INTO career_tip_chunks
                    (chunk_id, tip_id, chunk_index, chunk_text, embedding)
                VALUES (%s, %s, %s, %s, %s::vector)
                """,
                (
                    chunk_id,
                    tip_id,
                    index,
                    chunk,
                    _vector_literal(vector) if vector else None,
                ),
            )

        conn.commit()

    return {
        "status": "saved",
        "title": title,
        "chunks_saved": len(chunks),
        "with_embeddings": vectors[0] is not None,
    }


def _keyword_search(query: str, n_results: int) -> list[dict]:
    """بحث نصي بالـ PostgreSQL، بيشتغل بدون embeddings."""
    words = [
        w for w in re.findall(r"[A-Za-z0-9]+", query.lower()) if len(w) > 2
    ]

    if not words:
        return []

    tsquery = " | ".join(words)

    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                c.chunk_text,
                t.title,
                t.category,
                ts_rank(c.search_vector, to_tsquery('english', %s)) AS score
            FROM career_tip_chunks AS c
            JOIN career_tips AS t ON t.tip_id = c.tip_id
            WHERE c.search_vector @@ to_tsquery('english', %s)
            ORDER BY score DESC
            LIMIT %s
            """,
            (tsquery, tsquery, n_results),
        ).fetchall()

    return [
        {
            "text": row[0],
            "title": row[1],
            "category": row[2],
            "score": float(row[3]),
        }
        for row in rows
    ]


def search_tips(query: str, n_results: int = DEFAULT_RESULTS) -> dict:
    """بحث بالمعنى (embedding)، وإذا مو متاح بنرجع للبحث النصي."""
    query = _clean_text(query)

    if not query:
        raise ValueError("Search query cannot be empty.")
    if len(query) > 1000:
        raise ValueError("Search query must not exceed 1000 characters.")

    n_results = max(1, min(int(n_results), 10))
    results = []
    search_type = "vector_cosine_similarity"

    try:
        query_vector = _vector_literal(_embed_query(query))

        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    c.chunk_text,
                    t.title,
                    t.category,
                    1 - (c.embedding <=> %s::vector) AS score
                FROM career_tip_chunks AS c
                JOIN career_tips AS t ON t.tip_id = c.tip_id
                WHERE c.embedding IS NOT NULL
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
                """,
                (query_vector, query_vector, n_results),
            ).fetchall()

        results = [
            {
                "text": row[0],
                "title": row[1],
                "category": row[2],
                "score": float(row[3]),
            }
            for row in rows
            if float(row[3]) >= MIN_SCORE
        ]
    except Exception as exc:
        print(
            f"[RAG] vector search unavailable: {type(exc).__name__}",
            flush=True,
        )

    if not results:
        results = _keyword_search(query, n_results)
        search_type = "keyword_fulltext"

    return {
        "query": query,
        "results": results,
        "result_count": len(results),
        "search_type": search_type,
        "message": "" if results else "No matching tips found.",
    }


def save_note(note: str) -> dict:
    note = _clean_text(note)

    if not note:
        raise ValueError("Note is empty.")

    with _connect() as conn:
        conn.execute("INSERT INTO session_notes (note) VALUES (%s)", (note,))
        conn.commit()

    # كمان منحفظها بالـ RAG حتى الـ agent يقدر يبحث فيها لاحقاً
    note_key = hashlib.sha256(note.encode("utf-8")).hexdigest()[:8]
    searchable = True

    try:
        save_tip(
            title=f"My note: {note[:40]} ({note_key})",
            text=note,
            category="my_note",
        )
    except Exception as exc:
        searchable = False
        print(
            f"[RAG] note saved but not searchable: {type(exc).__name__}",
            flush=True,
        )

    return {"status": "saved", "searchable": searchable}


# تأكد إنو الجداول موجودة عند الاستيراد
init_rag_db()

# ---------------------------------------------------------------------------
# دفتر المستخدم: معلومات بيحفظها المستخدم بإرادتو (مو النصائح الثابتة)
# ---------------------------------------------------------------------------
USER_CATEGORIES = ("my_note", "my_analysis")


def save_user_entry(title: str, text: str, category: str = "my_analysis") -> dict:
    """يحفظ مدخل من المستخدم بالـ RAG (الفجوات واقتراحات التحسين مثلاً)."""
    if category not in USER_CATEGORIES:
        raise ValueError("Invalid category.")

    title = _clean_text(title)[:100]
    text = _clean_text(text)

    if not title or not text:
        raise ValueError("Title and text are required.")

    # العنوان بيدخل بنص البحث حتى المدخل ينلاقي بسهولة
    return save_tip(
        title=f"My analysis: {title}",
        text=f"{title}. {text}",
        category=category,
    )


def list_user_entries() -> list[dict]:
    """يرجّع مدخلات المستخدم (الملاحظات والتحليلات المحفوظة) مع معاينة."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                t.tip_id,
                t.title,
                t.category,
                t.created_at,
                (
                    SELECT c.chunk_text
                    FROM career_tip_chunks AS c
                    WHERE c.tip_id = t.tip_id
                    ORDER BY c.chunk_index
                    LIMIT 1
                )
            FROM career_tips AS t
            WHERE t.category = ANY(%s)
            ORDER BY t.created_at DESC
            LIMIT 50
            """,
            (list(USER_CATEGORIES),),
        ).fetchall()

    return [
        {
            "id": row[0],
            "title": row[1],
            "category": row[2],
            "created_at": row[3].isoformat(),
            "preview": (row[4] or "")[:200],
        }
        for row in rows
    ]


def delete_user_entry(tip_id: str) -> bool:
    """يحذف مدخل للمستخدم فقط (النصائح الأساسية ما بتنحذف من هون)."""
    with _connect() as conn:
        cursor = conn.execute(
            "DELETE FROM career_tips WHERE tip_id = %s AND category = ANY(%s)",
            (tip_id, list(USER_CATEGORIES)),
        )
        conn.commit()
        return cursor.rowcount > 0
