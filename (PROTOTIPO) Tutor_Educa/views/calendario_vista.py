"""
Calendario escolar en pantalla (tareas 20 y 24): cuadrícula del mes, resumen de asistencia, eventos y los
diálogos para pasar lista y crear eventos.

- La familia y el estudiante ven el calendario DE UN ESTUDIANTE (modo «alumno»).
- La docente ve el calendario DEL CURSO (modo «curso»): en cada día, cuántos faltaron o si falta pasar lista.

Ningún estado se comunica solo con color: cada uno tiene también un ícono y una palabra (se lee con poca luz o
con poca visión del color). Las reglas (domingo, sábado, feriados) vienen de ``services.calendario``.
"""

from __future__ import annotations

from datetime import date

from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.stacklayout import StackLayout
from kivy.uix.widget import Widget

from services import calendario
from views.componentes import (TRANSPARENTE, Boton, BotonIcono, CajaNota, Casilla, Chip, CampoTexto, Columna, ConFondo,
                               Etiqueta, Fila, InsigniaIcono, Metrica, Superficie, Texto, encabezado_seccion)
from views.dialogos import Dialogo
from views.estilo import Iconos, Paleta, Tipografia, color

CENTRO = {"center_y": 0.5}
LETRAS_DIA = ("L", "M", "M", "J", "V", "S", "D")


def _en_filas(elementos: list) -> StackLayout:
    """Pastillas que se acomodan en varias líneas si no caben."""
    caja = StackLayout(orientation="lr-tb", size_hint_y=None, spacing=dp(8))
    caja.bind(minimum_height=caja.setter("height"))
    for elemento in elementos:
        caja.add_widget(elemento)
    return caja


# ======================================================================================================
# Cuadrícula del mes
# ======================================================================================================
class CeldaDia(ButtonBehavior, ConFondo, Label):
    """Un día del mes: número arriba y, abajo, el ícono de su estado."""

    def __init__(self, dia: date, texto: str, fondo, borde, tinta, grosor: float = 1, al_presionar=None, **kwargs):
        super().__init__(text=texto, markup=True, font_name=Tipografia.MEDIA, font_size=sp(13.5), color=color(tinta),
                         halign="center", valign="middle", size_hint=(1, None), height=dp(50), radio=dp(10),
                         color_fondo=color(fondo), color_borde=color(borde) if borde else TRANSPARENTE,
                         grosor_borde=dp(grosor), **kwargs)
        self.dia = dia
        self.bind(size=lambda *_: setattr(self, "text_size", self.size))
        if al_presionar:
            self.bind(on_release=lambda *_: al_presionar(dia))


