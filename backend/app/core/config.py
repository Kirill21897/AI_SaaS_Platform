from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI SaaS Platform"
    API_V1_STR: str = "/api/v1"
    
    # Postgres
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "ai_user"
    POSTGRES_PASSWORD: str = "ai_password"
    POSTGRES_DB: str = "ai_saas_db"
    POSTGRES_PORT: str = "5433"
    
    # Qdrant
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_TRACKS: str = "tracks"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    
    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_CHAT_MODEL: str = "qwen2.5:7b"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    OLLAMA_KEEP_ALIVE: str = "30m"
    OLLAMA_NUM_CTX: int = 2048
    OLLAMA_NUM_PREDICT: int = 256
    OLLAMA_NUM_THREAD: int | None = None
    OLLAMA_NUM_BATCH: int | None = None
    OLLAMA_TEMPERATURE: float = 0.2
    OLLAMA_TOP_P: float = 0.9
    OLLAMA_REPEAT_PENALTY: float = 1.1
    EMBEDDING_DIMENSION: int = 1536
    QDRANT_RECREATE_COLLECTIONS: bool = False

    SECRET_KEY: str = "CHANGE_ME_SECRET_KEY"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    class Config:
        case_sensitive = True
        env_file = (
            str(Path(__file__).resolve().parents[2] / ".env"),
            str(Path(__file__).resolve().parents[1] / ".env"),
        )

settings = Settings()
