"""
Pantalla principal del docente.

Pestañas:
- Mi curso: estudiantes con su promedio de Matemáticas y quiénes necesitan refuerzo.
- Temas: desbloquear materia para un grupo (los que necesitan refuerzo o todo el curso).
- Avisos: escribir mensajes a los apoderados y ver quién los leyó.

Para desbloquear temas a un estudiante en particular se toca su nombre
(abre su ficha).
"""

from __future__ import annotations

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stacklayout import StackLayout

from ...modelos import Aviso, EscalaNotas, EstadoRefuerzo, promedio
from ..componentes import (Avatar, Boton, CampoTexto, Chip, Columna, EstadoVacio, Etiqueta, Fila, FilaLista,
                           InsigniaIcono, Metrica, Separador, Superficie, TarjetaTocable, Texto,
                           encabezado_seccion, insignia_nota)
from ..dialogos import Dialogo
from ..estilo import FormatoTexto, Paleta, Tipografia
from .base import PantallaConPestanas

CENTRO = {"center_y": 0.5}
TIPOS_AVISO = [("info", "Información"), ("evaluacion", "Evaluación"), ("refuerzo", "Refuerzo"), ("logro", "Logro")]


def tiene_tema(ficha, tema_id: str) -> bool:
    return any(r.tema_id == tema_id and r.activo for r in ficha.refuerzos)


