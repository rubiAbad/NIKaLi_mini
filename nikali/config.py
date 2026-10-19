import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHAT_MODEL = os.getenv("NIKALI_CHAT_MODEL", "qwen2.5:3b")
EMBED_MODEL = os.getenv("NIKALI_EMBED_MODEL", "nomic-embed-text")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
TOP_K = 1


def make_client():
    from ollama import Client

    return Client(host=OLLAMA_HOST, timeout=120)
