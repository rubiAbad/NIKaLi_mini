from pathlib import Path
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Providers: 'ollama'|'openai'|'mock'
    LLM_PROVIDER: str = "ollama"
    EMBED_PROVIDER: str = "nomic"
    VECTOR_DB: str = "memory"

    # Qdrant settings (si se usa)
    QDRANT_URL: str | None = None
    QDRANT_API_KEY: str | None = None

    # Ollama/OpenAI hosts & keys
    OLLAMA_HOST: str | None = None
    OPENAI_API_KEY: str | None = None

    BASE_DIR: Path = Path(__file__).resolve().parent

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
