import json
import math
import ollama
import streamlit as st

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title="NIKaLi - Tutor ScaffoldLM",
    page_icon="🤖",
    layout="wide",
)

# ==========================================
# UTILIDADES RAG (puro Python + Ollama)
# ==========================================

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Similitud coseno entre dos vectores (sin numpy)."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _get_embedding(texto: str) -> list[float]:
    """Genera embedding usando Ollama (modelo nomic-embed-text)."""
    res = ollama.embeddings(model="nomic-embed-text", prompt=texto)
    return res["embedding"]


def _split_markdown(texto: str) -> list[str]:
    """Divide el markdown en chunks por encabezados (#, ##, ###)."""
    chunks, current = [], []
    for line in texto.splitlines():
        if line.startswith("#") and current:
            chunks.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        chunks.append("\n".join(current).strip())
    return [c for c in chunks if c]


@st.cache_resource
def cargar_rag():
    """Carga el documento, genera embeddings con Ollama y construye el índice en memoria.
    @st.cache_resource garantiza que se ejecuta una sola vez por sesión de servidor.
    """
    with open(
        "output_marker/stewart_regla_cadena/fragmento_corregido.md",
        "r",
        encoding="utf-8",
    ) as f:
        markdown_document = f.read()

    chunks = _split_markdown(markdown_document)

    # Generar embeddings para cada chunk con nomic-embed-text
    embeddings = []
    for chunk in chunks:
        emb = _get_embedding(chunk)
        embeddings.append(emb)

    return chunks, embeddings


def recuperar_chunk(chunks: list, embeddings: list, texto: str):
    """Busca el chunk más similar al texto usando similitud coseno."""
    query_emb = _get_embedding(texto)
    best_id, best_score = 0, -1.0
    for i, emb in enumerate(embeddings):
        score = _cosine_similarity(query_emb, emb)
        if score > best_score:
            best_score, best_id = score, i
    return best_id, chunks[best_id]


# ==========================================
# LÓGICA DEL TUTOR (ScaffoldLM)
# ==========================================
PROBLEMA_ACTUAL = "Encontrar la derivada de y = sin(x²) usando la regla de la cadena."
PASOS_RESOLUCION = [
    "Identificar la función externa f(u) y la función interna g(x).",
    "Derivar la función externa f(u) respecto a u.",
    "Derivar la función interna g(x) respecto a x, y multiplicar ambas derivadas.",
]


def evaluar_respuesta(paso_esperado: str, respuesta_alumno: str) -> str:
    prompt = (
        "Eres un evaluador estricto de matemáticas. "
        "Clasifica la respuesta usando UNA SOLA PALABRA: CORRECTO, INCORRECTO o PREGUNTA.\n"
        f"Paso: {paso_esperado}\n"
        f'Alumno: "{respuesta_alumno}"\n'
        "CLASIFICACIÓN:"
    )
    res = ollama.chat(
        model="qwen2.5:3b", messages=[{"role": "user", "content": prompt}]
    )
    diagnostico = res["message"]["content"].strip().upper()
    if "CORRECTO" in diagnostico and "INCORRECTO" not in diagnostico:
        return "CORRECTO"
    if "PREGUNTA" in diagnostico:
        return "PREGUNTA"
    return "INCORRECTO"


def generar_intervencion(
    paso_esperado: str,
    respuesta_alumno: str,
    tipo_intervencion: str,
    contexto: str = "",
) -> str:
    evidencia = (
        f"\nEVIDENCIA DEL LIBRO: {contexto}\n"
        "Usa esta teoría para fundamentar tu respuesta sin copiarla textualmente."
        if contexto
        else ""
    )
    if tipo_intervencion == "INCORRECTO":
        instruccion = (
            "El estudiante se equivocó. Dale una pista breve. "
            "REGLA: NUNCA le des la respuesta directa."
        )
    else:
        instruccion = (
            "El estudiante tiene una duda. Explica el concepto usando la "
            "EVIDENCIA DEL LIBRO y anímalo a intentar el paso actual."
        )
    prompt = (
        "Eres NIK, el tutor amigable de la plataforma NIKaLi. Eres experto en cálculo diferencial.\n"
        f"{instruccion}{evidencia}\n"
        f"Paso actual: {paso_esperado}\n"
        f'Lo que dijo el estudiante: "{respuesta_alumno}"\n'
        "Respuesta de NIK:"
    )
    res = ollama.chat(
        model="qwen2.5:3b", messages=[{"role": "user", "content": prompt}]
    )
    return res["message"]["content"]


# ==========================================
# TÍTULO PRINCIPAL
# ==========================================
st.title("🤖 NIKaLi - Tutor ScaffoldLM")

# ==========================================
# SELECTOR DE DINÁMICA
# ==========================================
dinamica = st.radio(
    "Selecciona la dinámica de aprendizaje:",
    options=["Modo Exploración Libre (RAG)", "Modo Ejercicio Guiado"],
    horizontal=True,
)

st.divider()

# ==========================================
# ESTADO DE LA SESIÓN
# ==========================================
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

if "paso_actual" not in st.session_state:
    st.session_state.paso_actual = 0

if "debug_info" not in st.session_state:
    st.session_state.debug_info = {
        "estado": None,
        "chunk_id": None,
        "texto_recuperado": None,
    }

# ==========================================
# CARGAR RECURSOS (una sola vez)
# ==========================================
with st.spinner("🔧 Cargando base de conocimiento con Ollama…"):
    chunks, embeddings = cargar_rag()

