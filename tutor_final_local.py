import ollama
from langchain_text_splitters import MarkdownHeaderTextSplitter
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# ==========================================
# 1. INICIALIZAR RAG (Base Vectorial)
# ==========================================
print("Cargando modelo de embeddings y Qdrant...")
embedding_model = SentenceTransformer("BAAI/bge-m3")

# Cargamos el documento real que ya tienes
with open("output_marker/stewart_regla_cadena/fragmento_corregido.md", "r", encoding="utf-8") as f:
    markdown_document = f.read()

markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("#", "C"), ("##", "S"), ("###", "T")], strip_headers=False
)
chunks = markdown_splitter.split_text(markdown_document)
embeddings = embedding_model.encode([c.page_content for c in chunks])

qdrant = QdrantClient(":memory:")
qdrant.create_collection(
    collection_name="stewart",
    vectors_config=VectorParams(size=embeddings.shape[1], distance=Distance.COSINE),
)
qdrant.upsert(
    collection_name="stewart", 
    points=[PointStruct(id=i, vector=v.tolist(), payload={"text": c.page_content}) for i, (c, v) in enumerate(zip(chunks, embeddings))]
)

# ==========================================
# 2. LÓGICA DEL TUTOR (ScaffoldLM Lite)
# ==========================================
problema_actual = "Encontrar la derivada de y = sin(x^2) usando la regla de la cadena."
pasos_resolucion = [
    "Identificar la función externa f(u) y la función interna g(x).",
    "Derivar la función externa f(u) respecto a u.",
    "Derivar la función interna g(x) respecto a x, y multiplicar ambas derivadas."
]

def evaluar_respuesta(paso_esperado, respuesta_alumno):
    prompt = f"""Eres un evaluador estricto de matemáticas. Clasifica la respuesta usando UNA SOLA PALABRA: CORRECTO, INCORRECTO o PREGUNTA.
Paso: {paso_esperado}
Alumno: "{respuesta_alumno}"
CLASIFICACIÓN:"""
    res = ollama.chat(model='qwen2.5:3b', messages=[{'role': 'user', 'content': prompt}])
    diagnostico = res['message']['content'].strip().upper()
    
    if "CORRECTO" in diagnostico and "INCORRECTO" not in diagnostico: return "CORRECTO"
    if "PREGUNTA" in diagnostico: return "PREGUNTA"
    return "INCORRECTO"

def generar_intervencion(paso_esperado, respuesta_alumno, tipo_intervencion, contexto=""):
    # Inyectamos el contexto de Qdrant si existe
    evidencia = f"\nEVIDENCIA DEL LIBRO: {contexto}\nUsa esta teoría para fundamentar tu respuesta sin copiarla textualmente." if contexto else ""
    
    if tipo_intervencion == "INCORRECTO":
        instruccion = "El estudiante se equivocó. Dale una pista breve. REGLA: NUNCA le des la respuesta directa."
    else:
        instruccion = "El estudiante tiene una duda. Explica el concepto usando la EVIDENCIA DEL LIBRO y anímalo a intentar el paso actual."

    prompt = f"""Eres NIKaLi, un tutor de cálculo.
{instruccion}{evidencia}
Paso actual: {paso_esperado}
Lo que dijo el estudiante: "{respuesta_alumno}"
Respuesta del tutor:"""

    res = ollama.chat(model='qwen2.5:3b', messages=[{'role': 'user', 'content': prompt}])
    return res['message']['content']

# ==========================================
# 3. CICLO DE LA SESIÓN
# ==========================================
paso_actual = 0
print("\n" + "="*60)
print(f"🤖 NIKaLi: Vamos a resolver esto juntos: {problema_actual}")
print(f"📍 Primer paso: {pasos_resolucion[paso_actual]}")
print("="*60)

while paso_actual < len(pasos_resolucion):
    respuesta = input("\n🧑‍🎓 Tú: ")
    if respuesta.lower() in ['salir', 'exit', 'quit']: break

    estado = evaluar_respuesta(pasos_resolucion[paso_actual], respuesta)
    print(f"   [Debug] Estado: {estado}")

    if estado == "CORRECTO":
        paso_actual += 1
        if paso_actual < len(pasos_resolucion):
            print(f"\n🤖 NIKaLi: ¡Exacto! Siguiente paso: {pasos_resolucion[paso_actual]}")
        else:
            print("\n🤖 NIKaLi: ¡Excelente trabajo! Terminamos el problema.")
    else:
        # ¡LA MAGIA DEL RAG SUCEDE AQUÍ!
        contexto_recuperado = ""
        if estado == "PREGUNTA":
            vector_pregunta = embedding_model.encode([respuesta])[0].tolist()
            resultados = qdrant.query_points(collection_name="stewart", query=vector_pregunta, limit=1).points
            contexto_recuperado = resultados[0].payload["text"] if resultados else ""
            print(f"   [Debug] Chunk recuperado de Qdrant: ID {resultados[0].id}")

        pista = generar_intervencion(pasos_resolucion[paso_actual], respuesta, estado, contexto_recuperado)
        print(f"\n🤖 NIKaLi: {pista}")