class CalendarioMes(Columna):
    """
    Un mes con flechas para cambiar de mes. ``vista`` es una ``VistaCalendario``; ``modo`` es «alumno» o «curso».
    ``al_tocar_dia(dia)`` recibe el día tocado (por defecto muestra su detalle). ``al_cambiar_mes((año, mes))``
    permite a la pantalla recordar el mes que se estaba mirando.
    """

    def __init__(self, vista, hoy: date, modo: str = "alumno", acento=Paleta.MORA, al_tocar_dia=None,
                 mes: tuple[int, int] | None = None, al_cambiar_mes=None, **kwargs):
        super().__init__(spacing=dp(8), **kwargs)
        self.vista, self.hoy, self.modo, self.acento = vista, hoy, modo, acento
        self.al_tocar_dia = al_tocar_dia or self.mostrar_detalle
        self.al_cambiar_mes = al_cambiar_mes
        self.anio, self.mes = mes or (hoy.year, hoy.month)
        self._dibujar()

    # --- Navegación ---------------------------------------------------------------------------------
    def _mover(self, delta: int) -> None:
        self.anio, self.mes = calendario.mes_vecino(self.anio, self.mes, delta)
        if self.al_cambiar_mes:
            self.al_cambiar_mes((self.anio, self.mes))
        self._dibujar()

    def mostrar_detalle(self, dia: date) -> None:
        titulo, lineas = self.vista.describir(dia, self.hoy, self.modo)
        Dialogo(titulo, "\n\n".join(lineas), icono="calendar", tinta=self.acento,
                botones=[("Cerrar", None, "primario")]).open()

    # --- Estilo de cada día ---------------------------------------------------------------------------
    def estilo_dia(self, d: date) -> tuple[str, str | None, str, str, str, float]:
        """(fondo, borde, tinta, ícono, texto junto al ícono, grosor del borde). Separado para poder probarlo."""
        estado = self.vista.estado_dia(d)
        fondo, borde, tinta, icono, extra = Paleta.SUPERFICIE, Paleta.LINEA, Paleta.TINTA, "", ""
        if not estado.con_clases:
            fondo, borde, tinta = Paleta.GRIS_SUAVE, None, Paleta.TINTA_TENUE
            tipos = {e["tipo"] for e in estado.eventos if not int(e.get("hay_clases", 1))}
            if tipos:
                fondo, tinta = Paleta.AMBAR_SUAVE, Paleta.AMBAR
                icono = "flag" if "feriado" in tipos else "calendar-off"
        elif d <= self.hoy:
            marca = calendario.a_texto(d)
            if marca in self.vista.dias_con_lista:
                if self.modo == "alumno":
                    est = self.vista.estado_alumno(d)
                    fondo, tinta = {calendario.PRESENTE: (Paleta.VERDE_SUAVE, Paleta.VERDE),
                                    calendario.AUSENTE: (Paleta.ROJO_SUAVE, Paleta.ROJO),
                                    calendario.JUSTIFICADO: (Paleta.AMBAR_SUAVE, Paleta.AMBAR)}[est]
                    icono = calendario.ICONO_ESTADO[est]
                else:
                    faltaron = self.vista.ausencias_por_dia.get(marca, 0)
                    fondo, tinta = ((Paleta.VERDE_SUAVE, Paleta.VERDE) if not faltaron
                                    else (Paleta.ROJO_SUAVE, Paleta.ROJO))
                    icono, extra = ("check", "") if not faltaron else ("x", str(faltaron))
                borde = None
            elif self.modo == "curso":
                fondo, borde, tinta, icono = Paleta.AMBAR_SUAVE, Paleta.AMBAR, Paleta.AMBAR, "clipboard-list"
        if d == self.hoy:
            borde = self.acento
        grosor = 2.2 if d == self.hoy else 1
        return fondo, borde, tinta, icono, extra, grosor

    def _texto_celda(self, d: date, icono: str, extra: str) -> str:
        estado = self.vista.estado_dia(d)
        con_evento = any(int(e.get("hay_clases", 1)) for e in estado.eventos)
        linea = ""
        if icono:
            linea = Iconos.markup(icono, 13) + (f" {extra}" if extra else "")
        if con_evento:
            linea += ("  " if linea else "") + Iconos.markup("bookmark", 13)
        return f"{d.day}\n{linea}" if linea else f"{d.day}\n "

    # --- Dibujo --------------------------------------------------------------------------------------
    def _dibujar(self) -> None:
        self.clear_widgets()
        cabecera = Fila(spacing=dp(6), size_hint_y=None, height=dp(44))
        cabecera.add_widget(BotonIcono("chevron-left", al_presionar=lambda: self._mover(-1), lado=40,
                                       pos_hint=CENTRO))
        mes = calendario.NOMBRES_MES[self.mes - 1].capitalize()
        cabecera.add_widget(Texto(f"{mes} {self.anio}", tamano=16, fuente=Tipografia.SEMI, alinear="center",
                                  pos_hint=CENTRO))
        cabecera.add_widget(BotonIcono("chevron-right", al_presionar=lambda: self._mover(1), lado=40,
                                       pos_hint=CENTRO))
        self.add_widget(cabecera)

        letras = GridLayout(cols=7, spacing=dp(4), size_hint_y=None, height=dp(20))
        for letra in LETRAS_DIA:
            letras.add_widget(Texto(letra, tamano=12, fuente=Tipografia.MEDIA, color_texto=Paleta.TINTA_SUAVE,
                                    alinear="center"))
        self.add_widget(letras)

        cuadricula = GridLayout(cols=7, spacing=dp(4), size_hint_y=None)
        cuadricula.bind(minimum_height=cuadricula.setter("height"))
        for semana in calendario.semanas_del_mes(self.anio, self.mes):
            for d in semana:
                if d is None:
                    cuadricula.add_widget(Widget(size_hint=(1, None), height=dp(50)))
                    continue
                fondo, borde, tinta, icono, extra, grosor = self.estilo_dia(d)
                cuadricula.add_widget(CeldaDia(d, self._texto_celda(d, icono, extra), fondo, borde, tinta, grosor,
                                               al_presionar=self.al_tocar_dia))
        self.add_widget(cuadricula)
        self.add_widget(_en_filas(self._leyenda()))

    def _leyenda(self) -> list:
        if self.modo == "alumno":
            partes = [("Presente", Paleta.VERDE, "check"), ("Ausente", Paleta.ROJO, "x"),
                      ("Justificado", Paleta.AMBAR, "file-text")]
        else:
            partes = [("Todos presentes", Paleta.VERDE, "check"), ("Con ausentes", Paleta.ROJO, "x"),
                      ("Falta pasar lista", Paleta.AMBAR, "clipboard-list")]
        partes += [("Feriado o sin clases", Paleta.AMBAR, "flag"), ("Evento", self.acento, "bookmark")]
        return [Etiqueta(texto, tinta=tinta, icono=icono, tamano=11) for texto, tinta, icono in partes]


