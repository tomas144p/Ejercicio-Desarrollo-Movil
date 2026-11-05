"""
Tutor de demostración que funciona SIN clave de IA.

No es una inteligencia artificial: reconoce palabras clave ("explícame",
"ejemplo", "prueba", "pista"...) y responde usando la materia guardada en la
base de datos. Sirve para presentar el prototipo aunque no se haya
configurado una clave, y como respaldo si la IA real falla.

Sigue la misma pedagogía que se le pide a la IA real: explicar, mostrar un
ejemplo resuelto y tomar una mini prueba con pistas.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from ...evaluacion import CorrectorRespuestas, SesionPrueba, normalizar_texto
from ...modelos import EscalaNotas, EstadoRefuerzo


@dataclass
class EstadoTutorLocal:
    """Lo que el tutor recuerda dentro de una conversación."""

    tema_id: str | None = None
    sesion: SesionPrueba | None = None
    fallos: int = 0
    indice_ejemplo: int = 0
    indice_parrafo: int = 0


class TutorLocal:
    PALABRAS_TEMA = {
        "mat-fracciones": ("fraccion", "denominador", "numerador", "mcm", "minimo comun"),
        "mat-enteros": ("entero", "negativo", "bajo cero", "recta numerica"),
        "mat-porcentajes": ("porcentaje", "por ciento", "descuento"),
        "mat-potencias": ("potencia", "exponente", "al cuadrado", "al cubo", "elevado"),
        "mat-ecuaciones": ("ecuacion", "despejar", "incognita"),
        "mat-proporcionalidad": ("proporcional", "regla de tres"),
        "mat-pitagoras": ("pitagoras", "hipotenusa", "cateto", "triangulo rectangulo"),
    }
    # El orden importa: se usa la primera intención que coincida.
    INTENCIONES = (
        ("pista", ("pista", "ayudita")),
        ("ejemplo", ("ejemplo", "muestrame", "resuelto", "resuelve uno")),
        ("simple", ("mas simple", "mas facil", "otra forma", "otra manera", "no entendi", "no entiendo")),
        ("explicar", ("explica", "que es", "que son", "como se", "como hago", "por que", "no se", "duda",
                      "ayuda", "ensena", "entender", "repasa")),
        ("prueba", ("prueba", "evalua", "preguntame", "practic", "quiz", "hazme preguntas", "test")),
        ("error", ("error", "equivoc", "confund", "cuidado")),
        ("seguir", ("sigamos", "seguir", "continua", "siguiente", "dale", "ya", "ok", "si")),
        ("gracias", ("gracias", "genial", "bacan", "entendi")),
        ("saludo", ("hola", "buenas", "buenos dias", "hey")),
    )
    FELICITACIONES = ("¡Correcto!", "¡Muy bien!", "¡Exacto!", "¡Eso es!")

    def __init__(self, datos):
        self.datos = datos      # ServicioDatos: entrega temas, ejemplos y preguntas
        self.corrector = CorrectorRespuestas()

    # ------------------------------------------------------------------
    def saludo(self, contexto) -> str:
        nombre = contexto.usuario.primer_nombre
        if contexto.modo == "apoderado":
            hijo = contexto.ficha.estudiante.primer_nombre if contexto.ficha else "tu estudiante"
            return (f"Hola, {nombre}. Soy el asistente para familias de Tutor Educa. Puedo contarte cómo va "
                    f"{hijo}, qué está reforzando y darte ideas simples para apoyar en casa. ¿Por dónde partimos?")
        if contexto.tema:
            return (f"¡Hola, {nombre}! Soy tu tutor de matemáticas. Hoy trabajamos **{contexto.tema.titulo}**. "
                    "Puedo explicarte el tema, mostrarte un ejemplo resuelto o hacerte una mini prueba. "
                    "¿Qué te gustaría?")
        return (f"¡Hola, {nombre}! Soy tu tutor de matemáticas. Cuéntame qué tema quieres repasar "
                "(fracciones, enteros, porcentajes, potencias, ecuaciones, proporcionalidad o Pitágoras) "
                "o escribe tu duda.")

    def responder(self, contexto, estado: EstadoTutorLocal, texto: str) -> str:
        if contexto.modo == "apoderado":
            return self._responder_apoderado(contexto, texto)
        return self._responder_estudiante(contexto, estado, texto)

    # ------------------------------------------------------------------
    # Modo estudiante
    # ------------------------------------------------------------------
    def _intencion(self, limpio: str) -> str | None:
        palabras = set(re.findall(r"[a-z]+", limpio))
        for intencion, claves in self.INTENCIONES:
            for clave in claves:
                # Palabras cortas ("si", "ya", "ok") deben coincidir completas.
                if (len(clave) <= 3 and clave in palabras) or (len(clave) > 3 and clave in limpio):
                    return intencion
        return None

    def _detectar_tema(self, limpio: str) -> str | None:
        for tema_id, claves in self.PALABRAS_TEMA.items():
            if any(c in limpio for c in claves):
                return tema_id
        return None

    @staticmethod
    def _parece_respuesta(limpio: str, pregunta) -> bool:
        if re.search(r"\d", limpio):
            return True
        if pregunta is not None and pregunta.es_alternativas:
            if re.fullmatch(r"[a-d][).]?", limpio):
                return True
            return any(limpio == normalizar_texto(a) for a in pregunta.alternativas)
        return False

    def _responder_estudiante(self, contexto, estado: EstadoTutorLocal, texto: str) -> str:
        limpio = normalizar_texto(texto)
        prefijo = ""
        nuevo = self._detectar_tema(limpio)
        if nuevo and nuevo != estado.tema_id and self.datos.tema(nuevo):
            estado.tema_id, estado.sesion, estado.indice_ejemplo, estado.indice_parrafo = nuevo, None, 0, 0
            prefijo = f"Vamos con **{self.datos.tema(nuevo).titulo}**. "
        tema = self.datos.tema(estado.tema_id) if estado.tema_id else None
        intencion = self._intencion(limpio)
        sesion = estado.sesion

        # Hay una mini prueba en curso: casi todo se interpreta como respuesta.
        if sesion and not sesion.terminada and not prefijo:
            if intencion in ("pista", "simple", "error") or (intencion == "explicar" and "no se" in limpio):
                return self._pista(estado)
            if self._parece_respuesta(limpio, sesion.actual) or intencion is None:
                return self._corregir(estado, texto)
            if intencion == "seguir":
                return self._texto_pregunta(sesion)
            if intencion == "prueba":
                return "Ya estamos en una mini prueba. " + self._texto_pregunta(sesion)
            return (self._segun_intencion(intencion, tema, estado, contexto)
                    + "\n\nCuando quieras, escribe «sigamos» para volver a la prueba.")

        if tema is None:
            return self.saludo(contexto) if intencion in ("saludo", None) else (
                "¿Con qué tema quieres trabajar? Puedo ayudarte con fracciones, números enteros, porcentajes, "
                "potencias, ecuaciones, proporcionalidad o el teorema de Pitágoras.")
        return prefijo + self._segun_intencion(intencion, tema, estado, contexto)

    def _segun_intencion(self, intencion, tema, estado, contexto) -> str:
        if intencion == "saludo":
            return (f"¡Hola, {contexto.usuario.primer_nombre}! Seguimos con **{tema.titulo}**. ¿Te lo explico, "
                    "te muestro un ejemplo o te hago una mini prueba?")
        if intencion == "gracias":
            return "¡De nada! ¿Seguimos con un ejemplo o prefieres una mini prueba?"
        if intencion == "explicar":
            parrafos = tema.parrafos
            indice = estado.indice_parrafo % len(parrafos)
            estado.indice_parrafo += 1
            texto = f"{tema.resumen}\n\n{parrafos[0]}" if indice == 0 else parrafos[indice]
            return texto + "\n\n¿Sigo explicando o prefieres ver un ejemplo resuelto?"
        if intencion == "simple":
            return (f"Te lo digo en simple: {tema.clave}\n\nY ojo con este error típico: {tema.error_comun}"
                    "\n\n¿Vemos un ejemplo resuelto?")
        if intencion == "error":
            return f"Ojo con este error frecuente: {tema.error_comun}"
        if intencion == "ejemplo":
            return self._ejemplo(tema, estado)
        if intencion == "prueba":
            return self._iniciar_prueba(tema, estado)
        if intencion == "pista":
            return f"La clave de este tema: {tema.clave}"
        if intencion == "seguir":
            return self._ejemplo(tema, estado) if estado.indice_ejemplo == 0 else self._iniciar_prueba(tema, estado)
        return (f"No estoy seguro de haber entendido. En **{tema.titulo}** puedo explicarte el tema, mostrarte "
                "un ejemplo resuelto o hacerte una mini prueba de 3 preguntas. ¿Qué prefieres?")

    def _ejemplo(self, tema, estado) -> str:
        ejemplos = self.datos.ejemplos(tema.id)
        if not ejemplos:
            return f"La clave de este tema: {tema.clave}"
        ejemplo = ejemplos[estado.indice_ejemplo % len(ejemplos)]
        estado.indice_ejemplo += 1
        lineas = [f"Ejemplo: {ejemplo.enunciado}"]
        lineas += [f"{n}. {p.expresion}  ({p.nota})" for n, p in enumerate(ejemplo.pasos, start=1)]
        lineas.append(f"Resultado: **{ejemplo.resultado}**")
        if ejemplo.comprobacion:
            lineas.append(f"Comprobación: {ejemplo.comprobacion}")
        lineas.append("¿Otro ejemplo o una mini prueba?")
        return "\n".join(lineas)

    def _iniciar_prueba(self, tema, estado) -> str:
        preguntas = self.datos.preguntas(tema.id)
        elegidas = sorted(random.sample(preguntas, k=min(3, len(preguntas))), key=lambda p: p.orden)
        estado.sesion, estado.fallos = SesionPrueba(elegidas, self.corrector), 0
        return (f"¡Vamos! Mini prueba de {len(elegidas)} preguntas sobre {tema.titulo}. Si te equivocas, te doy "
                "una pista y otra oportunidad.\n\n" + self._texto_pregunta(estado.sesion))

    @staticmethod
    def _texto_pregunta(sesion: SesionPrueba) -> str:
        pregunta = sesion.actual
        lineas = [f"Pregunta {sesion.numero} de {sesion.total}: {pregunta.enunciado}"]
        if pregunta.es_alternativas:
            lineas += [f"{letra}) {alt}" for letra, alt in zip("abcd", pregunta.alternativas)]
            lineas.append("Responde con la letra.")
        return "\n".join(lineas)

    @staticmethod
    def _pista(estado) -> str:
        return f"Pista: {estado.sesion.pista()}\nInténtalo."

    def _corregir(self, estado, texto: str) -> str:
        sesion = estado.sesion
        pregunta = sesion.actual
        respuesta = texto
        coincidencia = re.fullmatch(r"\s*([a-dA-D])[).]?\s*", texto)
        if pregunta.es_alternativas and coincidencia:
            indice = "abcd".index(coincidencia.group(1).lower())
            if indice < len(pregunta.alternativas):
                respuesta = pregunta.alternativas[indice]
        correcta = self.corrector.es_correcta(pregunta, respuesta)
        if not correcta and estado.fallos == 0:
            estado.fallos = 1
            return f"Mmm, todavía no. Pista: {pregunta.pista}\nInténtalo otra vez."
        resultado = sesion.responder(respuesta)
        estado.fallos = 0
        if resultado.correcta:
            partes = [f"{random.choice(self.FELICITACIONES)} {pregunta.explicacion}"]
        else:
            partes = [f"La respuesta era {resultado.respuesta_correcta}. {pregunta.explicacion}"]
        if sesion.siguiente():
            partes.append(self._texto_pregunta(sesion))
        else:
            partes.append(f"Terminamos: {sesion.correctas} de {sesion.total} correctas. {sesion.mensaje_final()} "
                          "Para que cuente en tu progreso, rinde la prueba del tema en la pestaña Prueba.")
        return "\n\n".join(partes)

    # ------------------------------------------------------------------
    # Modo apoderado
    # ------------------------------------------------------------------
    def _responder_apoderado(self, contexto, texto: str) -> str:
        ficha = contexto.ficha
        if ficha is None:
            return "Aún no tengo datos de tu estudiante en este dispositivo. Ingresa con conexión para sincronizarlos."
        limpio = normalizar_texto(texto)
        if any(p in limpio for p in ("gracias", "genial")):
            return "¡De nada! Cualquier otra duda sobre su avance, aquí estoy."
        if any(p in limpio for p in ("apoy", "ayud", "casa", "actividad", "hacer")):
            return self._consejos(ficha)
        if any(p in limpio for p in ("reforz", "semana", "aprend", "estudi", "tema", "materia")):
            return self._refuerzos(ficha)
        if any(p in limpio for p in ("prueba", "evaluacion")):
            return self._evaluaciones(contexto)
        if any(p in limpio for p in ("nota", "promedio", "rendimiento", "como va", "asistencia", "resultado")):
            return self._rendimiento(contexto, ficha)
        if any(p in limpio for p in ("hola", "buenas")):
            return self.saludo(contexto)
        return (self._rendimiento(contexto, ficha) + "\n\n" + self._refuerzos(ficha)
                + "\n\nTambién puedo darte ideas para apoyar en casa.")

    @staticmethod
    def _consejos(ficha) -> str:
        nombre = ficha.estudiante.primer_nombre
        activos = [r for r in ficha.refuerzos_activos if r.tema]
        pendientes = [r for r in activos if r.estado != EstadoRefuerzo.LOGRADO] or activos
        if not pendientes:
            return (f"Por ahora {nombre} no tiene temas de refuerzo abiertos. Una buena rutina es conversar 10 "
                    "minutos al día sobre lo que vio en clases y pedirle que les explique un ejercicio: enseñar a "
                    "otro es una de las mejores formas de aprender.")
        lineas = [f"Ideas concretas para apoyar a {nombre} en casa:"]
        lineas += [f"**{r.tema.titulo}**: {r.tema.consejo_apoderado}" for r in pendientes[:2]]
        lineas.append("Con 10 a 15 minutos al día es suficiente; lo importante es la constancia y felicitar el "
                      "esfuerzo, no solo el resultado.")
        return "\n\n".join(lineas)

    @staticmethod
    def _refuerzos(ficha) -> str:
        nombre = ficha.estudiante.primer_nombre
        activos = [r for r in ficha.refuerzos_activos if r.tema]
        if not activos:
            return f"{nombre} no tiene temas de refuerzo desbloqueados por ahora."
        lineas = [f"La docente desbloqueó estos temas para {nombre}:"]
        for r in activos:
            mejor = ficha.mejor_intento(r.tema_id)
            detalle = f"mejor resultado {mejor.porcentaje} %" if mejor else "aún no rinde la prueba"
            lineas.append(f"- {r.tema.titulo}: {r.nombre_estado.lower()}, {detalle}.")
        pendientes = [r for r in activos if r.estado != EstadoRefuerzo.LOGRADO]
        if pendientes:
            lineas.append(f"\nConviene priorizar **{pendientes[0].tema.titulo}**. {pendientes[0].tema.resumen}")
        return "\n".join(lineas)

    @staticmethod
    def _rendimiento(contexto, ficha) -> str:
        nombre = ficha.estudiante.primer_nombre
        partes, bajos = [], []
        for asignatura_id in sorted({c.asignatura_id for c in ficha.calificaciones}):
            promedio = ficha.promedio(asignatura_id)
            nombre_asignatura = contexto.nombres_asignaturas.get(asignatura_id, asignatura_id)
            partes.append(f"{nombre_asignatura} {EscalaNotas.formatear(promedio)}")
            if promedio is not None and promedio < 5.0:
                bajos.append(nombre_asignatura)
        texto = (f"{nombre} tiene promedio general {EscalaNotas.formatear(ficha.promedio_general)} y "
                 f"{ficha.asistencia} % de asistencia. Por asignatura: {', '.join(partes)}.")
        if bajos:
            texto += f" Conviene poner atención a {', '.join(bajos)}."
        else:
            texto += " Va bien en todas sus asignaturas."
        return texto

    @staticmethod
    def _evaluaciones(contexto) -> str:
        evaluaciones = [a for a in contexto.avisos if a.tipo == "evaluacion"]
        if not evaluaciones:
            return "La docente no ha avisado evaluaciones en Tutor Educa. Si se publica una, aparecerá en Avisos."
        aviso = evaluaciones[0]
        return f"La docente avisó: **{aviso.titulo}**. {aviso.cuerpo}"
