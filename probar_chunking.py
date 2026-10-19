from langchain_text_splitters import MarkdownHeaderTextSplitter

# 1. Leer el archivo Markdown de prueba
nombre_archivo = "output_marker/stewart_regla_cadena/fragmento_corregido.md"

with open(nombre_archivo, "r", encoding="utf-8") as f:
    markdown_document = f.read()

# 2. Definir las reglas de división según la jerarquía del libro
headers_to_split_on = [
    ("#", "Capitulo_Seccion"),
    ("##", "Subseccion"),
    ("###", "Tema"),
]

# 3. Inicializar el splitter estructurado
markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers_to_split_on,
    strip_headers=False  # Mantiene los títulos dentro del texto del chunk
)

# 4. Generar los chunks
chunks = markdown_splitter.split_text(markdown_document)

# 5. Imprimir el resultado de la división
print(f"=== TOTAL DE CHUNKS GENERADOS: {len(chunks)} ===\n")

for i, chunk in enumerate(chunks, 1):
    print(f"------------------- CHUNK {i} -------------------")
    print(f"📌 Metadatos (Sección): {chunk.metadata}")
    print(f"📄 Contenido:\n{chunk.page_content}\n")
