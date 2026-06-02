import httpx

from app.core.config import settings

_cached_embedding_dimension: int | None = None


def _get_openrouter_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY.get_secret_value()}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.OPENROUTER_SITE_URL,
        "X-Title": settings.OPENROUTER_APP_NAME,
    }


def _openrouter_embedding(text: str) -> list[float]:
    response = httpx.post(
        f"{settings.OPENROUTER_BASE_URL.rstrip('/')}/embeddings",
        json={"model": settings.OPENROUTER_EMBEDDING_MODEL, "input": text},
        headers=_get_openrouter_headers(),
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    embeddings = data.get("data") or []
    if not embeddings:
        raise ValueError("Empty OpenRouter embeddings response")

    embedding = embeddings[0].get("embedding")
    if not isinstance(embedding, list):
        raise ValueError("Invalid OpenRouter embeddings response")

    return embedding


def get_embedding_dimension() -> int:
    global _cached_embedding_dimension
    if _cached_embedding_dimension is not None:
        return _cached_embedding_dimension

    try:
        _cached_embedding_dimension = len(_openrouter_embedding("dimension probe"))
        return _cached_embedding_dimension
    except Exception:
        if settings.EMBEDDING_DIMENSION is not None:
            _cached_embedding_dimension = int(settings.EMBEDDING_DIMENSION)
            return _cached_embedding_dimension
        raise RuntimeError(
            "Unable to determine embedding dimension from OpenRouter. "
            "Set EMBEDDING_DIMENSION in .env or check OPENROUTER_API_KEY / OPENROUTER_EMBEDDING_MODEL."
        )

def generate_embedding(text: str) -> list[float]:
    """
    Generate embedding for a given text using OpenRouter.
    """
    embedding = _openrouter_embedding(text)
    if settings.EMBEDDING_DIMENSION is not None and len(embedding) != int(settings.EMBEDDING_DIMENSION):
        raise ValueError(
            f"Embedding dimension mismatch: got {len(embedding)}, expected {int(settings.EMBEDDING_DIMENSION)}"
        )
    return embedding

def create_track_text_for_embedding(track) -> str:
    """
    Combines track fields into a single rich text string for vectorization.
    """
    skills = ", ".join(track.required_skills.keys()) if track.required_skills else ""
    tasks = ", ".join(track.tasks) if track.tasks else ""
    
    text = f"Title: {track.title}\n"
    text += f"Specialization: {track.specialization}\n"
    text += f"Description: {track.description}\n"
    text += f"Required Skills: {skills}\n"
    text += f"Tasks: {tasks}\n"
    
    return text
