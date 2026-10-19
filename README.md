# Mini NIKaLi

Prototipo local para comprender el flujo de un tutor de cálculo: material → chunks → embeddings → recuperación → respuesta, con un ejercicio guiado de regla de la cadena.

La web, la consola y las evaluaciones usan el mismo núcleo. No es una reproducción validada de ScaffoldLM ni un sistema listo para evaluar estudiantes sin supervisión.

## Iniciar en tu computadora

Necesitas Python 3.10 o posterior y [Ollama](https://ollama.com/) instalado. Desde la carpeta del repositorio:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
ollama pull nomic-embed-text
ollama pull qwen2.5:3b
python -m streamlit run app.py
```

En Windows, activa el entorno con `.venv\Scripts\activate` en lugar de `source`. Si tu sistema usa `python3`, sustituye `python` por `python3` en los comandos.

Mantén Ollama abierto. Si no está ejecutándose, inicia `ollama serve` en otra terminal. Abre la dirección local que imprime Streamlit, normalmente http://localhost:8501. La primera carga genera los embeddings y puede tardar más.

No hacen falta claves de OpenAI, Qdrant ni BGE-M3 para esta versión. Se conservó la tecnología de la web existente: Ollama, `nomic-embed-text`, similitud coseno y `qwen2.5:3b`. Los scripts anteriores con BGE-M3 + Qdrant quedan en el historial Git; sus métricas no son comparables directamente con esta versión.

## Qué cambió

- **Evaluación con contexto:** enunciado, paso, solución de referencia, criterio, historial y respuestas aceptadas. Salida JSON validada con estados `CORRECTO`, `INCORRECTO`, `PARCIAL`, `PREGUNTA` y `REVISAR`.
- **Avance controlado:** solo `CORRECTO` permite avanzar. Una clasificación ilegible no se convierte en acierto ni en error matemático del alumno.
- **Tutoría contextual:** pistas con enunciado e historial. Se recupera material tanto ante dudas como ante respuestas incompletas o incorrectas.
- **Interfaz:** problema y tarea siempre visibles, progreso, conversaciones separadas, reinicio por modo, material consultado en exploración y diagnóstico técnico opcional.
- **Fallos recuperables:** si falla un turno, no se altera el progreso; se conserva el intento para reintentar o descartarlo.
- **Un solo retrieval:** web, consola, comparación y evaluación comparten `nikali/rag.py`. Caché de la web por contenido, modelo y servidor; IDs de chunks derivados de fuente y encabezado, no posiciones numéricas.
- **Evaluación ampliada:** 16 preguntas con conjuntos de IDs relevantes, 6 chunks y 3 casos sin respuesta separados. Soporta varios chunks relevantes, Hit Rate, Precision, Recall y MRR.

## Material y límites

El archivo `output_marker/stewart_regla_cadena/fragmento_corregido.md` se conserva sin cambios. Contiene teoría y **solo el comienzo** de la demostración. El segundo chunk se marca como parcial; no se trata como prueba completa ni se usa para preguntas que exigen contenido ausente.

`data/notas_didacticas.md` añade cuatro notas **de elaboración propia**, identificadas como tales: dos ejemplos de regla de la cadena, regla del producto y regla del cociente. No se atribuyen esas notas a Stewart. Los ejemplos permiten comparar consultas específicas y las otras reglas evitan que recuperar todo el corpus sea la única prueba.

La demostración completa se convirtió en un caso sin respuesta. Para enseñarla, primero hay que incorporar y revisar una fuente completa. Los originales de Marker y el PDF se conservan en el repositorio, pero no se indexan automáticamente.

El modelo recibe instrucciones de reconocer falta de evidencia y de no revelar la solución en las pistas. **Estas instrucciones no garantizan cumplimiento.** El evaluador sigue siendo un LLM, sin verificador simbólico. Las fuentes recuperadas tampoco garantizan relevancia: el vecino más cercano puede no responder la pregunta. No hay umbral de abstención calibrado. El historial reciente enviado al modelo se limita a 12 mensajes, además del enunciado y avances aceptados.

Las sesiones viven en memoria de Streamlit; no hay cuentas ni almacenamiento permanente del progreso. Está diseñado para uso local. No publiques esta instancia tal cual como servicio multiusuario.

## Verificar paso a paso

### 1. Pruebas de lógica e interfaz, sin modelos

```bash
python -m unittest discover -s tests -v
```

Utilizan respuestas y vectores simulados. Comprueban flujo, formato, métricas y recuperación ante errores; **no miden calidad de los modelos**.

### 2. Ver exactamente qué se indexa

```bash
python probar_chunking.py
```

Revisa los IDs, las fuentes y el marcador de fragmento parcial. Los IDs cambian si renombramos el encabezado o la fuente; en ese caso hay que actualizar las etiquetas de `golden_dataset.py`. El informe incluye un hash del corpus para identificar la versión evaluada.

### 3. Retrieval real, con Ollama iniciado

```bash
python probar_rag.py "¿Cómo derivo (3x+1)^4?"
python evaluar_retrieval.py --k 1 2 --output results/retrieval.json
```

La web usa `TOP_K=1`; `k=2` es una comparación adicional. Las métricas son promedios por pregunta. Precision@k divide entre k; Recall divide entre el número de IDs relevantes. MRR considera la posición del primer relevante. Los casos sin respuesta no se incluyen en esas métricas.

Las etiquetas fueron propuestas manualmente para este corpus pequeño. Revísalas antes de reportar resultados académicos. El conjunto es de desarrollo: sigue siendo demasiado pequeño para demostrar generalización; la evaluación definitiva requiere otras preguntas, más contenido y revisión humana.

### 4. Evaluador real

```bash
python evaluar_tutor.py --output results/tutor.json
```

Incluye 15 casos: respuestas correctas e incorrectas, respuesta parcial, duda y un intento de forzar `CORRECTO`. Termina con código 1 si falla algún criterio. No llama a embeddings; permite revisar por separado el evaluador. Inspecciona los desacuerdos: no cambies las etiquetas solo para mejorar el porcentaje.

### 5. Recorrido manual en la web

1. En el ejercicio, responde `g(x)=x²`: debe permanecer en el primer paso y pedir la función externa.
2. Responde `f(u)=sin(u), g(x)=x²`: debe avanzar al segundo paso.
3. Responde `cos(x)`: debe permanecer en el segundo paso; `cos(u)` debe permitir avanzar.
4. Responde `2x`: todavía falta combinar. `2x cos(x²)` debe completar el ejercicio.
5. Cambia de modo: las conversaciones deben estar separadas. Reiniciar un modo debe conservar el otro.
6. En exploración, pide la demostración completa: debe reconocer que falta material. Repite con las preguntas de `UNANSWERABLE_CASES`.
7. Pide pistas y comprueba que no entreguen directamente el resultado. El panel técnico puede contener soluciones y debe permanecer oculto durante la práctica.

## Organización

| Archivo | Función |
| --- | --- |
| `app.py` | Interfaz Streamlit |
| `nikali/config.py` | Modelos, conexión y top-k |
| `nikali/rag.py` | Chunks, embeddings, recuperación y fuentes |
| `nikali/tutor.py` | Evaluación, pistas, historial y avance |
| `golden_dataset.py` | Única fuente de preguntas y etiquetas; `golde_dataset.py` es un alias compatible de nombre |
| `evaluar_retrieval.py` | Métricas del mismo retrieval que la web |
| `evaluar_tutor.py` | Casos de aceptación del evaluador real |
| `tutor_final_local.py` | Tutor en consola con el mismo núcleo |
| `scaffold_mac.py` | Entrada anterior redirigida al tutor compartido |
| `tests/` | Pruebas deterministas con dobles de Ollama |

Variables opcionales: `NIKALI_CHAT_MODEL`, `NIKALI_EMBED_MODEL` y `OLLAMA_HOST`. Cambiar el modelo requiere volver a ejecutar las evaluaciones; reinicia Streamlit después de cambiar variables de entorno.

## Verificación de esta corrección

Se ejecutaron 17 pruebas automatizadas, todas satisfactorias, con Python 3.12, Streamlit 1.66.0 y cliente Ollama 0.6.3. Las pruebas de interfaz usan `AppTest`, no inspección visual de navegador. No se ejecutaron los modelos reales ni se generaron métricas de calidad en el entorno de corrección; los comandos anteriores quedan preparados para tu máquina.

Referencias de las APIs empleadas: [embeddings de Ollama](https://docs.ollama.com/api/embed), [chat y salida estructurada](https://docs.ollama.com/api/chat) y [pruebas de Streamlit](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest).
