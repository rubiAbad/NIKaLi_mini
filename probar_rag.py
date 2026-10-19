import argparse
from nikali.config import TOP_K, make_client
from nikali.rag import Retriever, load_chunks

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pregunta", nargs="?", default="¿Cuál es la regla de la cadena en notación de Leibniz?")
    parser.add_argument("--k", type=int, default=TOP_K)
    args = parser.parse_args()
    retriever = Retriever(make_client(), load_chunks())
    for hit in retriever.search(args.pregunta, args.k):
        print(f"\n{hit.chunk.id} · {hit.score:.4f}\n{hit.chunk.source}\n{hit.chunk.text}")