# ==========================================
# SIDEBAR: DEBUG & MÉTRICAS RAG
# ==========================================
with st.sidebar:
    st.header("⚙️ Debug & Métricas RAG")

    st.subheader("📄 Chunk Recuperado")
    debug = st.session_state.debug_info
    if debug["chunk_id"] is not None:
        st.caption(f"**ID del chunk:** `{debug['chunk_id']}`")
        st.text_area(
            label="Texto del chunk",
            value=debug["texto_recuperado"] or "",
            height=200,
            disabled=True,
            key="sidebar_chunk_text",
        )
    else:
        st.info("Aquí aparecerá el fragmento recuperado.")

    st.subheader("🔍 Diagnóstico del Evaluador")
    if debug["estado"] is not None:
        color_map = {"CORRECTO": "🟢", "INCORRECTO": "🔴", "PREGUNTA": "🟡"}
        icono = color_map.get(debug["estado"], "⚪")
        st.markdown(f"### {icono} `{debug['estado']}`")
    else:
        st.info("Aquí aparecerá el estado del evaluador.")

# ==========================================
# HISTORIAL DEL CHAT
# ==========================================
for mensaje in st.session_state.mensajes:
    with st.chat_message(mensaje["role"]):
        st.markdown(mensaje["content"])

# ==========================================
# MODO EXPLORACIÓN LIBRE (RAG)
# ==========================================
if dinamica == "Modo Exploración Libre (RAG)":

    if not st.session_state.mensajes:
        with st.chat_message("assistant"):
            bienvenida = (
                "👋 ¡Hola! Soy **NIK**, tu tutor en NIKaLi. En este modo puedes preguntarme "
                "cualquier cosa sobre la regla de la cadena y buscaré en el libro "
                "el fragmento más relevante para responderte."
            )
            st.markdown(bienvenida)
            st.session_state.mensajes.append(
                {"role": "assistant", "content": bienvenida}
            )

    if prompt := st.chat_input("Escribe tu pregunta…"):
        st.session_state.mensajes.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        chunk_id, texto_chunk = recuperar_chunk(chunks, embeddings, prompt)
        st.session_state.debug_info.update(
            {"estado": None, "chunk_id": chunk_id, "texto_recuperado": texto_chunk}
        )

        system_prompt = (
            "Eres NIK, el tutor amigable de la plataforma NIKaLi. Eres experto en cálculo diferencial. "
            "Responde de forma clara y didáctica basándote en la siguiente "
            f"EVIDENCIA DEL LIBRO:\n\n{texto_chunk}\n\n"
            "No copies el texto literalmente; explica con tus propias palabras."
        )
        with st.chat_message("assistant"):
            with st.spinner("🤖 NIK está pensando…"):
                res = ollama.chat(
                    model="qwen2.5:3b",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                )
                respuesta = res["message"]["content"]
            st.markdown(respuesta)

        st.session_state.mensajes.append({"role": "assistant", "content": respuesta})
        st.rerun()

# ==========================================
# MODO EJERCICIO GUIADO (ScaffoldLM)
# ==========================================
else:
    paso = st.session_state.paso_actual
    total_pasos = len(PASOS_RESOLUCION)

    st.progress(
        paso / total_pasos,
        text=f"Paso {paso + 1} de {total_pasos}" if paso < total_pasos else "✅ ¡Ejercicio completado!",
    )

    if paso < total_pasos:
        if not st.session_state.mensajes:
            intro = (
                f"🎯 **Problema:** {PROBLEMA_ACTUAL}\n\n"
                f"📍 **Paso 1:** {PASOS_RESOLUCION[0]}"
            )
            with st.chat_message("assistant"):
                st.markdown(intro)
            st.session_state.mensajes.append({"role": "assistant", "content": intro})

        if prompt := st.chat_input("Tu respuesta…"):
            paso_esperado = PASOS_RESOLUCION[paso]

            st.session_state.mensajes.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.spinner("Evaluando…"):
                estado = evaluar_respuesta(paso_esperado, prompt)

            chunk_id, texto_chunk = None, ""
            if estado == "PREGUNTA":
                chunk_id, texto_chunk = recuperar_chunk(chunks, embeddings, prompt)

            st.session_state.debug_info.update(
                {"estado": estado, "chunk_id": chunk_id, "texto_recuperado": texto_chunk}
            )

            if estado == "CORRECTO":
                st.session_state.paso_actual += 1
                nuevo_paso = st.session_state.paso_actual
                if nuevo_paso < total_pasos:
                    respuesta_tutor = (
                        f"✅ ¡Exacto! Muy bien.\n\n"
                        f"📍 **Siguiente paso ({nuevo_paso + 1}/{total_pasos}):** "
                        f"{PASOS_RESOLUCION[nuevo_paso]}"
                    )
                else:
                    respuesta_tutor = (
                        "🏆 ¡Excelente trabajo! Completaste todos los pasos "
                        "de la regla de la cadena. ¡Eres un crack!"
                    )
            else:
                with st.spinner("🤖 NIK está preparando una pista…"):
                    respuesta_tutor = generar_intervencion(
                        paso_esperado, prompt, estado, texto_chunk
                    )

            with st.chat_message("assistant"):
                st.markdown(respuesta_tutor)
            st.session_state.mensajes.append(
                {"role": "assistant", "content": respuesta_tutor}
            )
            st.rerun()

    else:
        st.success("🎉 ¡Completaste el ejercicio! Puedes reiniciarlo abajo.")
        if st.button("🔄 Reiniciar ejercicio"):
            st.session_state.mensajes = []
            st.session_state.paso_actual = 0
            st.session_state.debug_info = {
                "estado": None, "chunk_id": None, "texto_recuperado": None
            }
            st.rerun()
