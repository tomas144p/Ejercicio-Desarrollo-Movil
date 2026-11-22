"""
Calculadora de notas (tarea 19). Sirve a los tres perfiles y funciona sin internet; no guarda nada.

- Puntaje → nota, con la exigencia que se elija (60 % por defecto).
- ¿Cuántos puntos necesito para una nota?
- Tabla de puntaje a nota de toda la prueba (para mirar o copiar).
- ¿Qué nota necesito para llegar a un promedio?
- Solo docentes: planilla del curso (puntaje de cada estudiante → nota, para copiar).

Los cálculos están en ``services/calculadora_notas.py`` (Python puro, con pruebas).
"""

from __future__ import annotations

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stacklayout import StackLayout

from models.modelos import EscalaNotas, Rol
from services import calculadora_notas as calc
from views.componentes import (Boton, CajaNota, CampoTexto, Chip, Columna, Etiqueta, Fila, Superficie, Texto,
                               encabezado_seccion)
from views.base_screen import FondoPapel, PantallaBase, crear_desplazable
from views.dialogos import Dialogo
from views.estilo import Paleta, Tipografia, color
from views.navegacion import BarraSuperior

CENTRO = {"center_y": 0.5}
CARACTERES_NUMERICOS = set("0123456789,.")
CARACTERES_LISTA = CARACTERES_NUMERICOS | set(" ;\n")


def _filtro(permitidos: set[str]):
    return lambda texto, _deshacer: "".join(ch for ch in texto if ch in permitidos)


def _campo(sugerencia: str, texto: str, acento, al_cambiar, lista: bool = False) -> CampoTexto:
    """Campo para escribir números: teclado numérico y solo caracteres que sirven (coma, punto, dígitos)."""
    campo = CampoTexto(sugerencia, texto=texto, acento=acento)
    campo.entrada.input_filter = _filtro(CARACTERES_LISTA if lista else CARACTERES_NUMERICOS)
    if not lista:
        campo.entrada.input_type = "number"
    campo.entrada.bind(text=lambda *_: al_cambiar())
    return campo


def _pastillas(opciones: list[str], al_elegir, acento) -> StackLayout:
    caja = StackLayout(orientation="lr-tb", size_hint_y=None, spacing=dp(8))
    caja.bind(minimum_height=caja.setter("height"))
    for opcion in opciones:
        caja.add_widget(Chip(opcion, acento=acento, al_presionar=lambda o=opcion: al_elegir(o)))
    return caja


