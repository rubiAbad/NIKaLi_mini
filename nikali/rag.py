"""Un único pipeline de recuperación para todas las entradas del proyecto."""
import hashlib
import math
import re
import unicodedata
from dataclasses import dataclass
from threading import RLock

from nikali.config import CORPUS_PATH, EMBED_MODEL, ROOT, TOP_K, make_embedder


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    source: str
    section: str
    partial: bool = False


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float


def split_markdown(text, source_id, source):
    """Divide por encabezados fuera de bloques de código; conserva fórmulas."""
    sections, lines, title, fence = [], [], "Introducción", None
    for line in text.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
        heading = re.match(r"^#{1,6}\s+(.+?)\s*$", line) if fence is None and not marker else None
        if heading:
            if lines and "\n".join(lines).strip():
                sections.append((title, "\n".join(lines).strip()))
            title, lines = heading.group(1), [line]
        else:
            lines.append(line)
    if lines and "\n".join(lines).strip():
        sections.append((title, "\n".join(lines).strip()))
    chunks = []
    seen = set()
    for title, body in sections:
        slug = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
        slug = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")
        chunk_id = f"{source_id}:{slug}"
        if chunk_id in seen:
            raise ValueError(f"Encabezado repetido: {title}; usa títulos únicos para IDs estables.")
        seen.add(chunk_id)
        chunks.append(Chunk(chunk_id, body, source, title))
    return tuple(chunks)


def load_chunks():
    fragment = CORPUS_PATH
    if not fragment.is_file():
        raise FileNotFoundError(f"Falta el material del libro: {fragment}. Actualiza el repositorio conservando sus carpetas.")
    original = split_markdown(fragment.read_text(encoding="utf-8"), "stewart", fragment.relative_to(ROOT).as_posix())
    # El fragmento original termina al empezar la demostración. No se completa
    # silenciosamente ni se atribuyen al libro explicaciones añadidas.
    original = tuple(Chunk(c.id, c.text, c.source, c.section, "demostracion" in c.id) for c in original)
    return original


def corpus_digest(chunks):
    payload = "\n".join(f"{c.id}\n{c.source}\n{c.partial}\n{c.text}" for c in chunks)
    return hashlib.sha256(payload.encode()).hexdigest()


def cosine(a, b):
    if not a or len(a) != len(b):
        raise ValueError("Embeddings vacíos o con dimensiones distintas.")
    if not all(math.isfinite(x) for x in (*a, *b)):
        raise ValueError("El embedding contiene valores no finitos.")
    na, nb = math.sqrt(sum(x*x for x in a)), math.sqrt(sum(x*x for x in b))
    if not na or not nb:
        raise ValueError("El modelo devolvió un embedding nulo.")
    return sum(x*y for x, y in zip(a, b)) / (na * nb)


def encode_texts(encoder, texts):
    vectors = encoder.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    vectors = [list(map(float, vector)) for vector in vectors]
    if len(vectors) != len(texts):
        raise ValueError("BGE-M3 no devolvió todos los embeddings solicitados.")
    return vectors


class Retriever:
    """Consulta vectores ya preparados. Nunca hace embeddings del corpus."""
    def __init__(self, chunks, vectors, model=EMBED_MODEL, *, encoder=None,
                 index_path=None, bundle_id=None):
        from pathlib import Path
        import weakref
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct

        if not chunks or len(chunks) != len(vectors):
            raise ValueError("Chunks vacíos o cantidad de vectores incompatible.")
        self.chunks, self.model = tuple(chunks), model
        self.encoder = encoder  # BGE-M3 se carga solo al hacer la primera consulta.
        self._lock = RLock()
        self.vectors = vectors
        for vector in vectors:
            cosine(vectors[0], vector)
        marker = None
        if index_path is not None:
            index_path = Path(index_path)
            index_path.mkdir(parents=True, exist_ok=True)
            marker = index_path / "ready.txt"
            if not bundle_id:
                raise ValueError("El índice persistente requiere identidad del paquete.")
        try:
            self.qdrant = QdrantClient(path=str(index_path), force_disable_check_same_thread=True) if index_path else QdrantClient(":memory:", force_disable_check_same_thread=True)
        except RuntimeError as exc:
            raise RuntimeError(f"No se pudo abrir Qdrant en {index_path}. Cierra otra instancia que use ese índice y reintenta.") from exc
        self._finalizer = weakref.finalize(self, self.qdrant.close)
        try:
            if marker and marker.exists():
                if marker.read_text(encoding="utf-8").strip() != bundle_id:
                    raise ValueError("La identidad del índice no coincide con el paquete.")
                config = self.qdrant.get_collection("nikali").config.params.vectors
                records = self.qdrant.retrieve("nikali", ids=list(range(len(chunks))), with_payload=True)
                if (config.size != len(vectors[0]) or config.distance != Distance.COSINE
                        or self.qdrant.count("nikali").count != len(chunks)
                        or len(records) != len(chunks)
                        or any(r.payload.get("chunk_id") != chunks[int(r.id)].id for r in records)):
                    raise ValueError("Índice local incompleto o incompatible con el paquete.")
            else:
                # Si una importación se interrumpió, se repite desde los vectores
                # guardados. No hay una llamada al modelo de embeddings.
                if self.qdrant.collection_exists("nikali"):
                    self.qdrant.delete_collection("nikali")
                self.qdrant.create_collection(
                    collection_name="nikali",
                    vectors_config=VectorParams(size=len(vectors[0]), distance=Distance.COSINE),
                )
                self.qdrant.upsert(collection_name="nikali", points=[
                    PointStruct(id=i, vector=v, payload={"chunk_id": c.id, "source": c.source})
                    for i, (c, v) in enumerate(zip(chunks, vectors))
                ])
                if marker:
                    marker.write_text(bundle_id, encoding="utf-8")
        except Exception:
            self.close()
            raise

    def close(self):
        self._finalizer()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def search(self, question, k=TOP_K):
        if not question.strip() or k < 1:
            raise ValueError("Escribe una consulta y usa k >= 1.")
        with self._lock:
            if self.encoder is None:
                self.encoder = make_embedder(self.model)
            query = encode_texts(self.encoder, [question])[0]
            cosine(self.vectors[0], query)
            points = self.qdrant.query_points(
                collection_name="nikali", query=query, limit=k, with_payload=True,
            ).points
        return [Hit(self.chunks[int(point.id)], point.score) for point in points]


def evidence(hits):
    return "\n\n".join(
        f"[{h.chunk.id}] Fuente: {h.chunk.source}\n"
        + ("ATENCIÓN: fragmento parcial; no contiene la demostración completa.\n" if h.chunk.partial else "")
        + h.chunk.text for h in hits
    )
