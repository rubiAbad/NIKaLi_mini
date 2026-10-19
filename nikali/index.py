"""Paquete portable del corpus: JSON verificable, sin ejecutar pickle ni modelos al leer."""
import hashlib
import json
import math
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from tempfile import NamedTemporaryFile

from nikali.config import (CORPUS_PATH, EMBED_DIMENSION, EMBED_MODEL, EMBED_REVISION,
                           INDEX_CACHE, PREPARED_PATH, ROOT, make_embedder)
from nikali.rag import Chunk, Retriever, corpus_digest, cosine, encode_texts, load_chunks

SCHEMA_VERSION = 1
CHUNKER_VERSION = "markdown-headings-v1"
PROFILE = {"model": EMBED_MODEL, "revision": EMBED_REVISION, "dimension": EMBED_DIMENSION,
           "normalize_embeddings": True, "distance": "Cosine"}


class PreparedIndexError(ValueError):
    pass


@dataclass(frozen=True)
class PreparedCorpus:
    chunks: tuple
    vectors: tuple
    digest: str
    manifest: dict


def canonical_digest(value):
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def source_digest(path):
    # read_text normaliza CRLF de Windows a LF; el hash es portable.
    return hashlib.sha256(Path(path).read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def load_prepared(path=PREPARED_PATH, *, source=CORPUS_PATH):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        claimed = data.pop("sha256")
        if canonical_digest(data) != claimed:
            raise ValueError("El checksum del paquete no coincide.")
        if data["schema_version"] != SCHEMA_VERSION or data["chunker_version"] != CHUNKER_VERSION:
            raise ValueError("Versión de paquete o chunking incompatible.")
        if data["embedding"] != PROFILE:
            raise ValueError("Modelo, revisión o configuración de embeddings incompatible.")
        if data["source"]["sha256"] != source_digest(source):
            raise ValueError("El Markdown cambió después de preparar los embeddings.")
        source_name = CORPUS_PATH.relative_to(ROOT).as_posix()
        if data["source"]["path"] != source_name:
            raise ValueError("La fuente del paquete no es el fragmento configurado.")
        chunks = tuple(Chunk(**row) for row in data["chunks"])
        if not chunks or len({c.id for c in chunks}) != len(chunks):
            raise ValueError("Chunks vacíos o IDs duplicados.")
        if any(not isinstance(c.text, str) or not c.text.strip() or c.source != source_name for c in chunks):
            raise ValueError("Texto o fuente de chunk inválido.")
        if corpus_digest(chunks) != data["corpus_sha256"]:
            raise ValueError("El contenido de los chunks no coincide con su hash.")
        vectors = tuple(tuple(v) for v in data["vectors"])
        if len(vectors) != len(chunks):
            raise ValueError("Faltan vectores para los chunks.")
        for v in vectors:
            if len(v) != EMBED_DIMENSION or any(type(x) not in (int, float) for x in v):
                raise ValueError("Dimensión o valores de embeddings inválidos.")
            cosine(vectors[0], v)
            if not math.isclose(sum(x*x for x in v), 1, rel_tol=1e-4, abs_tol=1e-4):
                raise ValueError("Se requieren vectores normalizados.")
        return PreparedCorpus(chunks, vectors, claimed, data)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise PreparedIndexError(
            f"No se puede usar el material preparado: {exc} "
            "Actualiza data/rag_preparado.json junto con el Markdown. "
            "Solo quien prepara el material debe ejecutar python preparar_indice.py --recrear."
        ) from exc


def prepare_index(path=PREPARED_PATH, *, recreate=False):
    path = Path(path)
    if path.exists() and not recreate:
        return load_prepared(path)  # idempotente: no carga modelos ni recalcula
    before = source_digest(CORPUS_PATH)
    chunks = load_chunks()
    encoder = make_embedder()
    vectors = encode_texts(encoder, [c.text for c in chunks])
    if source_digest(CORPUS_PATH) != before:
        raise PreparedIndexError("El material cambió durante la preparación; vuelve a intentarlo.")
    data = {"schema_version": SCHEMA_VERSION, "chunker_version": CHUNKER_VERSION,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "embedding": PROFILE,
            "libraries": {p: version(p) for p in ("sentence-transformers", "transformers", "torch")},
            "source": {"path": CORPUS_PATH.relative_to(ROOT).as_posix(), "sha256": before},
            "corpus_sha256": corpus_digest(chunks), "chunks": [asdict(c) for c in chunks],
            "vectors": vectors}
    data["sha256"] = canonical_digest(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False) as file:
            temporary = Path(file.name)
            json.dump(data, file, ensure_ascii=False, indent=2, allow_nan=False)
            file.write("\n")
        prepared = load_prepared(temporary)
        os.replace(temporary, path)  # conservar el anterior si falla preparación/validación
        return prepared
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def open_retriever(prepared=None, *, consumer="cli", encoder=None, cache_root=INDEX_CACHE):
    if consumer not in {"web", "cli", "diagnostico"}:
        raise ValueError("Consumidor desconocido.")
    prepared = prepared if prepared is not None else load_prepared()
    # Cada consumidor tiene su copia local para no competir por el bloqueo de Qdrant.
    path = Path(cache_root) / prepared.digest / consumer
    return Retriever(prepared.chunks, prepared.vectors, encoder=encoder,
                     index_path=path, bundle_id=prepared.digest)