# ======================================================================================================
# Resumen de asistencia y lista de eventos
# ======================================================================================================
def tarjeta_asistencia(ficha, acento=Paleta.MORA) -> Superficie:
    """Porcentaje, días y alerta de inasistencias seguidas de UN estudiante."""
    resumen = ficha.resumen_asistencia
    tarjeta = Superficie(spacing=dp(10))
    tarjeta.add_widget(Texto("Asistencia", tamano=16, fuente=Tipografia.SEMI))
    if resumen is None or not resumen.hay_datos:
        tarjeta.add_widget(Texto(f"Todavía no se ha pasado lista en el curso. Mientras tanto se muestra el último "
                                 f"porcentaje informado por el colegio: {ficha.asistencia} %.",
                                 tamano=13.5, color_texto=Paleta.TINTA_SUAVE))
        return tarjeta
    fila = Fila()
    tinta = Paleta.VERDE if resumen.porcentaje >= 90 else (Paleta.AMBAR if resumen.porcentaje >= 85 else Paleta.ROJO)
    fila.add_widget(Metrica(f"{resumen.porcentaje} %", "Asistencia", tinta=tinta))
    fila.add_widget(Metrica(f"{resumen.presentes} de {resumen.dias}", "Días presente"))
    fila.add_widget(Metrica(str(resumen.inasistencias), "Inasistencias"))
    tarjeta.add_widget(fila)
    if resumen.justificados:
        tarjeta.add_widget(Texto(f"{resumen.justificados} de las inasistencias fue justificada. "
                                 "Igual cuenta en el porcentaje.", tamano=12.5, color_texto=Paleta.TINTA_SUAVE))
    if resumen.alerta_seguidas:
        tarjeta.add_widget(CajaNota("Inasistencias seguidas",
                                    f"{ficha.estudiante.primer_nombre} faltó los últimos {resumen.seguidas} días con "
                                    "clases. Conviene conversarlo con el colegio.", icono="triangle-alert",
                                    tinta=Paleta.ROJO))
    elif resumen.porcentaje < 85:
        tarjeta.add_widget(CajaNota("Bajo el 85 %", "La asistencia está bajo el 85 % que se pide para aprobar el año. "
                                    "Vale la pena conversarlo con el colegio.", icono="info", tinta=Paleta.AMBAR))
    return tarjeta


def lista_eventos(vista, hoy: date, acento=Paleta.MORA, titulo: str = "Próximos eventos", al_baja=None,
                  vacio: str = "No hay eventos próximos.") -> Columna:
    """Los próximos eventos. Si se pasa ``al_baja``, los de la docente muestran un tacho para darlos de baja."""
    columna = Columna(spacing=dp(8))
    columna.add_widget(encabezado_seccion(titulo))
    eventos = vista.eventos_proximos(hoy)
    if not eventos:
        columna.add_widget(Texto(vacio, tamano=13.5, color_texto=Paleta.TINTA_SUAVE))
        return columna
    for evento in eventos:
        tarjeta = Superficie(padding=dp(12), spacing=0)
        fila = Fila(spacing=dp(12))
        sin_clases = not int(evento.get("hay_clases", 1))
        tinta = Paleta.AMBAR if sin_clases else acento
        fila.add_widget(InsigniaIcono(calendario.ICONO_TIPO_EVENTO.get(evento["tipo"], "calendar"), tinta=tinta,
                                      lado=38, pos_hint=CENTRO))
        textos = Columna(spacing=dp(2), pos_hint=CENTRO)
        textos.add_widget(Texto(evento["titulo"], tamano=14.5, fuente=Tipografia.MEDIA))
        detalle = calendario.texto_rango(evento["fecha_inicio"], evento["fecha_fin"])
        detalle += " · No hay clases" if sin_clases else ""
        textos.add_widget(Texto(detalle, tamano=12.5, color_texto=Paleta.TINTA_SUAVE))
        if evento.get("descripcion"):
            textos.add_widget(Texto(evento["descripcion"], tamano=12.5, color_texto=Paleta.TINTA_SUAVE))
        fila.add_widget(textos)
        if al_baja is not None and evento.get("curso_id") is not None:
            fila.add_widget(BotonIcono("trash-2", al_presionar=lambda e=evento: al_baja(e), tinta=Paleta.ROJO,
                                       lado=38, tamano=18, pos_hint=CENTRO))
        tarjeta.add_widget(fila)
        columna.add_widget(tarjeta)
    return columna


