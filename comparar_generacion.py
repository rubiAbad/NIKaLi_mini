"""Comparación ilustrativa, no evaluación de calidad automática."""
from nikali.config import make_client
from nikali.index import open_retriever
from nikali.tutor import chat, free_turn, new_session

if __name__ == "__main__":
    question = "¿Cuál es la fórmula de la regla de la cadena en notación de Leibniz?"
    client = make_client()
    retriever = open_retriever()
    print("SIN RAG:\n", chat(client, [{"role": "user", "content": question}]))
    result = free_turn(client, retriever, new_session(), question)
    print("\nCON RAG (mismo flujo que la web):\n", result["messages"][-1]["content"])
    print("Fuentes:", [h.chunk.id for h in result["debug"]["hits"]])
