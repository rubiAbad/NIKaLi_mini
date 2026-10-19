from langchain_text_splitters import MarkdownHeaderTextSplitter
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# 1. Cargar el Markdown de prueba (usa el nombre del archivo que tengas creado)
nombre_archivo = "output_marker/stewart_regla_cadena/fragmento_corregido.md"

with open(nombre_archivo, "r", encoding="utf-8") as f:
    markdown_document = f.read()

# 2. Realizar el Chunking por encabezados
headers_to_split_on = [
    ("#", "Capitulo_Seccion"),
    ("##", "Subseccion"),
    ("###", "Tema"),
]
markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers_to_split_on, 
    strip_headers=False
)
chunks = markdown_splitter.split_text(markdown_document)

# 3. Cargar el modelo BAAI/bge-m3
print("🔄 Cargando el modelo BAAI/bge-m3...")
embedding_model = SentenceTransformer("BAAI/bge-m3")

# Generar embeddings de los chunks
texts = [c.page_content for c in chunks]
embeddings = embedding_model.encode(texts)
vector_size = embeddings.shape[1]

# 4. Configurar Qdrant Local (en memoria)
print("📦 Inicializando Qdrant Local...")
qdrant_client = QdrantClient(":memory:")
collection_name = "stewart_calculo"

qdrant_client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
)

# 5. Insertar Chunks + Vectores + Metadatos
points = [
    PointStruct(
        id=idx,
        vector=vector.tolist(),
        payload={"text": chunk.page_content, **chunk.metadata}
    )
    for idx, (chunk, vector) in enumerate(zip(chunks, embeddings))
]

qdrant_client.upsert(collection_name=collection_name, points=points)
print(f"✅ ¡{len(points)} chunks indexados en Qdrant exitosamente!\n")

# 6. PRUEBA DE RETRIEVAL
pregunta_usuario = "¿Qué es la regla de la cadena y cuál es su fórmula en notación de Leibniz?"
print(f"🔍 Pregunta: '{pregunta_usuario}'\n")

query_vector = embedding_model.encode([pregunta_usuario])[0].tolist()

search_results = qdrant_client.query_points(
    collection_name=collection_name,
    query=query_vector,
    limit=1
).points

print("=== CHUNK RECUPERADO DE QDRANT ===")
for res in search_results:
    print(f"🎯 Score de similitud: {res.score:.4f}")
    print(f"📌 Metadatos: {res.payload.get('Capitulo_Seccion', '')}")
    print(f"📄 Texto recuperado:\n{res.payload['text']}\n")