# ======================================================================================================
# Pasar lista (docente)
# ======================================================================================================
SIGUIENTE_ESTADO = {calendario.PRESENTE: calendario.AUSENTE, calendario.AUSENTE: calendario.JUSTIFICADO,
                    calendario.JUSTIFICADO: calendario.PRESENTE}
ESTILO_ESTADO = {calendario.PRESENTE: (Paleta.VERDE, "check"), calendario.AUSENTE: (Paleta.ROJO, "x"),
                 calendario.JUSTIFICADO: (Paleta.AMBAR, "file-text")}


class FilaAsistencia(ButtonBehavior, ConFondo, BoxLayout):
    """Un estudiante en la lista: un toque cambia presente → ausente → justificado → presente."""

    def __init__(self, nombre: str, estado: str, al_cambiar=None, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(52), padding=(dp(12), 0),
                         spacing=dp(10), radio=dp(12), **kwargs)
        self.estado, self._al_cambiar = estado, al_cambiar
        self.add_widget(Texto(nombre, tamano=14.5, fuente=Tipografia.MEDIA, pos_hint=CENTRO))
        self._pastilla = None
        self._pintar()

    def _pintar(self) -> None:
        tinta, icono = ESTILO_ESTADO[self.estado]
        if self._pastilla is not None:
            self.remove_widget(self._pastilla)
        self._pastilla = Etiqueta(calendario.NOMBRES_ESTADO[self.estado], tinta=tinta, icono=icono, tamano=12)
        self._pastilla.pos_hint = CENTRO
        self.add_widget(self._pastilla)
        self.color_fondo = color(Paleta.suave(tinta)) if self.estado != calendario.PRESENTE else color(Paleta.SUPERFICIE)
        self.color_borde = color(Paleta.LINEA) if self.estado == calendario.PRESENTE else TRANSPARENTE

    def on_release(self) -> None:
        self.estado = SIGUIENTE_ESTADO[self.estado]
        self._pintar()
        if self._al_cambiar:
            self._al_cambiar()


def abrir_lista_del_dia(app, curso, dia: str, al_guardar=None) -> None:
    """Ventana para pasar (o corregir) la lista de un día. Todos parten presentes: solo se marca a quien faltó."""
    datos = app.datos
    ya_pasada, estados = datos.lista_del_dia(curso.id, dia)
    nombres = {f.estudiante.id: f.estudiante.nombre for f in datos.fichas_curso(curso.id)}
    contenido = Columna(spacing=dp(8))
    contenido.add_widget(Texto("Todos aparecen presentes. Toca a quien faltó: una vez = ausente, dos veces = "
                               "ausente justificado, tres = vuelve a presente.", tamano=13,
                               color_texto=Paleta.TINTA_SUAVE))
    resumen = Texto("", tamano=13.5, fuente=Tipografia.SEMI, color_texto=Paleta.TINTA)
    filas: dict[int, FilaAsistencia] = {}

    def recalcular() -> None:
        ausentes = sum(1 for f in filas.values() if f.estado == calendario.AUSENTE)
        justificados = sum(1 for f in filas.values() if f.estado == calendario.JUSTIFICADO)
        presentes = len(filas) - ausentes - justificados
        resumen.cambiar(f"{presentes} presentes · {ausentes} ausentes · {justificados} justificados")

    for estudiante_id in sorted(nombres, key=lambda i: nombres[i].lower()):
        fila = FilaAsistencia(nombres[estudiante_id], estados.get(estudiante_id, calendario.PRESENTE),
                              al_cambiar=recalcular)
        filas[estudiante_id] = fila
        contenido.add_widget(fila)
    contenido.add_widget(resumen)
    recalcular()

    def guardar():
        ausentes = [i for i, f in filas.items() if f.estado == calendario.AUSENTE]
        justificados = [i for i, f in filas.items() if f.estado == calendario.JUSTIFICADO]
        error = datos.pasar_lista(curso.id, dia, ausentes, justificados)
        if error:
            app.notificador.mostrar(error, "error")
            return False
        app.notificador.mostrar("Lista guardada.", "exito")
        if al_guardar:
            al_guardar()
        return None

    titulo = ("Corregir la lista" if ya_pasada else "Pasar lista") + f" · {calendario.fecha_legible(dia, False)}"
    Dialogo(titulo, contenido=contenido, icono="clipboard-check", tinta=Paleta.PIZARRA,
            botones=[("Cancelar", None, "contorno"), ("Guardar lista", guardar, "primario", "check")]).open()


