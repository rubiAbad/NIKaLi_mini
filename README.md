# Mini NIKaLi

Prototipo local para aprender el flujo de un tutor de cálculo: material preparado → recuperación → respuesta, con un ejercicio guiado de regla de la cadena. Web, consola y evaluaciones comparten la misma lógica.

| Componente | Configuración de esta versión |
| --- | --- |
| Evaluador y tutor | `qwen2.5:3b` mediante Ollama |
| Embeddings | `BAAI/bge-m3` mediante Sentence Transformers |
| Búsqueda | Qdrant local persistente, `TOP_K=1` |
| Interfaz | Streamlit |
| Material compartido | `data/rag_preparado.json`: chunks y embeddings del fragmento de Stewart |

No requiere claves de API, servicios de pago, Docker ni un servidor Qdrant. No es una implementación validada de ScaffoldLM ni un evaluador infalible.

## Actualizar una instalación existente

Detén Streamlit con **Ctrl+C**. Dentro del repositorio:

```bash
git status --short --branch
git fetch origin
git switch main
git pull --ff-only origin main
```

Si Git muestra archivos modificados o un conflicto, conserva esos cambios y revisa el mensaje antes de continuar. No uses `reset --hard`. La rama `fix/tutor-rag-web` también contiene la corrección; puedes actualizarla con `git pull --ff-only origin fix/tutor-rag-web` estando en esa rama.

Usa **un entorno exclusivo para la mini**, separado del de Marker/Surya: sus dependencias de Transformers pueden ser incompatibles. Si todavía no creaste `.venv-mini`, ejecuta `python -m venv .venv-mini` (o `python3` en Mac). Actívalo con `source .venv-mini/bin/activate` en Mac o `.\.venv-mini\Scripts\Activate.ps1` en PowerShell. Después:

```bash
python -m pip install -r requirements.txt
python verificar_entorno.py
python -m streamlit run app.py
```

## Primera instalación en otra computadora

