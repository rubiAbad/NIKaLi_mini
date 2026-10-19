import ollama
from langchain_text_splitters import MarkdownHeaderTextSplitter
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# 1. Cargar el Markdown de prueba
nombre_archivo = "output_marker/stewart_regla_cadena/fragmento_corregido.md"
with open(nombre_archivo, "r", encoding="utf-8") as f:
    markdown_document = f.read()

# 2. Chunking por encabezados
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

# 3. Generar Embeddings con BAAI/bge-m3
print("🔄 Cargando BAAI/bge-m3 e indexando...")
embedding_model = SentenceTransformer("BAAI/bge-m3")
texts = [c.page_content for c in chunks]
embeddings = embedding_model.encode(texts)
vector_size = embeddings.shape[1]

# 4. Inicializar Qdrant en Memoria
qdrant_client = QdrantClient(":memory:")
collection_name = "stewart_calculo"
qdrant_client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
)

# 5. Insertar puntos en Qdrant
points = [
    PointStruct(
        id=idx,
        vector=vector.tolist(),
        payload={"text": chunk.page_content, **chunk.metadata}
    )
    for idx, (chunk, vector) in enumerate(zip(chunks, embeddings))
]
qdrant_client.upsert(collection_name=collection_name, points=points)

# 6. Retrieval (Búsqueda semántica)
pregunta_usuario = "¿Qué es la regla de la cadena y cuál es su fórmula en notación de Leibniz?"
query_vector = embedding_model.encode([pregunta_usuario])[0].tolist()

search_results = qdrant_client.query_points(
    collection_name=collection_name,
    query=query_vector,
    limit=1
).points

chunk_recuperado = search_results[0].payload['text']

# =======================================================
# 7. EXPERIMENTO DE GENERACIÓN CON QWEN 2.5 3B (OLLAMA)
# =======================================================

print("\n" + "="*70)
print(f"❓ PREGUNTA DEL ESTUDIANTE:\n'{pregunta_usuario}'")
print("="*70 + "\n")

# --- CASO A: SIN RETRIEVAL ---
print("🤖 1. RESPUESTA SIN RETRIEVAL (Conocimiento general de Qwen 3B):\n")
res_sin_rag = ollama.chat(
    model='qwen2.5:3b',
    messages=[{'role': 'user', 'content': pregunta_usuario}]
)
print(res_sin_rag['message']['content'])

print("\n" + "-"*70 + "\n")

# --- CASO B: CON RETRIEVAL (RAG) ---
prompt_con_rag = f"""Eres un tutor experto en cálculo diferencial. Responde la duda del estudiante utilizando ÚNICAMENTE la siguiente información del libro de texto. Mantén la notación exacta indicada.

[CONTEXTO RECUPERADO DEL LIBRO]:
{chunk_recuperado}

[PREGUNTA DEL ESTUDIANTE]:
{pregunta_usuario}

[RESPUESTA]:"""

print("🎯 2. RESPUESTA CON RETRIEVAL (Fundamentada en el chunk de Qdrant):\n")
res_con_rag = ollama.chat(
    model='qwen2.5:3b',
    messages=[{'role': 'user', 'content': prompt_con_rag}]
)
print(res_con_rag['message']['content'])
print("\n" + "="*70)
