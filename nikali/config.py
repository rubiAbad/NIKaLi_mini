"""Configuración compartida. Esta mini versión usa Qwen 3B y BGE-M3."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    BASE_DIR: Path = ROOT
    LLM_PROVIDER: str = "ollama"
    EMBED_PROVIDER: str = "sentence-transformers"
    VECTOR_DB: str = "qdrant-local"
    CHAT_MODEL: str = "qwen2.5:3b"
    EMBED_MODEL: str = "BAAI/bge-m3"
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST") or "http://localhost:11434"
    # CPU por defecto para compartir la misma configuración en Windows y Mac.
    EMBED_DEVICE: str = os.getenv("NIKALI_EMBED_DEVICE") or "cpu"
    TOP_K: int = 1


settings = Settings()
CHAT_MODEL = settings.CHAT_MODEL
EMBED_MODEL = settings.EMBED_MODEL
OLLAMA_HOST = settings.OLLAMA_HOST
TOP_K = settings.TOP_K
CORPUS_PATH = ROOT / "output_marker/stewart_regla_cadena/fragmento_corregido.md"


def make_client(host=OLLAMA_HOST, timeout=300):
    from ollama import Client

    return Client(host=host, timeout=timeout)


def make_embedder(model=EMBED_MODEL, *, local_files_only=False):
    """Reutiliza la caché; el diagnóstico puede impedir descargas."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model, device=settings.EMBED_DEVICE,
                               local_files_only=local_files_only)
