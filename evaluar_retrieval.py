"""Evaluación del MISMO retrieval utilizado en app.py. Usa BGE-M3 local; no requiere Ollama."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from golden_dataset import GOLDEN_DATASET, UNANSWERABLE_CASES
from nikali.config import EMBED_MODEL, TOP_K
from nikali.rag import Retriever, corpus_digest, load_chunks


def metrics(retrieved, relevant, k):
    if k < 1 or not relevant:
        raise ValueError("Las métricas requieren k >= 1 y al menos un chunk relevante.")
    # No contar IDs duplicados como aciertos adicionales.
    ranked = list(dict.fromkeys(retrieved))[:k]
    relevant = set(relevant)
    hits = len(set(ranked) & relevant)
    first = next((i for i, item in enumerate(ranked, 1) if item in relevant), None)
    return {"hit_rate": float(hits > 0), "precision": hits / k,
            "recall": hits / len(relevant), "mrr": 1 / first if first else 0.0}


def evaluate(retriever, dataset, k):
    if not dataset or not 1 <= k <= len(retriever.chunks):
        raise ValueError("Dataset vacío o k fuera del tamaño del corpus.")
    available = {c.id for c in retriever.chunks}
    for item in dataset:
        if not item["ids_relevantes"] or not set(item["ids_relevantes"]) <= available:
            raise ValueError(f"Etiquetas inválidas en {item['id_pregunta']}.")
    rows = []
    for item in dataset:
        hits = retriever.search(item["pregunta"], k=k)
        ids = [h.chunk.id for h in hits]
        rows.append({**item, "ids_recuperados": ids, "scores": [h.score for h in hits],
                     **metrics(ids, item["ids_relevantes"], k)})
    aggregate = {name: sum(r[name] for r in rows) / len(rows)
                 for name in ("hit_rate", "precision", "recall", "mrr")}
    return {"k": k, "n_preguntas": len(rows), "metricas": aggregate, "detalle": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, nargs="+", default=[TOP_K, 2])
    parser.add_argument("--output", type=Path, help="Guardar informe JSON, por ejemplo results/retrieval.json")
    args = parser.parse_args()
    chunks = load_chunks()
    if any(k < 1 or k > len(chunks) for k in args.k):
        parser.error(f"k debe estar entre 1 y {len(chunks)}")
    retriever = Retriever(chunks)
    report = {"fecha_utc": datetime.now(timezone.utc).isoformat(), "embedding_model": EMBED_MODEL,
              "corpus_sha256": corpus_digest(chunks), "chunk_ids": [c.id for c in chunks],
              "top_k_web": TOP_K, "nota": "Conjunto de desarrollo pequeño; no demuestra generalización.",
              "resultados": [evaluate(retriever, GOLDEN_DATASET, k) for k in args.k]}
    # Recuperar siempre un vecino NO prueba que exista una respuesta. Estos casos
    # requieren revisión de la abstención del generador, no un recall ficticio.
    report["sin_respuesta_revision_manual"] = [
        {**item, "ids_recuperados": [h.chunk.id for h in retriever.search(item["pregunta"])],
         "nota": "Inspeccionar en Exploración: debería reconocer falta de evidencia."}
        for item in UNANSWERABLE_CASES
    ]
    for run in report["resultados"]:
        print(f"\nTop {run['k']} · {run['n_preguntas']} preguntas")
        for name, value in run["metricas"].items():
            print(f"  {name}: {value:.3f}")
    print("\nAdvertencia: benchmark de desarrollo, 6 chunks y 16 preguntas; validar etiquetas con una persona.")
    print("Los 3 casos sin respuesta se revisan aparte; no están incluidos en las métricas anteriores.")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Informe: {args.output}")


if __name__ == "__main__":
    main()
