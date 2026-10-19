"""Comprobaciones de arranque sin generar respuestas ni descargar pesos."""
from nikali.config import CHAT_MODEL


class StartupError(RuntimeError):
    pass


def check_ollama(client, model=CHAT_MODEL):
    try:
        response = client.list()
        names = {item.get("model") or item.get("name") for item in response["models"]}
    except Exception as exc:
        raise StartupError(
            "No se pudo consultar Ollama. Abre la aplicación Ollama o ejecuta "
            "ollama serve en otra terminal. Si configuraste OLLAMA_HOST, verifica esa dirección."
        ) from exc
    if model not in names:
        raise StartupError(f"Ollama está disponible, pero falta {model}. Ejecuta: ollama pull {model}")
    return model
