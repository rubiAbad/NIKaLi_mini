import ollama

# ==========================================
# 1. CONFIGURACIÓN Y ESTADO DEL DOMINIO
# ==========================================
problema_actual = "Encontrar la derivada de y = sin(x^2) usando la regla de la cadena."
pasos_resolucion = [
    "Identificar la función externa f(u) y la función interna g(x).",
    "Derivar la función externa f(u) respecto a u.",
    "Derivar la función interna g(x) respecto a x, y multiplicar ambas derivadas."
]

# ==========================================
# 2. MÓDULO DIAGNOSTICADOR (Evaluación)
# ==========================================
def evaluar_respuesta(paso_esperado, respuesta_alumno):
    prompt = f"""Eres un evaluador estricto de matemáticas. 
Tu única tarea es clasificar la respuesta del estudiante.

Paso que debe resolver: {paso_esperado}
Respuesta del estudiante: "{respuesta_alumno}"

Clasifica usando UNA SOLA PALABRA de esta lista:
- CORRECTO (Resolvió el paso bien)
- INCORRECTO (Tiene errores matemáticos o conceptuales)
- PREGUNTA (No sabe cómo avanzar o pide ayuda)

CLASIFICACIÓN:"""
    
    res = ollama.chat(model='qwen2.5:3b', messages=[{'role': 'user', 'content': prompt}])
    diagnostico = res['message']['content'].strip().upper()
    
    # Filtro de seguridad por si el modelo 3B alucina texto extra
    if "CORRECTO" in diagnostico and "INCORRECTO" not in diagnostico: return "CORRECTO"
    if "PREGUNTA" in diagnostico: return "PREGUNTA"
    return "INCORRECTO"

# ==========================================
# 3. MÓDULO TUTOR (Intervención Pedagógica)
# ==========================================
def generar_andamiaje(paso_esperado, respuesta_alumno, tipo_intervencion):
    if tipo_intervencion == "INCORRECTO":
        instruccion = "El estudiante se equivocó. Dale una pista breve para que note su error (scaffolding). REGLA: NUNCA le des la respuesta correcta directamente."
    else:
        instruccion = "El estudiante tiene una duda. Explica brevemente el concepto y anímalo a intentar el paso actual."

    prompt = f"""Eres NIKaLi, un tutor de cálculo.
{instruccion}

Paso actual: {paso_esperado}
Lo que dijo el estudiante: "{respuesta_alumno}"

Respuesta del tutor:"""

    res = ollama.chat(model='qwen2.5:3b', messages=[{'role': 'user', 'content': prompt}])
    return res['message']['content']

# ==========================================
# 4. ORQUESTADOR (El ciclo de la sesión)
# ==========================================
def iniciar_sesion():
    paso_actual = 0
    print("\n" + "="*60)
    print(f"🤖 NIKaLi: Vamos a resolver esto juntos: {problema_actual}")
    print(f"📍 Primer paso: {pasos_resolucion[paso_actual]}")
    print("="*60)

    while paso_actual < len(pasos_resolucion):
        respuesta = input("\n🧑‍🎓 Tú: ")
        if respuesta.lower() in ['salir', 'exit', 'quit']:
            break

        # 1. Diagnosticar
        estado = evaluar_respuesta(pasos_resolucion[paso_actual], respuesta)
        print(f"   [Debug Interno NIKaLi -> Estado detectado: {estado}]")

        # 2. Enrutar y Actuar
        if estado == "CORRECTO":
            paso_actual += 1
            if paso_actual < len(pasos_resolucion):
                print(f"\n🤖 NIKaLi: ¡Exacto! Siguiente paso: {pasos_resolucion[paso_actual]}")
            else:
                print("\n🤖 NIKaLi: ¡Excelente trabajo! Terminamos el problema con éxito.")
        else:
            # Si es incorrecto o pregunta, generamos el andamiaje (scaffold)
            pista = generar_andamiaje(pasos_resolucion[paso_actual], respuesta, estado)
            print(f"\n🤖 NIKaLi: {pista}")

if __name__ == "__main__":
    iniciar_sesion()
