"""Casos manuales de desarrollo; revisar etiquetas al ampliar el corpus.
Relevante significa que el chunk contiene información suficiente para responder.
Los casos sin respuesta se inspeccionan aparte: no se mezclan con recall.
"""
THEORY = "stewart:3-4-regla-de-la-cadena"
INCREMENTS = "stewart:comentarios-sobre-la-demostracion-de-la-regla-de-la-cadena"
SINE = "notas:ejemplo-seno-compuesto"
POWER = "notas:ejemplo-potencia-compuesta"
PRODUCT = "notas:regla-del-producto"
QUOTIENT = "notas:regla-del-cociente"


def case(number, question, ids, expected):
    return {"id_pregunta": f"Q_{number:03d}", "pregunta": question,
            "ids_relevantes": ids, "respuesta_referencia": expected}


GOLDEN_DATASET = [
    case(1, "¿Cuál es la regla de la cadena en notación de Leibniz?", [THEORY], "dy/dx = (dy/du)(du/dx)."),
    case(2, "¿Qué condiciones sobre f y g permiten derivar su composición?", [THEORY], "g derivable en x y f derivable en g(x)."),
    case(3, "Si u cambia al doble de rapidez que x e y al triple que u, ¿a qué rapidez cambia y respecto de x?", [THEORY], "Seis veces: las razones se multiplican."),
    case(4, "¿Cómo se descompone la raíz de x cuadrada más uno en dos funciones?", [THEORY], "f(u)=sqrt(u), g(x)=x²+1."),
    case(5, "¿Cómo se define el incremento Delta u a partir de g?", [INCREMENTS], "Delta u = g(x+Delta x)-g(x)."),
    case(6, "¿Cómo se expresa el cambio Delta y en términos de f y Delta u?", [INCREMENTS], "Delta y = f(u+Delta u)-f(u)."),
    case(7, "Para seno de x cuadrada, ¿cuáles son la función interna y la externa?", [SINE], "Interna x², externa sin(u)."),
    case(8, "¿Cuál es la derivada de sin(x²)?", [SINE], "2x cos(x²)."),
    case(9, "¿Por qué no es cos(x) la derivada de sin(x²)?", [SINE], "Hay que conservar el argumento x² y multiplicar por 2x."),
    case(10, "¿Cómo derivo (3x+1)^4?", [POWER], "12(3x+1)^3."),
    case(11, "En (3x+1)^4, ¿de dónde sale el factor 3 que multiplica la derivada?", [POWER], "De derivar la función interna 3x+1."),
    case(12, "¿Qué regla se usa para derivar el producto de dos funciones?", [PRODUCT], "a'b+ab'."),
    case(13, "¿Cómo se deriva x por seno de x?", [PRODUCT], "sin(x)+x cos(x)."),
    case(14, "¿Cuál es la regla para derivar a(x)/b(x)?", [QUOTIENT], "(a'b-ab')/b², con b distinto de cero."),
    case(15, "¿Cuánto vale la derivada de x/(x+1)?", [QUOTIENT], "1/(x+1)² para x distinto de -1."),
    case(16, "Muéstrame un ejemplo resuelto de derivación por regla de la cadena.", [SINE, POWER], "Cualquiera de los dos ejemplos completos es relevante."),
]

UNANSWERABLE_CASES = [
    case(101, "Dame la demostración completa y rigurosa de la regla de la cadena, incluido Delta u=0.", [], "El fragmento contiene solo el comienzo; reconocer que falta la demostración."),
    case(102, "¿Cómo se calcula una integral por partes?", [], "Ese tema no está en el material disponible."),
    case(103, "¿Quién ganó el partido de fútbol de ayer?", [], "No hay información sobre deportes en el material."),
]
