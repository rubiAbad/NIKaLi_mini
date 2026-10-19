"""Interfaz local: streamlit run app.py."""
import streamlit as st
from nikali.config import CHAT_MODEL, EMBED_MODEL, OLLAMA_HOST, TOP_K, make_client
from nikali.rag import Retriever, load_chunks
from nikali.tutor import PROBLEM, STEPS, free_turn, guided_turn, new_session

st.set_page_config(page_title="NIKaLi · Aprende paso a paso", page_icon="🌱", layout="wide")


@st.cache_resource(show_spinner=False)
def load_resources(chunks, model, host):
    # Los argumentos forman la clave de caché: cambiar texto, modelo o servidor
    # reconstruye el índice. El índice es de solo lectura; Retriever protege el acceso concurrente.
    client = make_client()
    return client, Retriever(chunks, model)


def show_hits(hits):
    for hit in hits:
        st.caption(f"{hit.chunk.id} · Similitud: {hit.score:.3f}")
        st.caption(hit.chunk.source)
        if hit.chunk.partial:
            st.warning("Fragmento parcial: no incluye la demostración completa.")
        st.markdown(hit.chunk.text)


st.title("🌱 NIKaLi")
st.caption("Entiende la idea. Intenta un paso. Construye tu solución.")
for name in ("guided", "free"):
    if name not in st.session_state:
        st.session_state[name] = new_session()

with st.sidebar:
    st.header("Tu espacio de práctica")
    mode = st.radio("¿Cómo quieres aprender?", ["Ejercicio guiado", "Explorar conceptos"], key="mode")
    key = "guided" if mode == "Ejercicio guiado" else "free"
    if st.button("Reiniciar ejercicio" if key == "guided" else "Borrar conversación", key="reset"):
        st.session_state[key] = new_session()
        st.session_state.pop(f"pending_{key}", None)
        st.rerun()
    st.caption("Cada modo conserva su propia conversación. Reiniciar afecta solo al modo seleccionado.")
    debug_enabled = st.checkbox("Ver diagnóstico técnico (puede mostrar soluciones)", value=False)
    st.divider()
    st.caption("Prototipo local de tutoría. La evaluación automática puede equivocarse.")
    st.caption("El material incluye un fragmento de Stewart y notas didácticas propias.")

session = st.session_state[key]
if key == "guided":
    with st.container(border=True):
        st.subheader("Regla de la cadena")
        st.write(PROBLEM)
        st.latex(r"y=\sin(x^2)")
        complete = session["step"] == len(STEPS)
        st.progress(session["step"] / len(STEPS), text="Ejercicio completado" if complete else f"Paso {session['step'] + 1} de {len(STEPS)}")
        if not complete:
            st.markdown(f"**Tu tarea:** {STEPS[session['step']].instruction}")
        else:
            st.success("Terminaste. Puedes volver a practicar con «Reiniciar ejercicio».")
else:
    st.subheader("Explora una idea")
    st.write("Pregunta por la regla de la cadena, los ejemplos, el producto o el cociente.")
    st.caption("La demostración completa todavía no está incluida en el material.")

try:
    chunks = load_chunks()
    with st.spinner("Preparando el material de estudio…"):
        client, retriever = load_resources(chunks, EMBED_MODEL, OLLAMA_HOST)
except Exception:
    st.error("No pude preparar el material. Comprueba las dependencias, los archivos del proyecto y la disponibilidad de BGE-M3 en la caché de Hugging Face o la conexión para descargarlo.")
    st.code("python -m pip install -r requirements.txt", language="bash")
    st.caption("BGE-M3 se carga con Sentence Transformers. Ollama se usa únicamente para las respuestas de Qwen.")
    st.stop()

if not session["messages"]:
    st.info("Escribe tu intento o pide una pista. El paso se mantiene hasta que tu respuesta esté completa." if key == "guided" else "¿Qué te gustaría entender? Puedes hacer preguntas de seguimiento.")
for message in session["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("hits"):
            with st.expander("Material consultado"):
                show_hits(message["hits"])

if debug_enabled:
    with st.sidebar:
        st.caption(f"Generación: {CHAT_MODEL} · Embeddings: {EMBED_MODEL} · top-k: {TOP_K}")
        st.caption(f"{len(chunks)} chunks en el índice")
        if session["debug"].get("verdict"):
            st.json(session["debug"]["verdict"])
        show_hits(session["debug"].get("hits", []))

pending_key = f"pending_{key}"
question = None
if pending_key in st.session_state:
    st.warning("El último turno no se completó. Tu progreso y conversación se conservaron.")
    st.write(st.session_state[pending_key])
    retry, discard = st.columns(2)
    if retry.button("Reintentar", key="retry"):
        question = st.session_state[pending_key]
    if discard.button("Descartar intento", key="discard"):
        del st.session_state[pending_key]
        st.rerun()
else:
    question = st.chat_input("Tu respuesta o pregunta…", key=f"input_{key}",
                             disabled=key == "guided" and session["step"] == len(STEPS))
if question:
    try:
        with st.spinner("NIK está revisando tu mensaje…"):
            handler = guided_turn if key == "guided" else free_turn
            updated = handler(client, retriever, session, question)
    except Exception:
        st.session_state[pending_key] = question
        st.error("No se pudo completar el turno. Revisa la conexión con Ollama y reintenta.")
        st.rerun()
    else:
        st.session_state[key] = updated
        st.session_state.pop(pending_key, None)
        st.rerun()
