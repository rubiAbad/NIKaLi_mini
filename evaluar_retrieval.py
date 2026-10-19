from langchain_text_splitters import MarkdownHeaderTextSplitter
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# 1. Preparar la Base Vectorial (Repetimos el proceso rápido)
with open("output_marker/stewart_regla_cadena/fragmento_corregido.md", "r", encoding="utf-8") as f:
    markdown_document = f.read()

markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("#", "C"), ("##", "S"), ("###", "T")], 
    strip_headers=False
)
chunks = markdown_splitter.split_text(markdown_document)

embedding_model = SentenceTransformer("BAAI/bge-m3")
embeddings = embedding_model.encode([c.page_content for c in chunks])

qdrant_client = QdrantClient(":memory:")
qdrant_client.create_collection(
    collection_name="stewart",
    vectors_config=VectorParams(size=embeddings.shape[1], distance=Distance.COSINE),
)

# Insertar asignando un ID numérico (Chunk 0 y Chunk 1)
qdrant_client.upsert(
    collection_name="stewart", 
    points=[PointStruct(id=i, vector=v.tolist(), payload={"text": c.page_content}) for i, (c, v) in enumerate(zip(chunks, embeddings))]
)

# =======================================================
# 2. CAPA DE EVALUACIÓN (GOLDEN DATASET)
# =======================================================
# Definimos preguntas y el ID del chunk que DEBERÍA responderlas.
# Chunk 0 = Teoría y fórmula Leibniz. Chunk 1 = Demostración con Deltas.

golden_dataset = [
    {"pregunta": "¿Cuál es la fórmula de la regla de la cadena en notación de Leibniz?", "id_esperado": 0},
    {"pregunta": "¿Cómo se demuestra usando el cambio en Delta u y Delta x?", "id_esperado": 1},
    {"pregunta": "Si u cambia al doble de rapidez que x, ¿qué pasa con y?", "id_esperado": 0}
]

def evaluar_metricas(k, dataset):
    total_preguntas = len(dataset)
    hits = 0
    suma_precision = 0
    suma_recall = 0

    print(f"\n--- EVALUANDO EN TOP K={k} ---")
    
    for item in dataset:
        # Vectorizar pregunta y buscar en Qdrant
        query_vector = embedding_model.encode([item["pregunta"]])[0].tolist()
        resultados = qdrant_client.query_points(
            collection_name="stewart", 
            query=query_vector, 
            limit=k
        ).points
        
        # Obtener los IDs de los chunks recuperados
        ids_recuperados = [res.id for res in resultados]
        id_correcto = item["id_esperado"]
        
        # Calcular si fue un Hit (Acierto)
        if id_correcto in ids_recuperados:
            hits += 1
            # Precision: (Chunks relevantes recuperados) / (Total de chunks recuperados)
            suma_precision += 1 / k
            # Recall: (Chunks relevantes recuperados) / (Total de chunks relevantes que existen) -> (1/1)
            suma_recall += 1 / 1
            print(f"✅ ¡Acierto! La pregunta '{item['pregunta'][:30]}...' recuperó el ID {id_correcto}.")
        else:
            print(f"❌ Fallo. La pregunta '{item['pregunta'][:30]}...' NO trajo el ID {id_correcto}.")

    # Promediar métricas
    hit_rate = (hits / total_preguntas) * 100
    precision = (suma_precision / total_preguntas) * 100
    recall = (suma_recall / total_preguntas) * 100

    print(f"\n📊 RESULTADOS (K={k}):")
    print(f"   Hit Rate@{k}:  {hit_rate:.1f}%")
    print(f"   Precision@{k}: {precision:.1f}%")
    print(f"   Recall@{k}:    {recall:.1f}%")

# 3. Ejecutar Evaluación para K=1 y K=2
evaluar_metricas(k=1, dataset=golden_dataset)
evaluar_metricas(k=2, dataset=golden_dataset)
