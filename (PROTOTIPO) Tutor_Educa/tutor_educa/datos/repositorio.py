"""
Consultas compartidas por el servidor (MySQL o demostración) y por la base
interna del teléfono.

Como ambas bases tienen exactamente las mismas tablas, las consultas se
escriben una sola vez en ``RepositorioTutor`` y las clases ``ServidorRemoto``
y ``BaseDatosLocal`` las heredan. El SQL es "portable": funciona igual en
SQLite y en MySQL (sin funciones propias de un motor).
"""

from __future__ import annotations

from ..modelos import (Asignatura, Calificacion, Curso, Ejemplo, EstadoRefuerzo, Intento,
                       Pregunta, Refuerzo, Tema)
from .conexiones import ConexionBD


class RepositorioTutor:
    """Lecturas y escrituras comunes sobre las tablas de Tutor Educa."""

    SQL_ESTUDIANTE = (
        "SELECT u.id, u.correo, u.nombre, e.curso_id, e.apoderado_id, e.asistencia, "
        "a.nombre AS apoderado_nombre FROM estudiantes e "
        "JOIN usuarios u ON u.id = e.usuario_id "
        "LEFT JOIN usuarios a ON a.id = e.apoderado_id")

    def __init__(self, conexion: ConexionBD):
        self.bd = conexion

    # ------------------------------------------------------------------
    # Conversión de filas (diccionarios) a objetos del dominio
    # ------------------------------------------------------------------
    @staticmethod
    def _a_asignatura(f: dict) -> Asignatura:
        return Asignatura(id=f["id"], nombre=f["nombre"], icono=f["icono"], color=f["color"],
                          tiene_tutor=bool(int(f["tiene_tutor"])), orden=int(f["orden"]))

    @staticmethod
    def _a_tema(f: dict) -> Tema:
        return Tema(id=f["id"], asignatura_id=f["asignatura_id"], titulo=f["titulo"], nivel=f["nivel"],
                    orden=int(f["orden"]), resumen=f["resumen"], contenido=f["contenido"],
                    clave=f["clave"], error_comun=f["error_comun"],
                    consejo_apoderado=f["consejo_apoderado"], icono=f.get("icono") or "book-open")

    @staticmethod
    def _a_ejemplo(f: dict) -> Ejemplo:
        return Ejemplo(id=int(f["id"]), tema_id=f["tema_id"], orden=int(f["orden"]), titulo=f["titulo"],
                       enunciado=f["enunciado"], pasos_texto=f["pasos"], resultado=f["resultado"],
                       comprobacion=f.get("comprobacion") or "")

    @staticmethod
    def _a_pregunta(f: dict) -> Pregunta:
        return Pregunta(id=int(f["id"]), tema_id=f["tema_id"], orden=int(f["orden"]),
                        enunciado=f["enunciado"], tipo=f["tipo"],
                        alternativas_texto=f.get("alternativas") or "", respuesta=f["respuesta"],
                        pista=f.get("pista") or "", explicacion=f.get("explicacion") or "")

    @staticmethod
    def _a_calificacion(f: dict) -> Calificacion:
        return Calificacion(id=int(f["id"]), estudiante_id=int(f["estudiante_id"]),
                            asignatura_id=f["asignatura_id"], nota=float(f["nota"]),
                            descripcion=f.get("descripcion") or "", fecha=f.get("fecha") or "")

    @staticmethod
    def _a_refuerzo(f: dict) -> Refuerzo:
        return Refuerzo(id=int(f["id"]), estudiante_id=int(f["estudiante_id"]), tema_id=f["tema_id"],
                        estado=f["estado"], mensaje=f.get("mensaje") or "",
                        desbloqueado_por=f.get("desbloqueado_por"),
                        desbloqueado_en=f.get("desbloqueado_en") or "",
                        actualizado_en=f.get("actualizado_en") or "", activo=bool(int(f["activo"])))

    @staticmethod
    def _a_intento(f: dict) -> Intento:
        return Intento(id=int(f["id"]), codigo=f["codigo"], estudiante_id=int(f["estudiante_id"]),
                       tema_id=f["tema_id"], correctas=int(f["correctas"]), total=int(f["total"]),
                       porcentaje=int(f["porcentaje"]), nota=float(f["nota"]),
                       realizado_en=f["realizado_en"], origen=f.get("origen") or "app")

    @staticmethod
    def _a_curso(f: dict) -> Curso:
        return Curso(id=int(f["id"]), nombre=f["nombre"], nivel=f["nivel"],
                     docente_id=int(f["docente_id"]), anio=int(f["anio"]))

    def _en(self, plantilla: str, valores: list, extra: tuple = ()) -> list[dict]:
        """Ejecuta una consulta con ``IN (...)``. ``{}`` marca dónde van los ``?``."""
        valores = list(valores)
        if not valores:
            return []
        marcadores = ", ".join("?" * len(valores))
        return self.bd.consultar(plantilla.format(marcadores), valores + list(extra))

    # ------------------------------------------------------------------
    # Usuarios
    # ------------------------------------------------------------------
    def usuario_por_correo(self, correo: str) -> dict | None:
        return self.bd.consultar_uno("SELECT * FROM usuarios WHERE correo = ?", (correo,))

    def usuario_por_id(self, usuario_id: int) -> dict | None:
        return self.bd.consultar_uno("SELECT * FROM usuarios WHERE id = ?", (usuario_id,))

    def nombres_usuarios(self, ids: list[int]) -> dict[int, str]:
        filas = self._en("SELECT id, nombre FROM usuarios WHERE id IN ({})", sorted(set(ids)))
        return {int(f["id"]): f["nombre"] for f in filas}

    # ------------------------------------------------------------------
    # Contenido de estudio
    # ------------------------------------------------------------------
    def asignaturas(self) -> list[Asignatura]:
        return [self._a_asignatura(f) for f in self.bd.consultar("SELECT * FROM asignaturas ORDER BY orden")]

    def temas(self, asignatura_id: str = "mat") -> list[Tema]:
        filas = self.bd.consultar("SELECT * FROM temas WHERE asignatura_id = ? ORDER BY orden", (asignatura_id,))
        return [self._a_tema(f) for f in filas]

    def tema(self, tema_id: str) -> Tema | None:
        fila = self.bd.consultar_uno("SELECT * FROM temas WHERE id = ?", (tema_id,))
        return self._a_tema(fila) if fila else None

    def ejemplos(self, tema_id: str) -> list[Ejemplo]:
        filas = self.bd.consultar("SELECT * FROM ejemplos WHERE tema_id = ? ORDER BY orden", (tema_id,))
        return [self._a_ejemplo(f) for f in filas]

    def preguntas(self, tema_id: str) -> list[Pregunta]:
        filas = self.bd.consultar("SELECT * FROM preguntas WHERE tema_id = ? ORDER BY orden", (tema_id,))
        return [self._a_pregunta(f) for f in filas]

    # ------------------------------------------------------------------
    # Cursos y estudiantes
    # ------------------------------------------------------------------
    def cursos_de_docente(self, docente_id: int) -> list[Curso]:
        filas = self.bd.consultar("SELECT * FROM cursos WHERE docente_id = ? ORDER BY nombre", (docente_id,))
        return [self._a_curso(f) for f in filas]

    def curso(self, curso_id: int) -> Curso | None:
        fila = self.bd.consultar_uno("SELECT * FROM cursos WHERE id = ?", (curso_id,))
        return self._a_curso(fila) if fila else None

    def estudiantes_de_curso(self, curso_id: int) -> list[dict]:
        return self.bd.consultar(f"{self.SQL_ESTUDIANTE} WHERE e.curso_id = ? ORDER BY u.nombre", (curso_id,))

    def estudiante(self, estudiante_id: int) -> dict | None:
        return self.bd.consultar_uno(f"{self.SQL_ESTUDIANTE} WHERE e.usuario_id = ?", (estudiante_id,))

    def hijos_de_apoderado(self, apoderado_id: int) -> list[dict]:
        return self.bd.consultar(f"{self.SQL_ESTUDIANTE} WHERE e.apoderado_id = ? ORDER BY u.nombre",
                                 (apoderado_id,))

    def calificaciones(self, estudiante_ids: list[int]) -> list[Calificacion]:
        filas = self._en("SELECT * FROM calificaciones WHERE estudiante_id IN ({}) "
                         "ORDER BY asignatura_id, fecha, id", estudiante_ids)
        return [self._a_calificacion(f) for f in filas]

    def refuerzos(self, estudiante_ids: list[int], solo_activos: bool = True) -> list[Refuerzo]:
        condicion = " AND activo = 1" if solo_activos else ""
        filas = self._en("SELECT * FROM refuerzos WHERE estudiante_id IN ({})" + condicion
                         + " ORDER BY desbloqueado_en DESC", estudiante_ids)
        return [self._a_refuerzo(f) for f in filas]

    def intentos(self, estudiante_ids: list[int]) -> list[Intento]:
        filas = self._en("SELECT * FROM intentos WHERE estudiante_id IN ({}) ORDER BY realizado_en DESC",
                         estudiante_ids)
        return [self._a_intento(f) for f in filas]

    def avisos(self, curso_ids: list[int], estudiante_ids: list[int] | None = None) -> list[dict]:
        """Avisos de los cursos. Si se indican estudiantes, solo los de todo el curso o dirigidos a ellos."""
        filas = self._en("SELECT * FROM avisos WHERE curso_id IN ({}) ORDER BY creado_en DESC, id DESC", curso_ids)
        if estudiante_ids is not None:
            filas = [f for f in filas if f["estudiante_id"] is None or int(f["estudiante_id"]) in estudiante_ids]
        return filas

    def lecturas(self, aviso_ids: list[int]) -> list[dict]:
        return self._en("SELECT * FROM avisos_leidos WHERE aviso_id IN ({})", aviso_ids)

    # ------------------------------------------------------------------
    # Escrituras (se usan igual en el servidor y en el teléfono)
    # ------------------------------------------------------------------
    def guardar_refuerzo(self, estudiante_id: int, tema_id: str, activo: bool, mensaje: str | None,
                         docente_id: int | None, fecha: str, id_nuevo: int | None = None) -> None:
        """Desbloquea (activo=True) o bloquea un tema. Nunca borra el avance del estudiante."""
        actual = self.bd.consultar_uno("SELECT id, activo, mensaje FROM refuerzos WHERE estudiante_id = ? "
                                       "AND tema_id = ?", (estudiante_id, tema_id))
        if actual:
            nuevo_mensaje = actual["mensaje"] if mensaje is None else mensaje
            if activo and not int(actual["activo"]):
                self.bd.ejecutar("UPDATE refuerzos SET activo = 1, mensaje = ?, desbloqueado_por = ?, "
                                 "desbloqueado_en = ?, actualizado_en = ? WHERE id = ?",
                                 (nuevo_mensaje, docente_id, fecha, fecha, actual["id"]))
            else:
                self.bd.ejecutar("UPDATE refuerzos SET activo = ?, mensaje = ?, actualizado_en = ? WHERE id = ?",
                                 (1 if activo else 0, nuevo_mensaje, fecha, actual["id"]))
        elif activo:
            fila = {"estudiante_id": estudiante_id, "tema_id": tema_id, "estado": EstadoRefuerzo.DISPONIBLE,
                    "mensaje": mensaje or "", "desbloqueado_por": docente_id, "desbloqueado_en": fecha,
                    "actualizado_en": fecha, "activo": 1}
            if id_nuevo is not None:
                fila["id"] = id_nuevo
            self.bd.insertar("refuerzos", fila)

    def avanzar_estado_refuerzo(self, estudiante_id: int, tema_id: str, estado: str, fecha: str) -> bool:
        """Cambia el estado solo si es un avance (disponible → en curso → logrado)."""
        actual = self.bd.consultar_uno("SELECT id, estado FROM refuerzos WHERE estudiante_id = ? AND tema_id = ?",
                                       (estudiante_id, tema_id))
        if not actual or not EstadoRefuerzo.es_avance(actual["estado"], estado):
            return False
        self.bd.ejecutar("UPDATE refuerzos SET estado = ?, actualizado_en = ? WHERE id = ?",
                         (estado, fecha, actual["id"]))
        return True

    def registrar_intento(self, datos: dict, id_nuevo: int | None = None) -> bool:
        """Guarda un intento. Si su código ya existe no lo duplica (sincronizar dos veces es seguro)."""
        if self.bd.valor("SELECT COUNT(*) FROM intentos WHERE codigo = ?", (datos["codigo"],), 0):
            return False
        fila = {k: datos[k] for k in ("codigo", "estudiante_id", "tema_id", "correctas", "total",
                                      "porcentaje", "nota", "realizado_en", "origen")}
        if id_nuevo is not None:
            fila["id"] = id_nuevo
        self.bd.insertar("intentos", fila)
        return True

    def publicar_aviso(self, datos: dict, id_nuevo: int | None = None) -> bool:
        if self.bd.valor("SELECT COUNT(*) FROM avisos WHERE codigo = ?", (datos["codigo"],), 0):
            return False
        fila = {k: datos[k] for k in ("codigo", "curso_id", "estudiante_id", "autor_id", "titulo",
                                      "cuerpo", "tipo", "creado_en")}
        if id_nuevo is not None:
            fila["id"] = id_nuevo
        self.bd.insertar("avisos", fila)
        return True

    def aviso_por_codigo(self, codigo: str) -> dict | None:
        return self.bd.consultar_uno("SELECT * FROM avisos WHERE codigo = ?", (codigo,))

    def marcar_aviso_leido(self, aviso_id: int, usuario_id: int, fecha: str) -> bool:
        if self.bd.valor("SELECT COUNT(*) FROM avisos_leidos WHERE aviso_id = ? AND usuario_id = ?",
                         (aviso_id, usuario_id), 0):
            return False
        self.bd.insertar("avisos_leidos", {"aviso_id": aviso_id, "usuario_id": usuario_id, "leido_en": fecha})
        return True
