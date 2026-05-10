import openai
import hashlib
import random
from app.core.config import settings

# Initialize OpenAI client
client = openai.OpenAI(
    api_key=settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY,
    base_url=settings.OPENROUTER_BASE_URL if settings.OPENROUTER_API_KEY else None
)

EMBEDDING_DIMENSION = 1536

def _deterministic_mock_embedding(text: str) -> list[float]:
    """
    Build a stable pseudo-embedding for local/dev mode.
    Same input text always produces the same vector, which keeps
    Qdrant indexing/search behavior reproducible.
    """
    text = text or ""
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed)
    return [rng.uniform(-1, 1) for _ in range(EMBEDDING_DIMENSION)]

def generate_embedding(text: str) -> list[float]:
    """
    Generate embedding for a given text using OpenAI API.
    In a real app, this calls the OpenAI API.
    For local testing without a real key, we return a mock vector.
    """
    try:
        api_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY
        # If using a mock key, return a mock embedding (1536 dimensions for text-embedding-3-small)
        if not api_key or "mock-key" in api_key:
            return _deterministic_mock_embedding(text)
            
        # Note: OpenRouter might not support embeddings for all models. 
        # If using OpenRouter, you might need a specific provider's embedding model.
        # Fallback to OpenAI for embeddings if OpenRouter doesn't support the requested model
        
        # Determine if we should use OpenAI client directly for embeddings
        # since OpenRouter is mainly for chat completions
        if settings.OPENROUTER_API_KEY and settings.OPENAI_API_KEY and "mock-key" not in settings.OPENAI_API_KEY:
            # We have both, use OpenAI for embeddings
            temp_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            response = temp_client.embeddings.create(
                input=text,
                model=settings.EMBEDDING_MODEL
            )
            return response.data[0].embedding
            
        # Try with whatever client is configured
        response = client.embeddings.create(
            input=text,
            model=settings.EMBEDDING_MODEL
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        # Return mock on failure to not break the pipeline during dev
        return _deterministic_mock_embedding(text)

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
