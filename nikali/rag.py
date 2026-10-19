"""Un único pipeline de recuperación para todas las entradas del proyecto."""
import hashlib
import math
import re
import unicodedata
from dataclasses import dataclass
from threading import RLock

from nikali.config import EMBED_MODEL, ROOT, TOP_K, make_embedder


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
    fragment = ROOT / "output_marker/stewart_regla_cadena/fragmento_corregido.md"
    original = split_markdown(fragment.read_text(encoding="utf-8"), "stewart", str(fragment.relative_to(ROOT)))
    # El fragmento original termina al empezar la demostración. No se completa
    # silenciosamente ni se atribuyen al libro explicaciones añadidas.
    original = tuple(Chunk(c.id, c.text, c.source, c.section, "demostracion" in c.id) for c in original)
    notes = ROOT / "data/notas_didacticas.md"
    supplemental = split_markdown(notes.read_text(encoding="utf-8"), "notas", "Notas didácticas del prototipo (elaboración propia)")
    return original + supplemental


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


class Retriever:
    def __init__(self, chunks, model=EMBED_MODEL, *, encoder=None):
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct

        if not chunks:
            raise ValueError("La base de conocimiento está vacía.")
        self.chunks, self.model = tuple(chunks), model
        self.encoder = encoder if encoder is not None else make_embedder(model)
        self._lock = RLock()
        self.vectors = self._embed([c.text for c in self.chunks])
        for vector in self.vectors:
            cosine(self.vectors[0], vector)
        self.qdrant = QdrantClient(":memory:", force_disable_check_same_thread=True)
        self.qdrant.create_collection(
            collection_name="nikali",
            vectors_config=VectorParams(size=len(self.vectors[0]), distance=Distance.COSINE),
        )
        self.qdrant.upsert(collection_name="nikali", points=[
            PointStruct(id=i, vector=v, payload={"chunk_id": c.id, "source": c.source})
            for i, (c, v) in enumerate(zip(self.chunks, self.vectors))
        ])

    def _embed(self, texts):
        # Documentos y consultas usan la misma instancia de SentenceTransformer.
        vectors = self.encoder.encode(texts, show_progress_bar=False)
        vectors = [list(map(float, vector)) for vector in vectors]
        if len(vectors) != len(texts):
            raise ValueError("BGE-M3 no devolvió todos los embeddings solicitados.")
        return vectors

    def search(self, question, k=TOP_K):
        if not question.strip() or k < 1:
            raise ValueError("Escribe una consulta y usa k >= 1.")
        # Streamlit comparte este recurso entre reruns/hilos. Serializamos el
        # acceso al encoder y al cliente local; nunca modificamos el índice aquí.
        with self._lock:
            query = self._embed([question])[0]
            cosine(self.vectors[0], query)  # valida tamaño y valores antes de consultar
            points = self.qdrant.query_points(
                collection_name="nikali", query=query, limit=k,
                with_payload=True,
            ).points
        return [Hit(self.chunks[int(point.id)], point.score) for point in points]


def evidence(hits):
    return "\n\n".join(
        f"[{h.chunk.id}] Fuente: {h.chunk.source}\n"
        + ("ATENCIÓN: fragmento parcial; no contiene la demostración completa.\n" if h.chunk.partial else "")
        + h.chunk.text for h in hits
    )
