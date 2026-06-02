from pathlib import Path
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI SaaS Platform"
    API_V1_STR: str = "/api/v1"
    
    # Postgres
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "ai_user"
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_DB: str = "ai_saas_db"
    POSTGRES_PORT: str = "5433"
    
    # Qdrant
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_TRACKS: str = "tracks"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    
    # OpenRouter chat model
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_API_KEY: SecretStr | None = None
    OPENROUTER_MODEL: str = "qwen/qwen3.5-flash-02-23"
    OPENROUTER_EMBEDDING_MODEL: str = "nvidia/llama-nemotron-embed-vl-1b-v2:free"
    OPENROUTER_SITE_URL: str = "http://localhost:3000"
    OPENROUTER_APP_NAME: str = "AI SaaS Platform"
    OPENROUTER_TEMPERATURE: float = 0.2
    OPENROUTER_TOP_P: float = 0.9
    OPENROUTER_MAX_TOKENS: int | None = 1024

    # Embeddings
    EMBEDDING_DIMENSION: int | None = None
    QDRANT_RECREATE_COLLECTIONS: bool = False

    SECRET_KEY: SecretStr | None = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days

    # Demo users for seed script
    DEMO_BACKEND_EMAIL: str = ""
    DEMO_BACKEND_PASSWORD: SecretStr | None = None
    DEMO_DATA_EMAIL: str = ""
    DEMO_DATA_PASSWORD: SecretStr | None = None
    DEMO_EMPTY_EMAIL: str = ""
    DEMO_EMPTY_PASSWORD: SecretStr | None = None

    @field_validator("EMBEDDING_DIMENSION", mode="before")
    @classmethod
    def empty_string_to_none(cls, value):
        if value == "":
            return None
        return value
    
    class Config:
        case_sensitive = True
        env_file = (
            str(Path(__file__).resolve().parents[3] / ".env"),
            str(Path(__file__).resolve().parents[2] / ".env"),
            str(Path(__file__).resolve().parents[1] / ".env"),
        )

settings = Settings()
