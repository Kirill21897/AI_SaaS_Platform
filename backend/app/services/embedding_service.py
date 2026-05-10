import os
import httpx
from app.core.config import settings

_cached_embedding_dimension: int | None = None

def get_embedding_dimension() -> int:
    global _cached_embedding_dimension
    if _cached_embedding_dimension is not None:
        return _cached_embedding_dimension

    if os.getenv("EMBEDDING_DIMENSION") is None:
        try:
            response = httpx.post(
                f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/embeddings",
                json={"model": settings.OLLAMA_EMBEDDING_MODEL, "prompt": "dimension probe"},
                timeout=60,
            )
            response.raise_for_status()
            embedding = response.json().get("embedding")
            if isinstance(embedding, list) and embedding:
                _cached_embedding_dimension = len(embedding)
                return _cached_embedding_dimension
        except Exception:
            pass

    _cached_embedding_dimension = int(settings.EMBEDDING_DIMENSION)
    return _cached_embedding_dimension

def _ollama_embedding(text: str) -> list[float]:
    response = httpx.post(
        f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/embeddings",
        json={"model": settings.OLLAMA_EMBEDDING_MODEL, "prompt": text},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    embedding = data.get("embedding")
    if not isinstance(embedding, list):
        raise ValueError("Invalid Ollama embeddings response")
    return embedding

def generate_embedding(text: str) -> list[float]:
    """
    Generate embedding for a given text using Ollama.
    """
    embedding = _ollama_embedding(text)
    if os.getenv("EMBEDDING_DIMENSION") is not None and len(embedding) != int(settings.EMBEDDING_DIMENSION):
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
