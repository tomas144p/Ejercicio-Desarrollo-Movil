"""
Materia preescrita de Matemáticas (5° a 8° básico).

Este archivo es la "fuente" del contenido que se puede leer sin internet.
Desde aquí se cargan la base interna del teléfono (SQLite) y el archivo
``database/tutor_educa_mysql.sql`` que se importa en phpMyAdmin.

Convenciones para escribir contenido nuevo:

- Las potencias se escriben con ``^``: ``5^3`` se muestra como 5 elevado a 3.
- En los pasos de un ejemplo, ``||`` separa la operación de su explicación.
- Las respuestas numéricas se guardan en formato estricto (``0.75``,
  ``5/6``, ``32000``). Si hay varias respuestas válidas se separan con ``|``.
- En las preguntas de alternativas, la respuesta debe ser idéntica a una
  de las alternativas.
"""

from __future__ import annotations


def _numerica(enunciado: str, respuesta: str, pista: str, explicacion: str) -> dict:
    """Pregunta en la que el estudiante escribe un número."""
    return {"tipo": "numerica", "enunciado": enunciado, "alternativas": [],
            "respuesta": respuesta, "pista": pista, "explicacion": explicacion}


def _alternativas(enunciado: str, alternativas: list[str], respuesta: str,
                  pista: str, explicacion: str) -> dict:
    """Pregunta en la que el estudiante elige una opción."""
    assert respuesta in alternativas, f"La respuesta {respuesta!r} no está entre las alternativas"
    return {"tipo": "alternativas", "enunciado": enunciado, "alternativas": alternativas,
            "respuesta": respuesta, "pista": pista, "explicacion": explicacion}


def _ejemplo(titulo: str, enunciado: str, pasos: list[str], resultado: str,
             comprobacion: str) -> dict:
    """Ejemplo resuelto que se dibuja como una hoja de cuaderno."""
    return {"titulo": titulo, "enunciado": enunciado, "pasos": pasos,
            "resultado": resultado, "comprobacion": comprobacion}


ASIGNATURA_ID = "mat"

