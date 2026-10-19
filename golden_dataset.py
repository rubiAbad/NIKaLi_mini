"""Casos manuales de desarrollo; revisar etiquetas al ampliar el corpus.
Relevante significa que el chunk contiene información suficiente para responder.
Los casos sin respuesta se inspeccionan aparte: no se mezclan con recall.
"""
THEORY = "stewart:3-4-regla-de-la-cadena"
INCREMENTS = "stewart:comentarios-sobre-la-demostracion-de-la-regla-de-la-cadena"


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
]

UNANSWERABLE_CASES = [
    case(101, "Dame la demostración completa y rigurosa de la regla de la cadena, incluido Delta u=0.", [], "El fragmento contiene solo el comienzo; reconocer que falta la demostración."),
    case(102, "¿Cómo se calcula una integral por partes?", [], "Ese tema no está en el material disponible."),
    case(103, "¿Quién ganó el partido de fútbol de ayer?", [], "No hay información sobre deportes en el material."),
]