# ======================================================================================================
# Crear un evento (docente)
# ======================================================================================================
def abrir_evento_nuevo(app, curso, dia: date | None = None, al_guardar=None) -> None:
    """Formulario de un evento de UN curso. Los de todo el colegio (feriados) los carga la administración."""
    sugerido = calendario.a_texto_chileno(dia or app.datos.hoy())
    estado = {"tipo": "evaluacion"}
    campo_titulo = CampoTexto("Título (por ejemplo: Prueba de ecuaciones)", acento=Paleta.PIZARRA)
    campo_desde = CampoTexto("Desde (DD/MM/AAAA)", texto=sugerido, acento=Paleta.PIZARRA)
    campo_hasta = CampoTexto("Hasta (opcional, si dura varios días)", acento=Paleta.PIZARRA)
    campo_detalle = CampoTexto("Detalle (opcional)", multilinea=True, alto=72, acento=Paleta.PIZARRA)
    sin_clases = Casilla("Ese día no hay clases", activa=False, acento=Paleta.PIZARRA)
    error = Texto("", tamano=13.5, color_texto=Paleta.ROJO)
    chips: dict[str, Chip] = {}

    def elegir(tipo: str) -> None:
        estado["tipo"] = tipo
        for clave, chip in chips.items():
            chip.seleccionado = clave == tipo
        if tipo in ("feriado", "sin_clases"):
            sin_clases.activa = True
        elif tipo in ("evaluacion", "reunion", "celebracion", "otro"):
            sin_clases.activa = False

    for clave, (nombre, _) in calendario.TIPOS_EVENTO.items():
        chips[clave] = Chip(nombre, seleccionado=clave == estado["tipo"], acento=Paleta.PIZARRA,
                            icono=calendario.ICONO_TIPO_EVENTO[clave], al_presionar=lambda c=clave: elegir(c))

    contenido = Columna(spacing=dp(10))
    contenido.add_widget(Texto(f"Para {curso.nombre}. Las familias lo ven en su calendario.", tamano=13,
                               color_texto=Paleta.TINTA_SUAVE))
    contenido.add_widget(campo_titulo)
    contenido.add_widget(_en_filas(list(chips.values())))
    for widget in (campo_desde, campo_hasta, campo_detalle, sin_clases, error):
        contenido.add_widget(widget)

    def guardar():
        try:
            inicio = calendario.desde_texto_chileno(campo_desde.texto)
            fin = calendario.desde_texto_chileno(campo_hasta.texto) if campo_hasta.texto.strip() else inicio
        except ValueError as problema:
            error.cambiar(str(problema))
            return False
        mensaje = app.datos.crear_evento(curso.id, campo_titulo.texto, estado["tipo"], inicio, fin,
                                         campo_detalle.texto, hay_clases=not sin_clases.activa)
        if mensaje:
            error.cambiar(mensaje)
            return False
        app.notificador.mostrar("Evento guardado.", "exito")
        if al_guardar:
            al_guardar()
        return None

    Dialogo("Nuevo evento", contenido=contenido, icono="calendar-plus", tinta=Paleta.PIZARRA,
            botones=[("Cancelar", None, "contorno"), ("Guardar", guardar, "primario", "check")]).open()