TEMAS_MATEMATICAS: list[dict] = [
    # ------------------------------------------------------------------
    {
        "id": "mat-fracciones",
        "titulo": "Suma y resta de fracciones",
        "nivel": "6° básico",
        "icono": "pie-chart",
        "resumen": ("Para sumar o restar fracciones necesitas que tengan el mismo denominador. "
                    "Si no lo tienen, primero las transformas en fracciones equivalentes."),
        "contenido": [
            "Una fracción representa partes de un entero. El número de abajo, el denominador, "
            "dice en cuántas partes iguales se dividió el entero; el de arriba, el numerador, "
            "dice cuántas de esas partes tomamos. En 3/8 el entero se dividió en 8 partes y "
            "tomamos 3.",
            "Cuando dos fracciones tienen el mismo denominador, sumar es muy simple: se suman "
            "los numeradores y el denominador se mantiene. Es como juntar trozos del mismo "
            "tamaño: 3 octavos más 2 octavos son 5 octavos. Para restar se hace lo mismo, pero "
            "restando los numeradores.",
            "Si los denominadores son distintos, los trozos no son del mismo tamaño y no se "
            "pueden juntar directamente. Primero buscamos un denominador común, idealmente el "
            "mínimo común múltiplo (mcm) de los denominadores. Luego amplificamos cada fracción, "
            "multiplicando numerador y denominador por el mismo número, para que ambas queden "
            "con ese denominador.",
            "Al final conviene simplificar el resultado: dividir numerador y denominador por el "
            "mismo número hasta que no se pueda más. Por ejemplo, 3/6 se simplifica a 1/2 "
            "dividiendo ambos por 3. Una fracción simplificada vale lo mismo, solo que está "
            "escrita de la forma más corta.",
        ],
        "clave": ("Solo se suman o restan los numeradores cuando los denominadores son iguales. "
                  "Si son distintos, primero iguálalos con fracciones equivalentes."),
        "error_comun": ("Sumar numeradores con numeradores y denominadores con denominadores: "
                        "1/2 + 1/4 NO es 2/6. Los denominadores no se suman nunca."),
        "consejo_apoderado": ("Usen comida para practicar: una pizza o un queque cortado en partes "
                              "iguales. Pídale que muestre cuánto es 1/2 + 1/4 con trozos reales y "
                              "que explique por qué el resultado es 3/4. Explicar en voz alta "
                              "ayuda mucho a fijar la idea."),
        "ejemplos": [
            _ejemplo("Mismo denominador", "Calcula 2/7 + 3/7",
                     ["2/7 + 3/7 || Los denominadores son iguales (7).",
                      "(2 + 3)/7 || Sumamos solo los numeradores.",
                      "5/7 || El denominador se mantiene."],
                     "5/7",
                     "Dibuja una barra dividida en 7 partes: pinta 2 y luego 3 más. Quedan 5 de 7 pintadas."),
            _ejemplo("Distinto denominador", "Calcula 1/4 + 1/6",
                     ["1/4 + 1/6 || Los denominadores son distintos: 4 y 6.",
                      "mcm(4, 6) = 12 || El menor número que es múltiplo de 4 y de 6.",
                      "3/12 + 2/12 || 1/4 = 3/12 (por 3) y 1/6 = 2/12 (por 2).",
                      "5/12 || Ahora sí sumamos los numeradores."],
                     "5/12",
                     "5/12 ya no se puede simplificar: 5 y 12 no tienen divisores comunes."),
            _ejemplo("Resta y simplificación", "Calcula 7/10 − 1/5",
                     ["7/10 − 1/5 || Denominadores distintos: 10 y 5.",
                      "7/10 − 2/10 || 1/5 = 2/10 (amplificamos por 2).",
                      "5/10 || Restamos los numeradores: 7 − 2 = 5.",
                      "1/2 || Simplificamos dividiendo ambos por 5."],
                     "1/2",
                     "Suma para comprobar: 1/2 + 1/5 = 5/10 + 2/10 = 7/10. ¡Coincide!"),
        ],
        "preguntas": [
            _numerica("Calcula 3/8 + 2/8", "5/8",
                      "Los denominadores ya son iguales: suma solo los numeradores.",
                      "3 + 2 = 5 y el denominador 8 se mantiene: 5/8."),
            _alternativas("¿Cuál es el mínimo común múltiplo de 4 y 6?", ["10", "12", "24", "2"], "12",
                          "Escribe los múltiplos de 6 (6, 12, 18...) y busca el primero que también sea múltiplo de 4.",
                          "Múltiplos de 4: 4, 8, 12... Múltiplos de 6: 6, 12... El primero que se repite es 12."),
            _numerica("Calcula 1/2 + 1/4", "3/4",
                      "Transforma 1/2 en cuartos: 1/2 = 2/4.",
                      "1/2 = 2/4, entonces 2/4 + 1/4 = 3/4."),
            _numerica("Calcula 5/6 − 1/3 y simplifica el resultado", "1/2",
                      "Transforma 1/3 en sextos: 1/3 = 2/6.",
                      "5/6 − 2/6 = 3/6, que simplificado es 1/2."),
            _alternativas("Martina comió 1/3 de una torta y su hermano 1/2. ¿Qué parte de la torta comieron entre los dos?",
                          ["2/5", "5/6", "1/6", "2/6"], "5/6",
                          "Busca un denominador común para 3 y 2.",
                          "1/3 = 2/6 y 1/2 = 3/6. Juntos: 2/6 + 3/6 = 5/6 de la torta."),
        ],
    },
    # ------------------------------------------------------------------
    {
        "id": "mat-enteros",
        "titulo": "Números enteros: suma y resta",
        "nivel": "7° básico",
        "icono": "thermometer",
        "resumen": ("Los números enteros incluyen a los negativos. Para sumarlos y restarlos, piensa "
                    "en una recta numérica o en una temperatura que sube y baja."),
        "contenido": [
            "Los números enteros son los positivos (1, 2, 3...), el cero y los negativos (−1, −2, "
            "−3...). Los negativos aparecen en la vida diaria: una temperatura bajo cero, un piso "
            "subterráneo o una deuda. En la recta numérica, los negativos están a la izquierda del "
            "cero y los positivos a la derecha.",
            "Para sumar números con el mismo signo, se suman sus valores y se conserva el signo: "
            "−5 + (−4) = −9, como bajar 5 grados y luego 4 más. Para sumar números con distinto "
            "signo, se restan sus valores (el mayor menos el menor) y se deja el signo del número "
            "que está más lejos del cero: −6 + 9 = 3.",
            "Restar un número es lo mismo que sumar su opuesto. Por eso 7 − (−3) se transforma en "
            "7 + 3 = 10: quitar una deuda de 3 es como ganar 3. Esta regla evita tener que "
            "memorizar muchos casos, porque toda resta se puede convertir en suma.",
            "Para comparar enteros, mira la recta numérica: el que está más a la derecha es el "
            "mayor. Así, −3 es mayor que −8, aunque 8 parezca un número más grande. Entre los "
            "negativos, el que está más cerca del cero es el mayor.",
        ],
        "clave": ("Restar es sumar el opuesto: a − (−b) = a + b. Y en una suma de signos distintos, "
                  "gana el signo del número más alejado del cero."),
        "error_comun": ("Pensar que −8 es mayor que −3 porque 8 es mayor que 3. En los negativos es al "
                        "revés: −3 está más a la derecha en la recta, así que es mayor."),
        "consejo_apoderado": ("El termómetro y el ascensor son grandes aliados. Pregunte, por ejemplo: "
                              "«si en Punta Arenas amaneció a −4 °C y subió 9 grados, ¿qué temperatura "
                              "hay?». También sirve jugar con los pisos de un estacionamiento subterráneo."),
        "ejemplos": [
            _ejemplo("Signos distintos", "Calcula −6 + 9",
                     ["−6 + 9 || Los signos son distintos.",
                      "9 − 6 = 3 || Restamos los valores: el mayor menos el menor.",
                      "+3 || Gana el signo del 9, que está más lejos del cero."],
                     "3",
                     "En la recta: parte en −6 y avanza 9 pasos a la derecha. Llegas a 3."),
            _ejemplo("Mismo signo negativo", "Calcula −5 + (−4)",
                     ["−5 + (−4) || Ambos son negativos.",
                      "5 + 4 = 9 || Sumamos los valores.",
                      "−9 || Conservamos el signo negativo."],
                     "−9",
                     "Si debes $5.000 y te prestan $4.000 más, ahora debes $9.000."),
            _ejemplo("Restar un negativo", "Calcula 4 − (−6)",
                     ["4 − (−6) || Restar un número es sumar su opuesto.",
                      "4 + 6 || El opuesto de −6 es 6.",
                      "10 || Ahora es una suma normal."],
                     "10",
                     "Comprueba: 10 + (−6) = 4. ¡Vuelves al inicio!"),
        ],
        "preguntas": [
            _numerica("Calcula −8 + 11", "3",
                      "Signos distintos: resta 11 − 8 y deja el signo del número más lejos del cero.",
                      "11 − 8 = 3 y gana el signo del 11 (positivo): 3."),
            _numerica("Calcula −3 + (−7)", "-10",
                      "Ambos son negativos: suma los valores y conserva el signo.",
                      "3 + 7 = 10 y se conserva el signo negativo: −10."),
            _numerica("Calcula 7 − (−3)", "10",
                      "Restar un negativo es sumar su opuesto.",
                      "7 − (−3) = 7 + 3 = 10."),
            _alternativas("¿Cuál de estos números es el mayor?", ["−8", "−3", "−12", "−5"], "−3",
                          "El mayor es el que está más cerca del cero, más a la derecha en la recta.",
                          "En la recta numérica −3 está más a la derecha que −5, −8 y −12, por eso es el mayor."),
            _numerica("En Punta Arenas amaneció a −4 °C y durante el día la temperatura subió 9 grados. "
                      "¿Qué temperatura hubo en la tarde?", "5",
                      "Calcula −4 + 9.",
                      "−4 + 9 = 5. En la tarde hubo 5 °C."),
        ],
    },
    # ------------------------------------------------------------------
    {
        "id": "mat-porcentajes",
        "titulo": "Porcentajes",
        "nivel": "7° básico",
        "icono": "percent",
        "resumen": ("Un porcentaje indica cuántas partes de cada 100 se toman. Calcular el 25 % de "
                    "algo es encontrar 25 de cada 100 partes."),
        "contenido": [
            "La palabra porcentaje viene de «por ciento»: de cada cien. El 30 % significa 30 de "
            "cada 100, y se puede escribir como fracción (30/100) o como decimal (0,3). El 100 % "
            "es el total y el 50 % es la mitad.",
            "Para calcular un porcentaje de una cantidad, multiplica la cantidad por el porcentaje "
            "y divide por 100. Por ejemplo, el 20 % de 350 es 350 × 20 ÷ 100 = 70. También puedes "
            "usar el decimal: 350 × 0,2 = 70.",
            "Hay atajos muy útiles: el 50 % es la mitad, el 25 % es la cuarta parte, el 10 % es "
            "dividir por 10 y el 1 % es dividir por 100. Con el 10 % puedes armar otros: el 30 % "
            "es tres veces el 10 %.",
            "En los descuentos, el porcentaje se calcula sobre el precio original y luego se resta. "
            "Para saber qué porcentaje es una parte del total, divide la parte por el total y "
            "multiplica por 100.",
        ],
        "clave": ("Porcentaje de una cantidad = cantidad × porcentaje ÷ 100. El 10 % es dividir por "
                  "10, y desde ahí puedes calcular casi cualquier porcentaje."),
        "error_comun": ("Olvidar restar el descuento: si algo cuesta $20.000 con 10 % de descuento, "
                        "$2.000 es lo que te descuentan, no lo que pagas. El precio final es $18.000."),
        "consejo_apoderado": ("Aprovechen las ofertas del supermercado o de los catálogos: pídale que "
                              "calcule cuánto se ahorra con un 10 %, 25 % o 50 % de descuento y cuánto "
                              "se paga al final. Usar precios reales hace que el tema tenga sentido."),
        "ejemplos": [
            _ejemplo("El 10 % como atajo", "Calcula el 30 % de 250",
                     ["10 % de 250 = 25 || El 10 % es dividir por 10.",
                      "30 % = 3 × 10 % || El 30 % son tres veces el 10 %.",
                      "3 × 25 = 75 || Multiplicamos."],
                     "75",
                     "Con la fórmula: 250 × 30 ÷ 100 = 7.500 ÷ 100 = 75."),
            _ejemplo("Precio con descuento",
                     "Una polera cuesta $12.000 y tiene 25 % de descuento. ¿Cuánto pagas?",
                     ["25 % de 12.000 || El 25 % es la cuarta parte.",
                      "12.000 ÷ 4 = 3.000 || Este es el descuento.",
                      "12.000 − 3.000 = 9.000 || Restamos el descuento al precio."],
                     "$9.000",
                     "Pagas el 75 % del precio: 12.000 × 0,75 = 9.000."),
            _ejemplo("¿Qué porcentaje es?",
                     "En un curso de 40 estudiantes, 10 llegan en bicicleta. ¿Qué porcentaje es?",
                     ["10 ÷ 40 = 0,25 || Parte dividida por el total.",
                      "0,25 × 100 = 25 || Multiplicamos por 100."],
                     "25 %",
                     "10 es la cuarta parte de 40, y la cuarta parte es el 25 %."),
        ],
        "preguntas": [
            _numerica("¿Cuánto es el 10 % de 450?", "45",
                      "El 10 % es dividir por 10.", "450 ÷ 10 = 45."),
            _numerica("¿Cuánto es el 25 % de 80?", "20",
                      "El 25 % es la cuarta parte: divide por 4.", "80 ÷ 4 = 20."),
            _alternativas("¿Cómo se escribe 30 % como número decimal?", ["3,0", "0,3", "0,03", "30,0"], "0,3",
                          "30 % es 30 de cada 100: divide 30 por 100.", "30 ÷ 100 = 0,3."),
            _numerica("Unas zapatillas cuestan $40.000 y tienen 20 % de descuento. ¿Cuánto pagas?", "32000",
                      "Primero calcula el descuento (20 % de 40.000) y luego réstalo.",
                      "20 % de 40.000 = 8.000. Pagas 40.000 − 8.000 = $32.000."),
            _numerica("En una prueba de 30 preguntas, Javiera contestó 6 mal. ¿Qué porcentaje de las "
                      "preguntas contestó mal?", "20",
                      "Divide 6 por 30 y multiplica por 100.", "6 ÷ 30 = 0,2 y 0,2 × 100 = 20 %."),
        ],
    },
    # ------------------------------------------------------------------
    {
        "id": "mat-potencias",
        "titulo": "Potencias",
        "nivel": "7° básico",
        "icono": "superscript",
        "resumen": ("Una potencia es una multiplicación abreviada: la base se multiplica por sí misma "
                    "tantas veces como indica el exponente."),
        "contenido": [
            "En 5^3 el 5 es la base y el 3 es el exponente. Se lee «cinco elevado a tres» o «cinco "
            "al cubo», y significa 5 × 5 × 5 = 125. El exponente no multiplica a la base: indica "
            "cuántas veces se repite la base como factor.",
            "Algunas potencias tienen nombre propio. Elevar a 2 se llama «al cuadrado», porque 4^2 "
            "es el área de un cuadrado de lado 4. Elevar a 3 se llama «al cubo», porque 3^3 es el "
            "volumen de un cubo de arista 3. Además, cualquier número elevado a 1 es el mismo número.",
            "Las potencias de 10 son muy útiles: 10^2 = 100, 10^3 = 1.000 y 10^6 = 1.000.000. El "
            "exponente te dice cuántos ceros hay después del 1. Por eso se usan para escribir "
            "números muy grandes, como la distancia entre planetas.",
            "Cuando multiplicas potencias de igual base, se conserva la base y se suman los "
            "exponentes: 2^3 × 2^4 = 2^7. Tiene lógica: son tres 2 multiplicados por otros cuatro "
            "2, en total siete 2.",
        ],
        "clave": ("El exponente indica cuántas veces se multiplica la base por sí misma: "
                  "2^4 = 2 × 2 × 2 × 2 = 16, no 2 × 4."),
        "error_comun": "Multiplicar la base por el exponente: 5^3 NO es 15. Es 5 × 5 × 5 = 125.",
        "consejo_apoderado": ("Pídale que arme un cuadrado con fósforos, legos o baldosas del piso: un "
                              "cuadrado de 3 por 3 tiene 3^2 = 9 piezas. Luego pregunte cuántas tendría "
                              "uno de 4 por 4. Ver la potencia hace que no se confunda con la multiplicación."),
        "ejemplos": [
            _ejemplo("Calcular una potencia", "Calcula 2^5",
                     ["2^5 || Base 2, exponente 5.",
                      "2 × 2 × 2 × 2 × 2 || El 2 se repite 5 veces.",
                      "4 × 4 × 2 || Agrupamos de a dos: 2 × 2 = 4.",
                      "32 || 4 × 4 = 16 y 16 × 2 = 32."],
                     "32",
                     "Revisa que no sea 2 × 5 = 10: el exponente no multiplica a la base."),
            _ejemplo("Potencias de 10", "Escribe 10^4 como número",
                     ["10^4 || Base 10, exponente 4.",
                      "10 × 10 × 10 × 10 || El 10 se repite 4 veces.",
                      "10.000 || Un 1 seguido de 4 ceros."],
                     "10.000",
                     "Cuenta los ceros: son 4, igual que el exponente."),
            _ejemplo("Igual base", "Escribe 3^2 × 3^2 como una sola potencia y calcula su valor",
                     ["3^2 × 3^2 || Las dos potencias tienen base 3.",
                      "3^4 || Conservamos la base y sumamos los exponentes: 2 + 2 = 4.",
                      "3 × 3 × 3 × 3 = 81 || Calculamos el valor."],
                     "81",
                     "Directo: 3^2 = 9 y 9 × 9 = 81. ¡Coincide!"),
        ],
        "preguntas": [
            _numerica("Calcula 5^3", "125", "Multiplica 5 × 5 × 5.", "5 × 5 = 25 y 25 × 5 = 125."),
            _alternativas("¿Qué significa 6^2?", ["6 × 2", "6 × 6", "6 + 6", "2 × 2 × 2 × 2 × 2 × 2"], "6 × 6",
                          "El exponente dice cuántas veces se repite la base.",
                          "6^2 = 6 × 6 = 36: el 6 se repite 2 veces."),
            _numerica("Calcula 2^6", "64", "Duplica partiendo de 2: 2, 4, 8...",
                      "2, 4, 8, 16, 32, 64: 2^6 = 64."),
            _alternativas("¿Cómo se escribe 4^2 × 4^3 como una sola potencia?", ["4^5", "4^6", "16^5", "8^5"], "4^5",
                          "Con igual base, se conserva la base y se suman los exponentes.",
                          "Se conserva la base 4 y se suman los exponentes: 2 + 3 = 5. Resultado: 4^5."),
            _numerica("Una caja con forma de cubo mide 3 cm por lado. ¿Cuántos cubitos de 1 cm caben "
                      "dentro? (Calcula 3^3)", "27",
                      "Un cubo de lado 3 tiene 3 × 3 × 3 cubitos.", "3^3 = 3 × 3 × 3 = 27 cubitos."),
        ],
    },
    # ------------------------------------------------------------------
    {
        "id": "mat-ecuaciones",
        "titulo": "Ecuaciones de primer grado",
        "nivel": "7° básico",
        "icono": "scale",
        "resumen": ("Una ecuación es una igualdad con un valor desconocido. Resolverla es encontrar el "
                    "número que hace verdadera la igualdad, manteniendo siempre el equilibrio."),
        "contenido": [
            "Una ecuación es como una balanza en equilibrio: lo que está a la izquierda del signo "
            "igual pesa lo mismo que lo que está a la derecha. La letra, normalmente x, representa "
            "un número que no conocemos. Resolver la ecuación es descubrir cuánto vale x.",
            "Para despejar x usamos operaciones inversas: la suma se deshace con una resta, y la "
            "multiplicación con una división. En x + 9 = 20 restamos 9 a ambos lados y queda "
            "x = 11. En 4x = 28 dividimos ambos lados por 4 y queda x = 7.",
            "La regla de oro es mantener el equilibrio: lo que haces a un lado del signo igual, lo "
            "haces también al otro. Si solo le quitas 9 a un lado, la balanza se desequilibra y el "
            "resultado cambia.",
            "Cuando hay dos pasos, como en 2x + 1 = 9, primero se deshace la suma o resta y después "
            "la multiplicación o división: restamos 1 a ambos lados (2x = 8) y luego dividimos por 2 "
            "(x = 4). Siempre puedes comprobar reemplazando x en la ecuación original.",
        ],
        "clave": ("Lo que hagas a un lado del signo igual, hazlo también al otro. Primero se deshacen "
                  "las sumas y restas; después, las multiplicaciones y divisiones."),
        "error_comun": ("Cambiar un número de lado sin cambiar la operación: en x + 9 = 20, el 9 pasa "
                        "restando (x = 20 − 9), no sumando."),
        "consejo_apoderado": ("Jueguen a «adivina mi número»: «pensé un número, lo multipliqué por 3, le "
                              "resté 5 y me dio 10». Pídale que descubra el número y que explique cómo lo "
                              "hizo. Así practica despejar sin darse cuenta."),
        "ejemplos": [
            _ejemplo("Un paso con suma", "Resuelve x + 7 = 15",
                     ["x + 7 = 15 || El 7 está sumando a la x.",
                      "x + 7 − 7 = 15 − 7 || Restamos 7 a ambos lados.",
                      "x = 8 || Queda la x sola."],
                     "x = 8",
                     "Reemplaza: 8 + 7 = 15. ¡Correcto!"),
            _ejemplo("Un paso con multiplicación", "Resuelve 5x = 35",
                     ["5x = 35 || 5x significa 5 × x.",
                      "5x ÷ 5 = 35 ÷ 5 || Dividimos ambos lados por 5.",
                      "x = 7 || Resultado."],
                     "x = 7",
                     "Reemplaza: 5 × 7 = 35. ¡Correcto!"),
            _ejemplo("Dos pasos", "Resuelve 2x + 3 = 11",
                     ["2x + 3 = 11 || Primero deshacemos la suma.",
                      "2x = 11 − 3 = 8 || Restamos 3 a ambos lados.",
                      "x = 8 ÷ 2 || Luego dividimos por 2.",
                      "x = 4 || Resultado."],
                     "x = 4",
                     "Reemplaza: 2 × 4 + 3 = 8 + 3 = 11. ¡Correcto!"),
        ],
        "preguntas": [
            _numerica("Resuelve x + 9 = 20", "11", "Resta 9 a ambos lados.",
                      "x = 20 − 9 = 11. Comprobación: 11 + 9 = 20."),
            _numerica("Resuelve 3x − 5 = 10", "5", "Primero suma 5 a ambos lados; después divide por 3.",
                      "3x = 15, entonces x = 15 ÷ 3 = 5."),
            _numerica("Resuelve x ÷ 4 = 3", "12",
                      "La división se deshace multiplicando: multiplica ambos lados por 4.",
                      "x = 3 × 4 = 12. Comprobación: 12 ÷ 4 = 3."),
            _alternativas("¿Cuál es la solución de 2x + 7 = 19?", ["x = 13", "x = 6", "x = 12", "x = 26"], "x = 6",
                          "Resta 7 y después divide por 2.", "2x = 19 − 7 = 12, y x = 12 ÷ 2 = 6."),
            _numerica("Resuelve 4x + 3 = 31", "7", "Resta 3 a ambos lados y luego divide por 4.",
                      "4x = 28, entonces x = 28 ÷ 4 = 7."),
        ],
    },
    # ------------------------------------------------------------------
    {
        "id": "mat-proporcionalidad",
        "titulo": "Proporcionalidad directa",
        "nivel": "7° básico",
        "icono": "trending-up",
        "resumen": ("Dos cantidades son directamente proporcionales cuando, al multiplicar una por un "
                    "número, la otra se multiplica por el mismo número. Su cociente siempre es constante."),
        "contenido": [
            "Si un pasaje de micro cuesta $800, dos pasajes cuestan $1.600 y cuatro cuestan $3.200. "
            "Cuando la cantidad de pasajes se duplica, el precio también se duplica. Eso es "
            "proporcionalidad directa: ambas cantidades crecen (o disminuyen) al mismo ritmo.",
            "En una relación proporcional, al dividir una cantidad por la otra siempre se obtiene el "
            "mismo número, llamado constante de proporcionalidad (k). En el ejemplo, 1.600 ÷ 2 = 800 "
            "y 3.200 ÷ 4 = 800: la constante es el precio de un pasaje.",
            "Con la constante puedes calcular cualquier valor: y = k × x. Si k = 800, entonces 10 "
            "pasajes cuestan 10 × 800 = 8.000. Otra estrategia es la reducción a la unidad: primero "
            "calculas cuánto vale 1 y luego multiplicas.",
            "En una tabla de valores proporcionales, cada par de números tiene el mismo cociente, y si "
            "los dibujas en un gráfico forman una línea recta que parte del cero. Si el cociente cambia "
            "de una columna a otra, la relación no es proporcional.",
        ],
        "clave": ("Si una cantidad se multiplica por un número, la otra se multiplica por el mismo "
                  "número. El cociente y ÷ x es siempre la misma constante k."),
        "error_comun": ("Sumar en vez de multiplicar: si 2 pasajes cuestan $1.600, 4 pasajes NO cuestan "
                        "$1.600 + 2. Se duplica la cantidad, entonces se duplica el precio: $3.200."),
        "consejo_apoderado": ("Cocinen juntos una receta y pídale que la ajuste: si la receta es para 4 "
                              "personas y serán 6, ¿cuánta harina se necesita? También sirve calcular "
                              "cuánto cuesta 1 kg si 3 kg cuestan $4.500."),
        "ejemplos": [
            _ejemplo("Reducción a la unidad", "3 kg de manzanas cuestan $4.500. ¿Cuánto cuestan 5 kg?",
                     ["3 kg cuestan 4.500 || Dato conocido.",
                      "1 kg: 4.500 ÷ 3 = 1.500 || Calculamos el valor de 1 kg.",
                      "5 kg: 5 × 1.500 = 7.500 || Multiplicamos por 5."],
                     "$7.500",
                     "La constante se mantiene: 7.500 ÷ 5 = 1.500 y 4.500 ÷ 3 = 1.500."),
            _ejemplo("Encontrar la constante",
                     "2 cuadernos cuestan $2.400 y 6 cuadernos $7.200. ¿Es proporcional? ¿Cuánto vale k?",
                     ["2.400 ÷ 2 = 1.200 || Primer cociente.",
                      "7.200 ÷ 6 = 1.200 || Segundo cociente.",
                      "k = 1.200 || Los cocientes son iguales: es proporcional."],
                     "k = 1.200",
                     "k es el precio de un cuaderno."),
            _ejemplo("Velocidad constante", "Un bus viaja a 80 km por hora. ¿Cuántos km recorre en 4 horas?",
                     ["1 hora: 80 km || La constante es 80.",
                      "4 horas: 4 × 80 || Cuatro veces más tiempo, cuatro veces más distancia.",
                      "320 km || Resultado."],
                     "320 km",
                     "320 ÷ 4 = 80: se mantiene la constante."),
        ],
        "preguntas": [
            _numerica("Si 2 entradas al cine cuestan $7.000, ¿cuánto cuestan 5 entradas?", "17500",
                      "Calcula primero cuánto cuesta 1 entrada.",
                      "1 entrada: 7.000 ÷ 2 = 3.500. 5 entradas: 5 × 3.500 = $17.500."),
            _alternativas("¿Cuál de estas tablas muestra una relación directamente proporcional?",
                          ["(1, 3) (2, 6) (3, 9)", "(1, 3) (2, 5) (3, 7)", "(1, 2) (2, 2) (3, 2)", "(1, 4) (2, 6) (3, 8)"],
                          "(1, 3) (2, 6) (3, 9)",
                          "Divide el segundo número por el primero en cada par: ¿da siempre lo mismo?",
                          "En (1, 3) (2, 6) (3, 9) el cociente siempre es 3. En las demás cambia."),
            _numerica("Un auto avanza a velocidad constante de 60 km por hora. ¿Cuántos km recorre en 3 horas?", "180",
                      "Multiplica los km de una hora por la cantidad de horas.", "3 × 60 = 180 km."),
            _numerica("Una receta para 4 personas usa 300 g de arroz. ¿Cuántos gramos se necesitan para 6 personas?", "450",
                      "Calcula cuánto arroz corresponde a 1 persona.",
                      "300 ÷ 4 = 75 g por persona, y 6 × 75 = 450 g."),
            _alternativas("Si y = 5 × x, ¿cuánto vale y cuando x = 8?", ["13", "40", "85", "3"], "40",
                          "Reemplaza x por 8 en la fórmula.", "y = 5 × 8 = 40."),
        ],
    },
    # ------------------------------------------------------------------
    {
        "id": "mat-pitagoras",
        "titulo": "Teorema de Pitágoras",
        "nivel": "8° básico",
        "icono": "triangle-right",
        "resumen": ("En todo triángulo rectángulo, el cuadrado de la hipotenusa es igual a la suma de "
                    "los cuadrados de los catetos: a^2 + b^2 = c^2."),
        "contenido": [
            "Un triángulo rectángulo tiene un ángulo de 90°, como la esquina de un cuaderno. Los dos "
            "lados que forman ese ángulo se llaman catetos, y el lado más largo, que está frente al "
            "ángulo recto, se llama hipotenusa.",
            "El teorema de Pitágoras dice que si los catetos miden a y b, y la hipotenusa mide c, "
            "entonces a^2 + b^2 = c^2. Por ejemplo, con catetos 3 y 4: 3^2 + 4^2 = 9 + 16 = 25, y "
            "como 5^2 = 25, la hipotenusa mide 5.",
            "Para encontrar la hipotenusa, suma los cuadrados de los catetos y saca la raíz cuadrada "
            "del resultado. Para encontrar un cateto, resta: al cuadrado de la hipotenusa le quitas "
            "el cuadrado del otro cateto, y luego sacas la raíz. La raíz cuadrada de 25 es 5 porque "
            "5 × 5 = 25.",
            "Hay tríos de números enteros que cumplen el teorema, llamados tríos pitagóricos: "
            "(3, 4, 5), (6, 8, 10) y (5, 12, 13). Son útiles para comprobar si una esquina está "
            "bien «a escuadra», algo que usan los maestros constructores.",
        ],
        "clave": ("La hipotenusa es siempre el lado más largo y está frente al ángulo recto. Para "
                  "hallarla se suman los cuadrados; para hallar un cateto, se restan."),
        "error_comun": ("Sumar los lados sin elevarlos al cuadrado: con catetos 3 y 4, la hipotenusa "
                        "NO es 7. Es la raíz de 9 + 16 = 25, o sea 5."),
        "consejo_apoderado": ("Busquen triángulos rectángulos en la casa: una escalera apoyada en la "
                              "pared, la diagonal de una mesa o de una pantalla. Midan los catetos con "
                              "una huincha y comprueben juntos si la diagonal coincide con el teorema."),
        "ejemplos": [
            _ejemplo("Encontrar la hipotenusa", "Los catetos miden 6 cm y 8 cm. ¿Cuánto mide la hipotenusa?",
                     ["c^2 = 6^2 + 8^2 || Aplicamos a^2 + b^2 = c^2.",
                      "c^2 = 36 + 64 = 100 || Calculamos los cuadrados y sumamos.",
                      "c = √100 || Sacamos la raíz cuadrada.",
                      "c = 10 cm || Porque 10 × 10 = 100."],
                     "10 cm",
                     "(6, 8, 10) es el doble del trío (3, 4, 5)."),
            _ejemplo("Encontrar un cateto",
                     "La hipotenusa mide 13 cm y un cateto 5 cm. ¿Cuánto mide el otro cateto?",
                     ["b^2 = 13^2 − 5^2 || Para un cateto, restamos.",
                      "b^2 = 169 − 25 = 144 || Calculamos.",
                      "b = √144 = 12 || Porque 12 × 12 = 144."],
                     "12 cm",
                     "5^2 + 12^2 = 25 + 144 = 169 = 13^2. ¡Correcto!"),
            _ejemplo("Una rampa", "Una rampa mide 15 m de largo y su base horizontal mide 12 m. ¿Qué altura alcanza?",
                     ["15 m es la hipotenusa || La rampa está frente al ángulo recto.",
                      "h^2 = 15^2 − 12^2 || Buscamos un cateto: restamos.",
                      "h^2 = 225 − 144 = 81 || Calculamos.",
                      "h = √81 = 9 m || Porque 9 × 9 = 81."],
                     "9 m",
                     "9^2 + 12^2 = 81 + 144 = 225 = 15^2."),
        ],
        "preguntas": [
            _numerica("Los catetos de un triángulo rectángulo miden 3 cm y 4 cm. ¿Cuánto mide la hipotenusa?", "5",
                      "Calcula 3^2 + 4^2 y luego saca la raíz cuadrada.",
                      "3^2 + 4^2 = 9 + 16 = 25, y √25 = 5 cm."),
            _alternativas("En un triángulo rectángulo, ¿cuál lado es la hipotenusa?",
                          ["El lado más corto", "El lado opuesto al ángulo recto",
                           "Cualquiera de los catetos", "El lado de la base"],
                          "El lado opuesto al ángulo recto",
                          "Mira qué lado queda frente a la esquina de 90°.",
                          "La hipotenusa está frente al ángulo recto y es siempre el lado más largo."),
            _numerica("La hipotenusa mide 10 cm y un cateto mide 6 cm. ¿Cuánto mide el otro cateto?", "8",
                      "Resta 10^2 − 6^2 y luego saca la raíz.", "100 − 36 = 64 y √64 = 8 cm."),
            _alternativas("¿Cuál de estos tríos de medidas forma un triángulo rectángulo?",
                          ["(2, 3, 4)", "(9, 12, 15)", "(4, 5, 7)", "(5, 6, 8)"], "(9, 12, 15)",
                          "Comprueba si el cuadrado del mayor es igual a la suma de los cuadrados de los otros dos.",
                          "9^2 + 12^2 = 81 + 144 = 225 = 15^2."),
            _numerica("Una escalera de 5 m se apoya en una pared y su base queda a 3 m de la pared. ¿A qué "
                      "altura de la pared llega la escalera?", "4",
                      "La escalera es la hipotenusa. Calcula 5^2 − 3^2.", "25 − 9 = 16 y √16 = 4 m."),
        ],
    },
]