class PantallaDocente(PantallaConPestanas):
    PESTANAS = [("curso", "Mi curso", "users"), ("temas", "Temas", "book-open"), ("avisos", "Avisos", "megaphone")]
    ACENTO = Paleta.PIZARRA

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.curso = None
        self.fichas = []
        self.filtro = "todos"
        self._borrador = {"titulo": "", "cuerpo": "", "tipo": "info", "destinatario": None}

    def reiniciar(self) -> None:
        super().reiniciar()
        self.filtro = "todos"
        self._borrador = {"titulo": "", "cuerpo": "", "tipo": "info", "destinatario": None}

    def actualizar(self) -> None:
        if self.app.usuario is None:
            return
        cursos = self.app.datos.cursos_docente()
        self.curso = cursos[0] if cursos else None
        self.fichas = self.app.datos.fichas_curso(self.curso.id) if self.curso else []
        super().actualizar()

    def titulo(self) -> str:
        return f"Hola, {self.app.usuario.primer_nombre}"

    def subtitulo(self) -> str:
        return f"Docente de {self.curso.nombre}" if self.curso else "Docente"

    def _sin_curso(self, c) -> bool:
        if self.curso is None:
            c.add_widget(EstadoVacio("users", "No hay cursos en este dispositivo",
                                     "Ingresa con conexión para descargar tus cursos.", tinta=self.ACENTO))
            return True
        return False

    # ------------------------------------------------------------------
    # Mi curso
    # ------------------------------------------------------------------
    def pestana_curso(self, c) -> None:
        if self._sin_curso(c):
            return
        promedios = [p for p in (f.promedio("mat") for f in self.fichas) if p is not None]
        promedio_curso = promedio(promedios)
        necesitan = [f for f in self.fichas if f.necesita_refuerzo]
        logrados = sum(1 for f in self.fichas for r in f.refuerzos_activos if r.estado == EstadoRefuerzo.LOGRADO)

        resumen = Superficie()
        fila = Fila()
        tinta = Paleta.POR_CATEGORIA_NOTA[EscalaNotas.categoria(promedio_curso)][0]
        fila.add_widget(Metrica(EscalaNotas.formatear(promedio_curso), "Promedio de Matemáticas", tinta=tinta))
        fila.add_widget(Metrica(str(len(necesitan)), "Bajo 5,0 en Matemáticas",
                                tinta=Paleta.ROJO if necesitan else Paleta.TINTA))
        fila.add_widget(Metrica(str(logrados), "Temas logrados", tinta=Paleta.VERDE))
        resumen.add_widget(fila)
        c.add_widget(resumen)

        filtros = StackLayout(orientation="lr-tb", size_hint_y=None, spacing=dp(8))
        filtros.bind(minimum_height=filtros.setter("height"))
        filtros.add_widget(Chip(f"Todos ({len(self.fichas)})", seleccionado=self.filtro == "todos",
                                acento=self.ACENTO, al_presionar=lambda: self._filtrar("todos")))
        filtros.add_widget(Chip(f"Necesitan refuerzo ({len(necesitan)})", seleccionado=self.filtro == "refuerzo",
                                acento=self.ACENTO, icono="triangle-alert",
                                al_presionar=lambda: self._filtrar("refuerzo")))
        c.add_widget(filtros)

        mostradas = necesitan if self.filtro == "refuerzo" else self.fichas
        lista = Superficie(padding=(dp(16), dp(4)), spacing=0)
        for indice, ficha in enumerate(mostradas):
            activos = [r for r in ficha.refuerzos_activos if r.tema]
            if activos:
                detalle = "Refuerzo: " + ", ".join(f"{r.tema.titulo.split(':')[0]} ({r.nombre_estado.lower()})"
                                                    for r in activos[:2])
                if len(activos) > 2:
                    detalle += f" y {len(activos) - 2} más"
            else:
                detalle = "Sin temas desbloqueados"
            if indice:
                lista.add_widget(Separador())
            lista.add_widget(FilaLista(ficha.estudiante.nombre, detalle,
                                       inicio=Avatar(ficha.estudiante.iniciales, tinta=self.ACENTO, lado=40),
                                       fin=insignia_nota(ficha.promedio("mat")),
                                       al_presionar=lambda e=ficha.estudiante.id: self.app.ir_a("ficha", estudiante_id=e)))
        if not mostradas:
            lista.add_widget(EstadoVacio("circle-check", "Nadie necesita refuerzo", "Todo el curso tiene "
                                         "promedio 5,0 o más en Matemáticas.", tinta=Paleta.VERDE))
        c.add_widget(lista)
        c.add_widget(Texto("El número es el promedio de Matemáticas. Bajo 5,0 se sugiere reforzar. Toca a un "
                           "estudiante para ver su ficha y desbloquearle temas.", tamano=12,
                           color_texto=Paleta.TINTA_TENUE))

    def _filtrar(self, filtro: str) -> None:
        self.filtro = filtro
        self.dibujar_pestana(conservar_posicion=True)

    # ------------------------------------------------------------------
    # Temas
    # ------------------------------------------------------------------
    def pestana_temas(self, c) -> None:
        if self._sin_curso(c):
            return
        c.add_widget(Texto("Desbloquea la materia que quieres reforzar. Tus estudiantes podrán leerla y "
                           "practicar incluso sin internet.", tamano=13.5, color_texto=Paleta.TINTA_SUAVE))
        for tema in self.app.datos.temas():
            con_tema = [f for f in self.fichas if tiene_tema(f, tema.id)]
            logrados = [f for f in con_tema if any(r.tema_id == tema.id and r.activo and
                                                   r.estado == EstadoRefuerzo.LOGRADO for r in f.refuerzos)]
            tarjeta = Superficie(spacing=dp(12))
            cabecera = Fila(spacing=dp(12))
            cabecera.add_widget(InsigniaIcono(tema.icono, tinta=self.ACENTO, lado=44, pos_hint=CENTRO))
            textos = Columna(spacing=dp(2), pos_hint=CENTRO)
            textos.add_widget(Texto(tema.titulo, tamano=15.5, fuente=Tipografia.SEMI))
            textos.add_widget(Texto(tema.nivel, tamano=12.5, color_texto=Paleta.TINTA_SUAVE))
            cabecera.add_widget(textos)
            tarjeta.add_widget(cabecera)
            if con_tema:
                n = len(con_tema)
                estado = f"Desbloqueado para {n} {'estudiante' if n == 1 else 'estudiantes'}"
                if logrados:
                    estado += f"; {len(logrados)} ya {'lo logró' if len(logrados) == 1 else 'lo lograron'}"
            else:
                estado = "Aún no se ha desbloqueado"
            tarjeta.add_widget(Texto(estado + ".", tamano=13, color_texto=Paleta.TINTA_SUAVE))
            botones = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
            botones.add_widget(Boton("Vista previa", icono="eye", variante="contorno", acento=self.ACENTO, alto=44,
                                     tamano=14, al_presionar=lambda t=tema.id: self.app.abrir_leccion(t, vista_previa=True)))
            botones.add_widget(Boton("Desbloquear", icono="lock-open", acento=self.ACENTO, alto=44, tamano=14,
                                     al_presionar=lambda t=tema: self._dialogo_desbloqueo(t)))
            tarjeta.add_widget(botones)
            c.add_widget(tarjeta)

    def _dialogo_desbloqueo(self, tema) -> None:
        necesitan = [f for f in self.fichas if f.necesita_refuerzo and not tiene_tema(f, tema.id)]
        todos = [f for f in self.fichas if not tiene_tema(f, tema.id)]
        eleccion = {"grupo": "necesitan" if necesitan else "todos"}
        contenido = Columna(spacing=dp(12))
        opciones = StackLayout(orientation="lr-tb", size_hint_y=None, spacing=dp(8))
        opciones.bind(minimum_height=opciones.setter("height"))
        chip_necesitan = Chip(f"Necesitan refuerzo ({len(necesitan)})", acento=self.ACENTO)
        chip_todos = Chip(f"Todo el curso ({len(todos)})", acento=self.ACENTO)
        detalle = Texto("", tamano=13, color_texto=Paleta.TINTA_SUAVE)

        def elegir(grupo):
            eleccion["grupo"] = grupo
            chip_necesitan.seleccionado = grupo == "necesitan"
            chip_todos.seleccionado = grupo == "todos"
            lista = necesitan if grupo == "necesitan" else todos
            nombres = ", ".join(f.estudiante.nombre for f in lista)
            detalle.cambiar(f"Lo recibirán: {nombres}." if lista else "Todos los de este grupo ya tienen el tema.")

        chip_necesitan.bind(on_release=lambda *_: elegir("necesitan"))
        chip_todos.bind(on_release=lambda *_: elegir("todos"))
        opciones.add_widget(chip_necesitan)
        opciones.add_widget(chip_todos)
        contenido.add_widget(opciones)
        contenido.add_widget(detalle)
        campo = CampoTexto("Mensaje opcional para tus estudiantes", multilinea=True, alto=90, acento=self.ACENTO)
        contenido.add_widget(campo)
        elegir(eleccion["grupo"])

        def confirmar():
            grupo = necesitan if eleccion["grupo"] == "necesitan" else todos
            if not grupo:
                self.app.notificador.mostrar("Todos los estudiantes de ese grupo ya tienen este tema.")
                return False
            cantidad = self.app.datos.desbloquear_varios([f.estudiante.id for f in grupo], tema.id, campo.texto.strip())
            self.app.notificador.mostrar(f"{tema.titulo}: desbloqueado para {cantidad} "
                                         f"{'estudiante' if cantidad == 1 else 'estudiantes'}.", "exito")
            self.actualizar()
            return True

        Dialogo(f"Desbloquear {tema.titulo}", "¿Para quiénes quieres desbloquear este tema?", contenido=contenido,
                icono="lock-open", tinta=self.ACENTO,
                botones=[("Cancelar", None, "contorno"), ("Desbloquear", confirmar, "primario")]).open()

    # ------------------------------------------------------------------
    # Avisos
    # ------------------------------------------------------------------
    def pestana_avisos(self, c) -> None:
        if self._sin_curso(c):
            return
        borrador = self._borrador
        redactar = Superficie(spacing=dp(12))
        redactar.add_widget(Texto("Nuevo aviso para apoderados", tamano=16, fuente=Tipografia.SEMI))

        destino = Fila()
        nombre_destino = self._nombre_destinatario(borrador["destinatario"])
        destino.add_widget(Texto(f"Para: {nombre_destino}", tamano=13.5, fuente=Tipografia.MEDIA, pos_hint=CENTRO))
        destino.add_widget(Boton("Cambiar", variante="fantasma", acento=self.ACENTO, alto=34, tamano=13,
                                 size_hint_x=None, width=dp(96), al_presionar=self._elegir_destinatario,
                                 pos_hint=CENTRO))
        redactar.add_widget(destino)

        tipos = StackLayout(orientation="lr-tb", size_hint_y=None, spacing=dp(8))
        tipos.bind(minimum_height=tipos.setter("height"))
        for clave, nombre in TIPOS_AVISO:
            tipos.add_widget(Chip(nombre, seleccionado=borrador["tipo"] == clave, acento=self.ACENTO,
                                  al_presionar=lambda k=clave: self._cambiar_tipo(k)))
        redactar.add_widget(tipos)

        self.campo_titulo = CampoTexto("Título del aviso", texto=borrador["titulo"], acento=self.ACENTO)
        self.campo_cuerpo = CampoTexto("Escribe el mensaje para las familias…", multilinea=True, alto=120,
                                       texto=borrador["cuerpo"], acento=self.ACENTO)
        self.campo_titulo.entrada.bind(text=lambda _w, v: borrador.__setitem__("titulo", v))
        self.campo_cuerpo.entrada.bind(text=lambda _w, v: borrador.__setitem__("cuerpo", v))
        redactar.add_widget(self.campo_titulo)
        redactar.add_widget(self.campo_cuerpo)
        redactar.add_widget(Boton("Enviar aviso", icono="send", acento=self.ACENTO, al_presionar=self._enviar_aviso))
        c.add_widget(redactar)

        c.add_widget(encabezado_seccion("Avisos enviados"))
        avisos = self.app.datos.avisos_curso(self.curso.id)
        if not avisos:
            c.add_widget(EstadoVacio("megaphone", "Aún no hay avisos", "Los avisos que envíes aparecerán aquí.",
                                     tinta=self.ACENTO))
        con_apoderado = {f.estudiante.id for f in self.fichas if f.apoderado_nombre}
        for aviso in avisos:
            c.add_widget(self._tarjeta_aviso(aviso, con_apoderado))

    def _tarjeta_aviso(self, aviso: Aviso, con_apoderado: set) -> TarjetaTocable:
        tinta, fondo, icono, nombre_tipo = Paleta.POR_TIPO_AVISO.get(aviso.tipo, Paleta.POR_TIPO_AVISO["info"])
        tarjeta = TarjetaTocable(spacing=dp(8), al_presionar=lambda: Dialogo.informar(aviso.titulo, aviso.cuerpo,
                                                                                      icono=icono, tinta=tinta))
        cabecera = Fila()
        cabecera.add_widget(Etiqueta(nombre_tipo, tinta=tinta, fondo=fondo, icono=icono, pos_hint=CENTRO))
        cabecera.add_widget(Texto(FormatoTexto.fecha_relativa(aviso.creado_en), tamano=12,
                                  color_texto=Paleta.TINTA_TENUE, alinear="right", pos_hint=CENTRO))
        tarjeta.add_widget(cabecera)
        tarjeta.add_widget(Texto(aviso.titulo, tamano=15, fuente=Tipografia.SEMI))
        destinatarios = 1 if aviso.estudiante_id else len(con_apoderado)
        if aviso.pendiente:
            estado, color_estado = "Pendiente de envío: se enviará cuando vuelva la conexión.", Paleta.AMBAR
        else:
            estado = f"Leído por {aviso.lectores} de {destinatarios} {'apoderado' if destinatarios == 1 else 'apoderados'}."
            color_estado = Paleta.TINTA_SUAVE
        tarjeta.add_widget(Texto(f"Para: {self._nombre_destinatario(aviso.estudiante_id)}. {estado}", tamano=12.5,
                                 color_texto=color_estado))
        return tarjeta

    def _nombre_destinatario(self, estudiante_id) -> str:
        if not estudiante_id:
            return "todo el curso"
        ficha = next((f for f in self.fichas if f.estudiante.id == estudiante_id), None)
        return f"familia de {ficha.estudiante.nombre}" if ficha else "un estudiante"

    def _cambiar_tipo(self, tipo: str) -> None:
        self._borrador["tipo"] = tipo
        self.dibujar_pestana(conservar_posicion=True)

    def _elegir_destinatario(self) -> None:
        contenido = Columna(spacing=0)
        dialogo = None

        def elegir(estudiante_id):
            self._borrador["destinatario"] = estudiante_id
            dialogo.dismiss()
            self.dibujar_pestana(conservar_posicion=True)

        contenido.add_widget(FilaLista("Todo el curso", "Lo reciben todas las familias",
                                       inicio=InsigniaIcono("users", tinta=self.ACENTO, lado=38),
                                       al_presionar=lambda: elegir(None)))
        for ficha in self.fichas:
            if not ficha.apoderado_nombre:
                continue
            contenido.add_widget(Separador())
            contenido.add_widget(FilaLista(ficha.estudiante.nombre, f"Apoderado/a: {ficha.apoderado_nombre}",
                                           inicio=Avatar(ficha.estudiante.iniciales, tinta=self.ACENTO, lado=38),
                                           al_presionar=lambda e=ficha.estudiante.id: elegir(e)))
        dialogo = Dialogo("¿Para quién es el aviso?", "Solo aparecen los estudiantes con apoderado registrado.",
                          contenido=contenido, icono="users", tinta=self.ACENTO, botones=[("Cancelar", None, "contorno")])
        dialogo.open()

    def _enviar_aviso(self) -> None:
        titulo, cuerpo = self.campo_titulo.texto.strip(), self.campo_cuerpo.texto.strip()
        if len(titulo) < 3 or len(cuerpo) < 5:
            self.app.notificador.mostrar("Escribe un título y un mensaje antes de enviar.", "error")
            return
        borrador = self._borrador
        aviso = Aviso.nuevo(self.curso.id, self.app.usuario.id, titulo, cuerpo,
                            estudiante_id=borrador["destinatario"], tipo=borrador["tipo"])
        self.app.datos.publicar_aviso(aviso)
        self._borrador = {"titulo": "", "cuerpo": "", "tipo": "info", "destinatario": None}
        if self.app.en_linea:
            self.app.notificador.mostrar("Aviso enviado a las familias.", "exito")
        else:
            self.app.notificador.mostrar("Aviso guardado: se enviará cuando vuelva la conexión.", "aviso")
        self.actualizar()