class PantallaCalculadora(PantallaBase):
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.curso_id = None
        self._dibujar_de_nuevo = True
        self._scroll = None
        raiz = FondoPapel()
        self._zona_superior = BoxLayout(size_hint_y=None, height=dp(64))
        self._zona_contenido = BoxLayout()
        raiz.add_widget(self._zona_superior)
        raiz.add_widget(self._zona_contenido)
        self.add_widget(raiz)

    def preparar(self, curso_id=None) -> None:
        """Cada vez que se entra por un botón se parte de cero (con los valores de siempre)."""
        self.curso_id = curso_id
        self._dibujar_de_nuevo = True

    def actualizar(self) -> None:
        # Una sincronización no debe borrar lo que la persona estaba escribiendo: solo se dibuja al entrar.
        if not self._dibujar_de_nuevo or self.app.usuario is None:
            return
        self._dibujar_de_nuevo = False
        self._zona_superior.clear_widgets()
        self._zona_superior.add_widget(BarraSuperior(self.app, "Calculadora de notas", "Sin internet · no guarda nada",
                                                     acento=self.acento, volver=True, mostrar_salir=False))
        self._zona_contenido.clear_widgets()
        self._scroll, c = crear_desplazable()
        self._contenido(c)
        self._zona_contenido.add_widget(self._scroll)

    # ------------------------------------------------------------------
    def _contenido(self, c) -> None:
        acento = self.acento
        # --- La prueba ---
        prueba = Superficie(spacing=dp(10))
        prueba.add_widget(Texto("La prueba", tamano=16, fuente=Tipografia.SEMI))
        self.c_maximo = _campo("Puntaje máximo", "60", acento, self._recalcular)
        self.c_exigencia = _campo("Exigencia (%)", "60", acento, self._recalcular)
        prueba.add_widget(self.c_maximo)
        prueba.add_widget(self.c_exigencia)
        prueba.add_widget(Texto("La exigencia es el porcentaje que hay que lograr para sacar un 4,0. Lo más común es 60 %.",
                                tamano=12.5, color_texto=Paleta.TINTA_SUAVE))
        prueba.add_widget(_pastillas(["50 %", "60 %", "70 %"], lambda o: self._poner(self.c_exigencia, o[:2]), acento))
        c.add_widget(prueba)

        # --- Puntaje → nota ---
        a_nota = Superficie(spacing=dp(10))
        a_nota.add_widget(Texto("De puntaje a nota", tamano=16, fuente=Tipografia.SEMI))
        self.c_obtenido = _campo("Puntaje obtenido", "", acento, self._recalcular)
        a_nota.add_widget(self.c_obtenido)
        self.r_nota = Texto("", tamano=30, fuente=Tipografia.SEMI)
        self.r_nota_texto = Texto("", tamano=13.5, color_texto=Paleta.TINTA_SUAVE)
        a_nota.add_widget(self.r_nota)
        a_nota.add_widget(self.r_nota_texto)
        c.add_widget(a_nota)

        # --- Nota → puntos ---
        a_puntos = Superficie(spacing=dp(10))
        a_puntos.add_widget(Texto("¿Cuántos puntos necesito?", tamano=16, fuente=Tipografia.SEMI))
        self.c_deseada = _campo("Nota que quiero", "4,0", acento, self._recalcular)
        a_puntos.add_widget(self.c_deseada)
        a_puntos.add_widget(_pastillas(["4,0", "5,0", "6,0", "7,0"], lambda o: self._poner(self.c_deseada, o), acento))
        self.r_puntos = Texto("", tamano=20, fuente=Tipografia.SEMI)
        self.r_puntos_texto = Texto("", tamano=13.5, color_texto=Paleta.TINTA_SUAVE)
        a_puntos.add_widget(self.r_puntos)
        a_puntos.add_widget(self.r_puntos_texto)
        a_puntos.add_widget(Boton("Ver la tabla de toda la prueba", icono="table", variante="contorno", acento=acento,
                                  alto=44, tamano=14, al_presionar=self._abrir_tabla))
        c.add_widget(a_puntos)

        # --- Promedio ---
        c.add_widget(encabezado_seccion("¿Qué nota necesito para promediar?",
                                        "Se supone que todas las evaluaciones valen lo mismo."))
        promedio = Superficie(spacing=dp(10))
        self.c_objetivo = _campo("Promedio que quiero", "5,0", acento, self._recalcular)
        self.c_notas = _campo("Notas que ya tengo (separadas por espacio)", "", acento, self._recalcular, lista=True)
        self.c_faltan = _campo("Evaluaciones que faltan", "1", acento, self._recalcular)
        for campo in (self.c_objetivo, self.c_notas, self.c_faltan):
            promedio.add_widget(campo)
        self.r_promedio = Texto("", tamano=20, fuente=Tipografia.SEMI)
        self.r_promedio_texto = Texto("", tamano=13.5, color_texto=Paleta.TINTA_SUAVE)
        promedio.add_widget(self.r_promedio)
        promedio.add_widget(self.r_promedio_texto)
        c.add_widget(promedio)

        # --- Planilla del curso (solo docentes) ---
        if self.app.usuario.rol == Rol.DOCENTE and self._curso() is not None:
            c.add_widget(encabezado_seccion("Notas de tu curso", f"{self._curso().nombre}"))
            planilla = Superficie(spacing=dp(10))
            planilla.add_widget(Texto("Escribe el puntaje de cada estudiante y ve su nota al instante. Usa el puntaje "
                                      "máximo y la exigencia de arriba.", tamano=13.5, color_texto=Paleta.TINTA_SUAVE))
            planilla.add_widget(Boton("Abrir la planilla del curso", icono="list", acento=acento, alto=46, tamano=14,
                                      al_presionar=self._abrir_planilla))
            planilla.add_widget(Texto("Estas notas todavía no se guardan en Tutor Educa: puedes copiarlas. El ingreso "
                                      "de notas con porcentajes llega con la tarea de notas manuales.", tamano=12,
                                      color_texto=Paleta.TINTA_TENUE))
            c.add_widget(planilla)
        self._recalcular()

    def _poner(self, campo: CampoTexto, valor: str) -> None:
        campo.texto = valor

    # ------------------------------------------------------------------
    # Cálculo en vivo
    # ------------------------------------------------------------------
    def _prueba(self) -> tuple[float, float]:
        maximo = calc.parsear_numero(self.c_maximo.texto, "El puntaje máximo")
        exigencia = calc.parsear_numero(self.c_exigencia.texto, "La exigencia")
        calc.validar_prueba(maximo, exigencia)
        return maximo, exigencia

    def _recalcular(self) -> None:
        if not hasattr(self, "r_promedio_texto"):
            return                                   # la pantalla todavía se está armando
        self._calcular_nota()
        self._calcular_puntos()
        self._calcular_promedio()

    @staticmethod
    def _mostrar(titulo: Texto, detalle: Texto, principal: str, secundario: str = "", tinta=Paleta.TINTA,
                 error: bool = False) -> None:
        titulo.cambiar(principal)
        titulo.color = color(Paleta.ROJO if error else tinta)
        detalle.cambiar(secundario)

    def _calcular_nota(self) -> None:
        if not self.c_obtenido.texto.strip():
            self._mostrar(self.r_nota, self.r_nota_texto, "", "Escribe el puntaje obtenido para ver la nota.")
            return
        try:
            maximo, exigencia = self._prueba()
            obtenido = calc.parsear_numero(self.c_obtenido.texto, "El puntaje obtenido")
            if obtenido < 0 or obtenido > maximo:
                raise calc.ErrorCalculo(f"El puntaje obtenido debe estar entre 0 y {calc.formato_puntaje(maximo)}.")
        except calc.ErrorCalculo as error:
            self._mostrar(self.r_nota, self.r_nota_texto, "", str(error), error=True)
            self.r_nota_texto.color = color(Paleta.ROJO)
            return
        nota = calc.nota_por_puntaje(maximo, obtenido, exigencia)
        categoria = EscalaNotas.categoria(nota)
        self._mostrar(self.r_nota, self.r_nota_texto, EscalaNotas.formatear(nota),
                      f"{calc.formato_puntaje(obtenido)} de {calc.formato_puntaje(maximo)} puntos "
                      f"({calc.formato_puntaje(round(obtenido / maximo * 100, 1))} %) · {EscalaNotas.MENSAJES[categoria]}",
                      Paleta.POR_CATEGORIA_NOTA[categoria][0])
        self.r_nota_texto.color = color(Paleta.TINTA_SUAVE)

    def _calcular_puntos(self) -> None:
        if not self.c_deseada.texto.strip():
            self._mostrar(self.r_puntos, self.r_puntos_texto, "", "Escribe la nota que quieres sacar.")
            return
        try:
            maximo, exigencia = self._prueba()
            deseada = calc.parsear_nota(self.c_deseada.texto, "La nota que quieres")
            puntos = calc.puntaje_para_nota(maximo, deseada, exigencia)
        except calc.ErrorCalculo as error:
            self._mostrar(self.r_puntos, self.r_puntos_texto, "", str(error), error=True)
            self.r_puntos_texto.color = color(Paleta.ROJO)
            return
        self.r_puntos_texto.color = color(Paleta.TINTA_SUAVE)
        if puntos is None:
            self._mostrar(self.r_puntos, self.r_puntos_texto, "No alcanza", "Ni con el puntaje máximo se llega a esa nota.",
                          error=True)
            return
        self._mostrar(self.r_puntos, self.r_puntos_texto,
                      f"{calc.formato_puntaje(puntos)} de {calc.formato_puntaje(maximo)} puntos",
                      f"Para sacar un {EscalaNotas.formatear(deseada)} necesitas el "
                      f"{calc.formato_puntaje(round(puntos / maximo * 100, 1))} % de la prueba.",
                      Paleta.POR_CATEGORIA_NOTA[EscalaNotas.categoria(deseada)][0])

    def _calcular_promedio(self) -> None:
        try:
            objetivo = calc.parsear_nota(self.c_objetivo.texto, "El promedio que quieres")
            notas = calc.parsear_notas(self.c_notas.texto)
            faltan = calc.parsear_numero(self.c_faltan.texto, "Las evaluaciones que faltan")
            if faltan < 1 or faltan != int(faltan) or faltan > 20:
                raise calc.ErrorCalculo("Las evaluaciones que faltan deben ser un número entero entre 1 y 20.")
            resultado = calc.nota_necesaria([(n, 1.0) for n in notas], float(faltan), objetivo)
        except calc.ErrorCalculo as error:
            self._mostrar(self.r_promedio, self.r_promedio_texto, "", str(error), error=True)
            self.r_promedio_texto.color = color(Paleta.ROJO)
            return
        self.r_promedio_texto.color = color(Paleta.TINTA_SUAVE)
        actual = f"Hoy tu promedio es {EscalaNotas.formatear(resultado.promedio_actual)}. " if notas else ""
        en_cada = " en cada una" if faltan > 1 else ""
        if resultado.estado == "ya_cumple":
            self._mostrar(self.r_promedio, self.r_promedio_texto, "¡Ya lo lograste!",
                          actual + f"Aunque saques un 1,0{en_cada}, igual llegas al {EscalaNotas.formatear(objetivo)}.",
                          Paleta.VERDE)
        elif resultado.estado == "imposible":
            self._mostrar(self.r_promedio, self.r_promedio_texto, "No alcanza",
                          actual + f"Aun sacando un 7,0{en_cada} llegarías como máximo a "
                          f"{EscalaNotas.formatear(resultado.mejor_promedio)}.", error=True)
        else:
            self._mostrar(self.r_promedio, self.r_promedio_texto,
                          f"Necesitas un {EscalaNotas.formatear(resultado.nota)}{en_cada}",
                          actual + f"Para promediar un {EscalaNotas.formatear(objetivo)}.",
                          Paleta.POR_CATEGORIA_NOTA[EscalaNotas.categoria(resultado.nota)][0])

    # ------------------------------------------------------------------
    # Tabla y planilla
    # ------------------------------------------------------------------
    def _copiar(self, texto: str, mensaje: str) -> None:
        from kivy.core.clipboard import Clipboard
        Clipboard.copy(texto)
        self.app.notificador.mostrar(mensaje, "exito")

    def _abrir_tabla(self) -> None:
        try:
            maximo, exigencia = self._prueba()
            tabla = calc.tabla_puntajes(maximo, exigencia)
        except calc.ErrorCalculo as error:
            self.app.notificador.mostrar(str(error), "error")
            return
        contenido = Columna(spacing=dp(4), padding=(0, 0, dp(14), 0))
        contenido.add_widget(Texto(f"{calc.formato_puntaje(maximo)} puntos · exigencia {calc.formato_puntaje(exigencia)} %",
                                   tamano=13, color_texto=Paleta.TINTA_SUAVE))
        for puntaje, nota in tabla:
            fila = Fila(spacing=dp(8), size_hint_y=None, height=dp(30))
            fila.add_widget(Texto(calc.etiqueta_puntos(puntaje), tamano=14, pos_hint=CENTRO))
            fila.add_widget(Texto(EscalaNotas.formatear(nota), tamano=14, fuente=Tipografia.SEMI, alinear="right",
                                  color_texto=Paleta.POR_CATEGORIA_NOTA[EscalaNotas.categoria(nota)][0], pos_hint=CENTRO))
            contenido.add_widget(fila)

        def copiar():
            self._copiar(calc.texto_tabla(maximo, exigencia), "Tabla copiada.")
            return False

        Dialogo("Tabla de notas", contenido=contenido, icono="table", tinta=self.acento,
                botones=[("Cerrar", None, "contorno"), ("Copiar", copiar, "primario", "copy")]).open()

    def _curso(self):
        cursos = self.app.datos.cursos_docente()
        return next((k for k in cursos if k.id == self.curso_id), cursos[0] if cursos else None)

    def _abrir_planilla(self) -> None:
        try:
            maximo, exigencia = self._prueba()
        except calc.ErrorCalculo as error:
            self.app.notificador.mostrar(str(error), "error")
            return
        curso = self._curso()
        fichas = sorted(self.app.datos.fichas_curso(curso.id), key=lambda f: f.estudiante.nombre.lower())
        filas: list[tuple[str, CampoTexto, Texto]] = []
        contenido = Columna(spacing=dp(6), padding=(0, 0, dp(14), 0))      # margen a la derecha: la barra no tapa la nota
        contenido.add_widget(Texto(f"{calc.formato_puntaje(maximo)} puntos · exigencia {calc.formato_puntaje(exigencia)} %",
                                   tamano=13, color_texto=Paleta.TINTA_SUAVE))

        def recalcular_fila(campo: CampoTexto, resultado: Texto) -> None:
            texto = campo.texto.strip()
            if not texto:
                resultado.cambiar("–")
                resultado.color = color(Paleta.TINTA_TENUE)
                return
            try:
                obtenido = calc.parsear_numero(texto)
                if obtenido < 0 or obtenido > maximo:
                    raise calc.ErrorCalculo("fuera de rango")
            except calc.ErrorCalculo:
                resultado.cambiar("¿?")
                resultado.color = color(Paleta.ROJO)
                return
            nota = calc.nota_por_puntaje(maximo, obtenido, exigencia)
            resultado.cambiar(EscalaNotas.formatear(nota))
            resultado.color = color(Paleta.POR_CATEGORIA_NOTA[EscalaNotas.categoria(nota)][0])

        for ficha in fichas:
            fila = Fila(spacing=dp(8))
            fila.add_widget(Texto(ficha.estudiante.nombre, tamano=14, fuente=Tipografia.MEDIA, pos_hint=CENTRO))
            campo = CampoTexto("Pts", acento=self.acento, size_hint_x=None, width=dp(84))
            campo.entrada.input_filter = _filtro(CARACTERES_NUMERICOS)
            campo.entrada.input_type = "number"
            resultado = Texto("–", tamano=16, fuente=Tipografia.SEMI, alinear="right", size_hint_x=None, width=dp(40),
                              color_texto=Paleta.TINTA_TENUE, pos_hint=CENTRO)
            campo.entrada.bind(text=lambda _i, _t, c=campo, r=resultado: recalcular_fila(c, r))
            fila.add_widget(campo)
            fila.add_widget(resultado)
            contenido.add_widget(fila)
            filas.append((ficha.estudiante.nombre, campo, resultado))

        def copiar():
            lineas = [f"{curso.nombre} · notas · {calc.formato_puntaje(maximo)} puntos · exigencia "
                      f"{calc.formato_puntaje(exigencia)} %"]
            for nombre, campo, _resultado in filas:
                if not campo.texto.strip():
                    continue
                try:
                    obtenido = calc.parsear_numero(campo.texto)
                    if not 0 <= obtenido <= maximo:
                        continue
                except calc.ErrorCalculo:
                    continue
                lineas.append(f"{nombre}: {calc.formato_puntaje(obtenido)} pts → "
                              f"{EscalaNotas.formatear(calc.nota_por_puntaje(maximo, obtenido, exigencia))}")
            if len(lineas) == 1:
                self.app.notificador.mostrar("Escribe al menos un puntaje.", "aviso")
                return False
            self._copiar("\n".join(lineas), "Notas copiadas.")
            return False

        Dialogo("Planilla del curso", contenido=contenido, icono="list", tinta=self.acento,
                botones=[("Cerrar", None, "contorno"), ("Copiar notas", copiar, "primario", "copy")]).open()
