# golden_dataset.py

golden_dataset_stewart = [
    {
        "id_pregunta": "Q_001",
        "tipo": "recuperacion_formula",
        "pregunta_alumno": "¿Cómo se expresa matemáticamente la regla de la cadena usando la notación de Leibniz?",
        "chunk_id_esperado": 0,
        "ground_truth_humano": "Si y=f(u) y u=g(x), entonces dy/dx = (dy/du) * (du/dx)."
    },
    {
        "id_pregunta": "Q_002",
        "tipo": "recuperacion_demostracion",
        "pregunta_alumno": "¿Cómo se demuestra la regla de la cadena utilizando los incrementos Delta u y Delta x?",
        "chunk_id_esperado": 1,
        "ground_truth_humano": "Se demuestra definiendo los incrementos, asumiendo que Delta u no es cero, y aplicando el límite cuando Delta x tiende a cero a la fracción (Delta y / Delta x) = (Delta y / Delta u) * (Delta u / Delta x)."
    },
    {
        "id_pregunta": "Q_003",
        "tipo": "comprension_teorica",
        "pregunta_alumno": "Si la variable u cambia el doble de rápido que x, y la variable y cambia tres veces más rápido que u, ¿qué concepto de Leibniz explica el cambio total?",
        "chunk_id_esperado": 0,
        "ground_truth_humano": "La regla de la cadena, que establece que las razones de cambio se multiplican (dy/dx = dy/du * du/dx)."
    },
    {
        "id_pregunta": "Q_004",
        "tipo": "paso_matematico",
        "pregunta_alumno": "En la demostración formal, ¿qué pasa con Delta u cuando Delta x tiende a cero?",
        "chunk_id_esperado": 1,
        "ground_truth_humano": "Como u=g(x) es diferenciable y por lo tanto continua, cuando Delta x tiende a cero, Delta u también tiende a cero."
    }
]