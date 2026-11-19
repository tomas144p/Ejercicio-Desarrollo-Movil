"""
Servicio de datos para las pantallas (patrón "fachada").

Las pantallas no escriben SQL: le piden todo a ``ServicioDatos``. Este
servicio lee siempre de la base LOCAL (así la app funciona igual con o sin
conexión) y, cuando el usuario cambia algo, lo guarda localmente y lo deja
en la cola de sincronización para enviarlo al servidor.
"""

from __future__ import annotations

from typing import Callable

from services.acciones_docente import avisos_sin_confirmar
from services.cursos import ResumenCurso
from services.graficos import grafico_progreso
from services.metricas import Metricas, ResumenEfecto, a_csv, calcular_metricas, resumen_curso, semestre_actual
from models.modelos import (Asignatura, Aviso, Curso, Estudiante, EstadoRefuerzo, FichaEstudiante, Intento,
                        Tema, ahora_iso)

# Orden en que se muestran los refuerzos: primero lo que está en curso.
ORDEN_ESTADOS = {EstadoRefuerzo.EN_PROGRESO: 0, EstadoRefuerzo.DISPONIBLE: 1, EstadoRefuerzo.LOGRADO: 2}


class ServicioDatos:
    def __init__(self, local, al_haber_cambios: Callable | None = None, almacen=None):
        self.local = local
        self.error_grafico = ""
        self.almacen = almacen            # AlmacenIntentos (JSON); puede ser None en las pruebas
        self.usuario = None
        self._al_haber_cambios = al_haber_cambios
        self._temas: dict[str, Tema] | None = None
        self._asignaturas: list[Asignatura] | None = None

    # --- Sesión -------------------------------------------------------------
    def iniciar_sesion(self, usuario) -> None:
        self.usuario = usuario
        self.invalidar()

    def cerrar_sesion(self) -> None:
        self.usuario = None
        self.invalidar()

    def colegio_nombre(self) -> str:
        """Nombre del colegio de quien tiene la sesión abierta ("" si todavía no se ha descargado)."""
        if self.usuario is None:
            return ""
        colegio_id = self.usuario.colegio_id
        if colegio_id is None:      # ingreso sin conexión: el colegio quedó guardado con los datos descargados
            fila = self.local.usuario_por_id(self.usuario.id)
            colegio_id = fila.get("colegio_id") if fila else None
        fila = self.local.colegio(int(colegio_id)) if colegio_id is not None else None
        return fila["nombre"] if fila else ""

    def invalidar(self) -> None:
        """Olvida lo guardado en memoria (se llama después de sincronizar)."""
        self._temas = None
        self._asignaturas = None

    # --- Contenido ----------------------------------------------------------
    def asignaturas(self) -> list[Asignatura]:
        if self._asignaturas is None:
            self._asignaturas = self.local.asignaturas()
        return self._asignaturas

    def asignatura(self, asignatura_id: str) -> Asignatura | None:
        return next((a for a in self.asignaturas() if a.id == asignatura_id), None)

    def temas(self) -> list[Tema]:
        if self._temas is None:
            self._temas = {t.id: t for t in self.local.temas("mat")}
        return sorted(self._temas.values(), key=lambda t: t.orden)

    def tema(self, tema_id: str) -> Tema | None:
        self.temas()
        return self._temas.get(tema_id)

    def ejemplos(self, tema_id: str):
        return self.local.ejemplos(tema_id)

    def preguntas(self, tema_id: str):
        return self.local.preguntas(tema_id)

    # --- Fichas de estudiantes ---------------------------------------------
    def _fichas(self, filas: list[dict]) -> list[FichaEstudiante]:
        ids = [int(f["id"]) for f in filas]
        calificaciones = self.local.calificaciones(ids)
        refuerzos = self.local.refuerzos(ids, solo_activos=False)
        intentos = self.local.intentos(ids)
        for refuerzo in refuerzos:
            refuerzo.tema = self.tema(refuerzo.tema_id)
        refuerzos.sort(key=lambda r: (ORDEN_ESTADOS.get(r.estado, 9), r.tema.orden if r.tema else 99))
        cursos: dict[int, Curso | None] = {}
        fichas = []
        for fila in filas:
            eid, curso_id = int(fila["id"]), int(fila["curso_id"])
            if curso_id not in cursos:
                cursos[curso_id] = self.local.curso(curso_id)
            fichas.append(FichaEstudiante(
                estudiante=Estudiante(id=eid, correo=fila["correo"], nombre=fila["nombre"]),
                curso=cursos[curso_id], asistencia=int(fila["asistencia"]),
                apoderado_nombre=fila.get("apoderado_nombre") or "",
                apoderado_id=int(fila["apoderado_id"]) if fila.get("apoderado_id") else None,
                calificaciones=[c for c in calificaciones if c.estudiante_id == eid],
                refuerzos=[r for r in refuerzos if r.estudiante_id == eid],
                intentos=[i for i in intentos if i.estudiante_id == eid]))
        return fichas

    def ficha(self, estudiante_id: int) -> FichaEstudiante | None:
        fila = self.local.estudiante(estudiante_id)
        return self._fichas([fila])[0] if fila else None

    def cursos_docente(self) -> list[Curso]:
        return self.local.cursos_de_docente(self.usuario.id) if self.usuario else []

    def resumen_cursos(self) -> list[ResumenCurso]:
        """Un resumen por curso de la docente (para elegir curso cuando tiene más de uno)."""
        resumenes = []
        for curso in self.cursos_docente():
            fichas = self.fichas_curso(curso.id)
            resumenes.append(ResumenCurso(curso=curso, estudiantes=len(fichas),
                                          en_riesgo=sum(1 for f in fichas if f.necesita_refuerzo),
                                          sin_apoderado=sum(1 for f in fichas if not f.apoderado_nombre),
                                          avisos_sin_confirmar=avisos_sin_confirmar(
                                              self.avisos_curso(curso.id), fichas).avisos))
        return resumenes

    def fichas_curso(self, curso_id: int) -> list[FichaEstudiante]:
        return self._fichas(self.local.estudiantes_de_curso(curso_id))

    # --- Métricas de uso y desempeño (efecto de Tutor Educa) ----------------------------------------------
    def metricas_de(self, ficha: FichaEstudiante, hoy=None) -> Metricas:
        """Las métricas del semestre actual de una ficha ya cargada."""
        return calcular_metricas(ficha.estudiante.id, ficha.calificaciones, ficha.intentos, semestre_actual(hoy))

    def metricas_estudiante(self, estudiante_id: int, hoy=None) -> Metricas | None:
        ficha = self.ficha(estudiante_id)
        return self.metricas_de(ficha, hoy) if ficha else None

    def metricas_curso(self, curso_id: int, hoy=None) -> list[tuple[FichaEstudiante, Metricas]]:
        return [(f, self.metricas_de(f, hoy)) for f in self.fichas_curso(curso_id)]

    def resumen_efecto_curso(self, curso_id: int, hoy=None) -> ResumenEfecto:
        return resumen_curso([m for _f, m in self.metricas_curso(curso_id, hoy)])

    def exportar_metricas_csv(self, curso_id: int, carpeta, anonimo: bool = False, hoy=None):
        """Guarda las métricas del curso como CSV (abre directo en Excel en español) y devuelve la ruta del archivo."""
        from datetime import date
        from pathlib import Path
        curso = next((c for c in self.cursos_docente() if c.id == curso_id), None)
        if curso is None:
            raise ValueError("Ese curso no es tuyo.")
        filas = [(f.estudiante.nombre, curso.nombre, m) for f, m in self.metricas_curso(curso_id, hoy)]
        filas.sort(key=lambda fila: fila[0].lower())
        carpeta = Path(carpeta)
        carpeta.mkdir(parents=True, exist_ok=True)
        nombre_curso = "".join(c if c.isalnum() else "_" for c in curso.nombre).strip("_")
        sufijo = "anonimo" if anonimo else "con_nombres"
        ruta = carpeta / f"metricas_{nombre_curso}_{date.today():%Y-%m-%d}_{sufijo}.csv"
        ruta.write_text(a_csv(filas, anonimo), encoding="utf-8")
        return ruta

    def hijos(self) -> list[FichaEstudiante]:
        return self._fichas(self.local.hijos_de_apoderado(self.usuario.id)) if self.usuario else []

    def nombre_de(self, usuario_id: int | None) -> str:
        if not usuario_id:
            return ""
        return self.local.nombres_usuarios([usuario_id]).get(int(usuario_id), "")

    # --- Acciones del estudiante -------------------------------------------
    def iniciar_tema(self, estudiante_id: int, tema_id: str) -> None:
        """Al abrir un tema nuevo, pasa de «Nuevo» a «En curso»."""
        fecha = ahora_iso()
        if self.local.avanzar_estado_refuerzo(estudiante_id, tema_id, EstadoRefuerzo.EN_PROGRESO, fecha):
            self._encolar("estado_refuerzo", {"estudiante_id": estudiante_id, "tema_id": tema_id,
                                              "estado": EstadoRefuerzo.EN_PROGRESO, "fecha": fecha})

    def registrar_intento(self, intento: Intento) -> bool:
        """Guarda el resultado de una prueba. Devuelve True si con esto el tema quedó logrado."""
        datos = {"codigo": intento.codigo, "estudiante_id": intento.estudiante_id, "tema_id": intento.tema_id,
                 "correctas": intento.correctas, "total": intento.total, "porcentaje": intento.porcentaje,
                 "nota": intento.nota, "realizado_en": intento.realizado_en, "origen": intento.origen}
        self.local.registrar_intento(datos, id_nuevo=self.local.id_local("intentos"))
        self.local.encolar("intento", datos)
        if self.almacen:
            self.almacen.agregar(intento)      # bitácora local en JSON (persiste al cerrar la app)
        logrado = False
        if intento.logrado:
            fecha = ahora_iso()
            if self.local.avanzar_estado_refuerzo(intento.estudiante_id, intento.tema_id,
                                                  EstadoRefuerzo.LOGRADO, fecha):
                self.local.encolar("estado_refuerzo", {"estudiante_id": intento.estudiante_id,
                                                       "tema_id": intento.tema_id,
                                                       "estado": EstadoRefuerzo.LOGRADO, "fecha": fecha})
                logrado = True
        self._avisar()
        return logrado

    def bitacora(self, estudiante_id: int) -> list:
        """
        Pruebas del estudiante leídas desde el archivo JSON, de la más reciente a la más antigua.

        La primera vez, las pruebas que ya estaban en la base de datos se copian al JSON
        (así la bitácora no parte vacía). Los registros nuevos ya llegan con su duración.
        """
        if not self.almacen:
            return []
        ficha = self.ficha(estudiante_id)
        if ficha and ficha.intentos:
            self.almacen.agregar_varios(ficha.intentos)
        return self.almacen.de_estudiante(estudiante_id)

    def grafico_progreso(self, estudiante_id: int):
        """Genera el gráfico (PNG) de las pruebas del estudiante. Devuelve su ruta, o None si aún no hay suficientes datos."""
        if not self.almacen:
            return None
        ruta = self.almacen.ruta.parent / f"grafico_progreso_{estudiante_id}.png"
        self.error_grafico = ""
        registros = self.bitacora(estudiante_id)
        if ruta.exists() and ruta.stat().st_mtime >= self.almacen.ruta.stat().st_mtime:
            return ruta                           # el gráfico ya está al día: no se vuelve a dibujar
        try:
            hecho = grafico_progreso(registros, ruta)
        except Exception as error:               # por ejemplo, matplotlib no instalado en este Python
            self.error_grafico = f"No se pudo dibujar el gráfico: {error}"
            print(self.error_grafico)
            return None
        if hecho:
            print(f"Gráfico de progreso guardado en {ruta}")
        return ruta if hecho else None

    # --- Acciones del docente ----------------------------------------------
    def cambiar_desbloqueo(self, estudiante_id: int, tema_id: str, activo: bool,
                           mensaje: str | None = None, avisar: bool = True) -> None:
        fecha = ahora_iso()
        self.local.guardar_refuerzo(estudiante_id, tema_id, activo, mensaje, self.usuario.id, fecha,
                                    id_nuevo=self.local.id_local("refuerzos"))
        self.local.encolar("desbloqueo", {"estudiante_id": estudiante_id, "tema_id": tema_id,
                                          "activo": activo, "mensaje": mensaje,
                                          "docente_id": self.usuario.id, "fecha": fecha})
        if avisar:
            self._avisar()

    def desbloquear_varios(self, estudiante_ids: list[int], tema_id: str, mensaje: str = "",
                           con_aviso: bool = True) -> int:
        """
        Desbloquea un tema y, por defecto, deja un AVISO en la sección «Avisos» de las familias.

        Así la familia se entera por el mismo lugar de siempre (con el botón «Recibido») y la docente
        no tiene que escribir nada aparte. El mensaje opcional de la docente se agrega al aviso.
        """
        fichas = {i: self.ficha(i) for i in estudiante_ids}
        nuevos = [i for i, f in fichas.items()
                  if f and not any(r.tema_id == tema_id and r.activo for r in f.refuerzos)]
        for estudiante_id in estudiante_ids:
            self.cambiar_desbloqueo(estudiante_id, tema_id, True, mensaje or None, avisar=False)
        if con_aviso and nuevos:
            self._avisos_de_desbloqueo([fichas[i] for i in nuevos], tema_id, mensaje,
                                       [f for f in fichas.values() if f])
        self._avisar()
        return len(estudiante_ids)

    def _avisos_de_desbloqueo(self, fichas: list[FichaEstudiante], tema_id: str, mensaje: str,
                              pedidos: list[FichaEstudiante]) -> None:
        """
        Un aviso para todo el curso si la docente lo desbloqueó para todo el curso; si no, un aviso por
        estudiante que lo recibe por primera vez (``fichas``). ``pedidos`` son todos los elegidos.
        """
        tema = self.tema(tema_id)
        if not tema or not self.usuario:
            return
        extra = f"\n\nMensaje de la docente: {mensaje.strip()}" if mensaje and mensaje.strip() else ""
        titulo = f"Nuevo tema de refuerzo: {tema.titulo}"
        por_curso: dict[int, list[FichaEstudiante]] = {}
        for ficha in fichas:
            if ficha.curso is not None:
                por_curso.setdefault(int(ficha.curso.id), []).append(ficha)
        elegidos = {f.estudiante.id for f in pedidos}
        for curso_id, grupo in por_curso.items():
            ids_curso = {f.estudiante.id for f in self.fichas_curso(curso_id)}
            if elegidos >= ids_curso:
                cuerpo = (f"Se liberó el tema «{tema.titulo}» para todo el curso. Los estudiantes pueden "
                          f"repasarlo desde su app, incluso sin internet.{extra}")
                self.publicar_aviso(Aviso.nuevo(curso_id, self.usuario.id, titulo, cuerpo, tipo="refuerzo"))
                continue
            for ficha in grupo:
                cuerpo = (f"Se liberó el tema «{tema.titulo}» para {ficha.estudiante.primer_nombre}. Puede "
                          f"repasarlo desde su app, incluso sin internet. Lo encuentras en la pestaña "
                          f"Refuerzos.{extra}")
                self.publicar_aviso(Aviso.nuevo(curso_id, self.usuario.id, titulo, cuerpo,
                                                estudiante_id=ficha.estudiante.id, tipo="refuerzo"))

    def publicar_aviso(self, aviso: Aviso) -> None:
        datos = {"codigo": aviso.codigo, "curso_id": aviso.curso_id, "estudiante_id": aviso.estudiante_id,
                 "autor_id": aviso.autor_id, "titulo": aviso.titulo, "cuerpo": aviso.cuerpo,
                 "tipo": aviso.tipo, "creado_en": aviso.creado_en}
        self.local.publicar_aviso(datos, id_nuevo=self.local.id_local("avisos"))
        self._encolar("aviso", datos)

    def _a_aviso(self, fila: dict) -> Aviso:
        return Aviso(id=int(fila["id"]), codigo=fila["codigo"], curso_id=int(fila["curso_id"]),
                     estudiante_id=int(fila["estudiante_id"]) if fila["estudiante_id"] is not None else None,
                     autor_id=int(fila["autor_id"]), titulo=fila["titulo"], cuerpo=fila["cuerpo"],
                     tipo=fila["tipo"], creado_en=fila["creado_en"], pendiente=int(fila["id"]) < 0)

    def avisos_curso(self, curso_id: int) -> list[Aviso]:
        """Avisos enviados por el docente, con cuántos apoderados los leyeron."""
        avisos = [self._a_aviso(f) for f in self.local.avisos([curso_id])]
        lecturas = self.local.lecturas([a.id for a in avisos])
        for aviso in avisos:
            aviso.lectores = sum(1 for l in lecturas if int(l["aviso_id"]) == aviso.id)
        return avisos

    # --- Acciones del apoderado ---------------------------------------------
    def avisos_apoderado(self) -> list[Aviso]:
        if not self.usuario:
            return []
        hijos = self.local.hijos_de_apoderado(self.usuario.id)
        cursos = sorted({int(h["curso_id"]) for h in hijos})
        avisos = [self._a_aviso(f) for f in self.local.avisos(cursos, [int(h["id"]) for h in hijos])]
        leidos = {int(l["aviso_id"]) for l in self.local.lecturas([a.id for a in avisos])
                  if int(l["usuario_id"]) == self.usuario.id}
        for aviso in avisos:
            aviso.leido = aviso.id in leidos
        return avisos

    def no_leidos(self) -> int:
        return sum(1 for a in self.avisos_apoderado() if not a.leido)

    def marcar_leido(self, aviso: Aviso) -> None:
        if aviso.leido or not self.usuario:
            return
        fecha = ahora_iso()
        if self.local.marcar_aviso_leido(aviso.id, self.usuario.id, fecha):
            aviso.leido = True
            self._encolar("aviso_leido", {"aviso_codigo": aviso.codigo, "usuario_id": self.usuario.id,
                                          "fecha": fecha})

    # --- Cola ----------------------------------------------------------------
    def pendientes(self) -> int:
        return self.local.cantidad_pendientes()

    def _encolar(self, tipo: str, datos: dict) -> None:
        self.local.encolar(tipo, datos)
        self._avisar()

    def _avisar(self) -> None:
        if self._al_haber_cambios:
            self._al_haber_cambios()