Necesitas acceso al repositorio privado, Git, **Python 3.11 o 3.12 de 64 bits** y [Ollama](https://ollama.com/download). Usa un entorno propio en cada computadora; no copies `venv` de otra persona. La velocidad y la memoria necesarias dependen del equipo. La instalación completa todavía debe verificarse en los Windows y Mac del equipo.

```bash
git clone https://github.com/rubiAbad/NIKaLi_mini.git
cd NIKaLi_mini
```

**macOS (Terminal):**

```bash
python3 -m venv .venv-mini
source .venv-mini/bin/activate
```

**Windows (PowerShell):**

```powershell
py -3.11 -m venv .venv-mini
.\.venv-mini\Scripts\Activate.ps1
```

Si instalaste Python 3.12, usa `py -3.12`. Si PowerShell impide activar el entorno, puedes ejecutar directamente `.\.venv-mini\Scripts\python.exe` en lugar de `python` en los comandos siguientes, sin cambiar las políticas del sistema. En CMD la activación es `.venv-mini\Scripts\activate.bat`.

**Ambos sistemas, con el entorno activado:**

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
ollama pull qwen2.5:3b
python verificar_entorno.py
python verificar_entorno.py --modelos
python -m streamlit run app.py
```

Mantén Ollama abierto; si no está ejecutándose, abre otra terminal y usa `ollama serve`. Si ya tienes Qwen descargado, no hace falta repetir su descarga. Abre [http://localhost:8501](http://localhost:8501) y deja abierta la terminal de Streamlit. Para detenerlo, presiona **Ctrl+C**.

El repositorio ya incluye **los chunks y los embeddings reales del libro** en `data/rag_preparado.json`. Tus compañeras no deben ejecutar Marker, preparar Markdown, hacer chunking ni recalcular esos embeddings. Al abrir la web se valida el paquete y se carga Qdrant. En cada equipo, la primera apertura importa los vectores guardados a `.nikali_index/`; las siguientes reutilizan esa base en disco.

**BGE-M3 sigue siendo necesario para las preguntas.** Se carga al hacer la primera consulta que requiera retrieval o al usar `--modelos`. Reutiliza la caché de Hugging Face; si falta esa revisión del modelo, necesita descargar los pesos. No se descarga a través de Ollama y no va incluido en el JSON. El diagnóstico y Streamlit son procesos distintos: cargan por separado el modelo en RAM, pero reutilizan los pesos descargados.

## Diagnóstico

- `python verificar_entorno.py`: comprueba Python, importación de dependencias, paquete preparado y su correspondencia con el libro, conexión a Ollama y presencia de Qwen. No carga los pesos ni prueba la generación; informa qué queda pendiente.
- `python verificar_entorno.py --modelos`: además carga BGE-M3, genera el embedding de una consulta e interroga el índice preparado. Puede descargar pesos; no codifica el corpus.
- `python verificar_entorno.py --modelos --sin-descarga`: exige que BGE-M3 ya esté en caché; no descarga pesos.
- `python evaluar_tutor.py --output results/tutor.json`: envía 15 casos al Qwen real. Revisa los desacuerdos; no cambies las etiquetas solo para mejorar el porcentaje.

La web detecta Ollama inaccesible o Qwen ausente antes de abrir Qdrant. Si un turno falla, conserva el intento, el progreso y el historial para reintentar o descartar. El diagnóstico técnico opcional puede mostrar soluciones; déjalo oculto durante la práctica.

## Configuración única

`nikali/config.py` define los modelos y la conexión. El `config.py` de la raíz es una entrada de compatibilidad que importa esa misma configuración; ya no depende de `BaseSettings` de Pydantic.

Opcionalmente copia `.env.example` a `.env`. Se admiten `OLLAMA_HOST` y `NIKALI_EMBED_DEVICE`; las variables del sistema prevalecen sobre `.env`. BGE-M3 usa CPU por defecto para una base común. Un dispositivo como `mps` o `cuda` requiere soporte en tu equipo y volver a verificar el funcionamiento. Ollama administra por separado la ejecución de Qwen.

Los modelos de esta mini versión están fijados a Qwen 2.5 de 3B y BGE-M3. Las antiguas variables de proveedores, `NIKALI_CHAT_MODEL` y `NIKALI_EMBED_MODEL` no cambian esta selección. Reinicia Streamlit si modificas la configuración.

Las cinco dependencias directas principales tienen versiones fijadas en `requirements.txt`; Transformers tiene un rango compatible. Esto reduce diferencias, pero **no es un bloqueo completo de dependencias transitivas** ni de revisiones de pesos. Tras validar cada equipo puedes registrar su instalación con `python -m pip freeze > requirements-local.txt`. No uses ese archivo de una plataforma como instalación universal de otra.

## Preparar el material una sola vez

El paquete actual ya está generado con BGE-M3 real y se descarga con `git pull`. **Estos comandos son para quien cambie el material**, no forman parte de la instalación normal:

```bash
python preparar_indice.py
# Solo después de cambiar/revisar el Markdown o la configuración de embeddings:
python preparar_indice.py --recrear
```

Sin `--recrear`, si el paquete ya es válido, solo lo comprueba y no carga el modelo. Con `--recrear`, realiza chunking y embeddings una vez, valida el resultado y reemplaza el JSON de forma atómica. Comparte por Git el JSON junto con el Markdown y cualquier cambio de configuración. No compartas `.nikali_index/` ni el entorno virtual.

El paquete registra IDs, textos, fuentes, fragmentos parciales, vectores de 1024 dimensiones, fecha, versiones de librerías, revisión de BGE-M3 y hashes de integridad. Preparación y consultas usan la misma revisión y normalización. Si el material, el modelo o el archivo no coinciden, la aplicación muestra un error **sin recalcular silenciosamente**. Los saltos de línea de Windows y Mac producen el mismo hash del texto.

Qdrant guarda una copia local por paquete y por consumidor (`web`, `cli`, `diagnostico`), de modo que una evaluación puede ejecutarse mientras está abierta la web. Dos instancias del mismo consumidor compiten por el bloqueo: cierra una antes de abrir la otra. El modelo de consultas se carga una vez por proceso y no vuelve a generar vectores de documentos. Si borras `.nikali_index/` con los procesos cerrados, se restaura desde el JSON sin recalcular embeddings. Esta persistencia conserva el material, no el historial de conversación.

## Material y evaluación de retrieval

Se retiraron las cuatro notas generadas por el asistente. No se sustituyeron por contenido inventado ni se amplió automáticamente el fragmento. El PDF y los originales de Marker permanecen en el repositorio; no se indexan automáticamente.

El paquete conserva **dos chunks**: teoría de la regla de la cadena y el comienzo de su demostración. Este segundo chunk está marcado como parcial. Las seis preguntas de desarrollo se limitan a información presente; tres casos sin respuesta se revisan por separado.

```bash
python probar_chunking.py
python probar_rag.py "¿Cuál es la regla de la cadena en notación de Leibniz?"
python evaluar_retrieval.py --k 1 --output results/retrieval.json
```

La evaluación carga el mismo paquete e índice lógico que la web. Registra el hash del paquete, revisión del modelo y hash del corpus y calcula Hit Rate, Precision, Recall y MRR. **Es una prueba de funcionamiento muy pequeña, no evidencia de calidad general.** Si pruebas `--k 2`, recuperas todo el corpus: Hit Rate y Recall perfectos son esperables y no validan el buscador. Revisa las etiquetas con una persona antes de reportarlas. Para ampliar el experimento, incorpora material del libro previamente revisado y luego actualiza las etiquetas.

## Tutor y pruebas

El ejercicio `y = sin(x²)`, sus tres pasos, referencias y criterios están definidos en `nikali/tutor.py`. Son configuración didáctica del prototipo, **no chunks del libro**. El evaluador recibe problema, criterio, referencia, historial y avances aceptados. Solo `CORRECTO` avanza; `PARCIAL`, `INCORRECTO`, `PREGUNTA` y `REVISAR` mantienen el paso. Las pistas reciben ese contexto y material recuperado.

```bash
python -m unittest discover -s tests -v
```

Las pruebas usan Qdrant real, vectores controlados y respuestas de Qwen simuladas. Verifican la lógica, los modos separados, reinicios, recuperación tras fallos y mensajes de arranque. No miden la calidad de los modelos. Se ejecutan en Linux con Python 3.12. También se preparó el paquete con BGE-M3 real y se ejecutaron consultas reales sobre él. Qwen sigue pendiente de evaluación real, al igual que la instalación completa en los Windows y Mac del equipo.

Recorrido manual recomendado:

1. En ejercicio guiado, responde `g(x)=x²`: debe pedir la externa sin avanzar.
2. Responde `f(u)=sin(u), g(x)=x²`: debe avanzar al segundo paso.
3. `cos(x)` debe mantener el paso; `cos(u)` debe permitir avanzar.
4. `2x` todavía es incompleto; `2x cos(x²)` debe completar el ejercicio.
5. Cambia de modo y reinicia uno: el otro debe conservar su conversación.
6. En exploración, pide la demostración completa o una integral por partes: debe reconocer que falta evidencia.
7. Pide pistas y revisa que no revelen directamente la solución.

Los prompts no garantizan exactitud, abstención ni que una pista no revele la respuesta. No hay verificador simbólico ni umbral de relevancia calibrado. El vecino más cercano puede no responder la pregunta. El progreso solo vive en memoria; se pierde al reiniciar el servidor. Esta versión está pensada para uso local.

## Archivos principales

| Archivo | Función |
| --- | --- |
| `app.py` | Interfaz y estado de cada modo |
| `nikali/config.py` | Configuración única |
| `nikali/rag.py` | Chunking para preparación, embeddings de consultas, Qdrant y fuentes |
| `nikali/index.py`, `preparar_indice.py` | Preparación explícita, validación del paquete e importación persistente |
| `data/rag_preparado.json` | Chunks y embeddings reales compartidos |
| `nikali/tutor.py` | Evaluación, pistas y avance |
| `nikali/preflight.py`, `verificar_entorno.py` | Comprobaciones de arranque |
| `golden_dataset.py` | Preguntas y etiquetas; `golde_dataset.py` es un alias compatible |
| `evaluar_retrieval.py`, `evaluar_tutor.py` | Evaluaciones con modelos reales |
| `tutor_final_local.py` | Tutor en consola; `scaffold_mac.py` conserva la entrada antigua |
| `comparar_generacion.py` | Comparación ilustrativa con y sin RAG, sin calificación automática |
| `tests/` | Pruebas del programa |

Referencias: [BGE-M3](https://huggingface.co/BAAI/bge-m3), [Sentence Transformers](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html), [Qdrant Client](https://github.com/qdrant/qdrant-client), [Ollama](https://docs.ollama.com/api/chat), [instalación de Streamlit](https://docs.streamlit.io/get-started/installation/command-line).
