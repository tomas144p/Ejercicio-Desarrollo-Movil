"""
Pruebas del calendario (tareas 20 y 24): reglas de días con clases, asistencia diaria, eventos y feriados.

Lo más importante que verifican:
- El domingo nunca se pasa lista; el sábado solo si el curso lo activó; un feriado nunca; el futuro tampoco.
  Y eso lo hace cumplir EL SERVIDOR, no solo la app (una app modificada no se salta las reglas).
- Cada perfil ve solo lo suyo: la familia solo las inasistencias de SU estudiante, y nadie ve otro colegio.
- Funciona sin conexión: se pasa lista en el teléfono y se sincroniza sola, sin duplicar.
- Una base antigua (sin las tablas nuevas) se actualiza sola.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI))

from services import calendario as cal  # noqa: E402
from test_backend import CLAVE, HAY_API, BaseApi, ahora  # noqa: E402

if HAY_API:
    from models.contenido.datos_iniciales import DatosIniciales  # noqa: E402
    from models.datos.local import BaseDatosLocal  # noqa: E402
    from models.datos.servidor import GestorServidor  # noqa: E402
    from services.autenticacion import ServicioAutenticacion  # noqa: E402
    from services.configuracion import ConfigServidor  # noqa: E402
    from services.datos_app import ServicioDatos  # noqa: E402
    from services.sincronizacion import ServicioSincronizacion  # noqa: E402
    from test_nucleo import MonitorFalso  # noqa: E402


def evento(inicio: str, fin: str | None = None, tipo: str = "feriado", hay_clases: int = 0, curso_id=None,
           activo: int = 1, titulo: str = "Evento") -> dict:
    return {"codigo": f"c-{inicio}-{titulo}", "colegio_id": 1, "curso_id": curso_id, "titulo": titulo, "tipo": tipo,
            "fecha_inicio": inicio, "fecha_fin": fin or inicio, "hay_clases": hay_clases, "activo": activo}


# ======================================================================================================
# Reglas puras (sin base de datos)
# ======================================================================================================
class PruebasReglas(unittest.TestCase):
    LUNES, SABADO, DOMINGO = date(2026, 11, 16), date(2026, 11, 21), date(2026, 11, 22)

    def test_domingo_nunca_hay_clases(self):
        for con_sabado in (False, True):
            estado = cal.estado_del_dia(self.DOMINGO, con_sabado, [])
            self.assertFalse(estado.con_clases)
            self.assertIn("domingo", estado.motivo.lower())

    def test_sabado_solo_si_el_curso_lo_activo(self):
        self.assertFalse(cal.estado_del_dia(self.SABADO, False, []).con_clases)
        self.assertTrue(cal.estado_del_dia(self.SABADO, True, []).con_clases)
        self.assertTrue(cal.estado_del_dia(self.LUNES, False, []).con_clases)

    def test_feriado_y_sin_clases_bloquean_pero_un_evento_con_clases_no(self):
        self.assertFalse(cal.estado_del_dia(self.LUNES, False, [evento("2026-11-16")]).con_clases)
        self.assertFalse(cal.estado_del_dia(self.LUNES, False, [evento("2026-11-16", tipo="sin_clases")]).con_clases)
        self.assertTrue(cal.estado_del_dia(self.LUNES, False,
                                           [evento("2026-11-16", tipo="evaluacion", hay_clases=1)]).con_clases)

    def test_un_evento_de_otro_curso_o_dado_de_baja_no_bloquea(self):
        self.assertTrue(cal.estado_del_dia(self.LUNES, False, [evento("2026-11-16", curso_id=7)], curso_id=1).con_clases)
        self.assertFalse(cal.estado_del_dia(self.LUNES, False, [evento("2026-11-16", curso_id=7)], curso_id=7).con_clases)
        self.assertTrue(cal.estado_del_dia(self.LUNES, False, [evento("2026-11-16", activo=0)]).con_clases)

    def test_un_evento_de_varios_dias_bloquea_todo_el_rango(self):
        vacaciones = [evento("2026-11-16", "2026-11-18", tipo="sin_clases")]
        for dia in (16, 17, 18):
            self.assertFalse(cal.estado_del_dia(date(2026, 11, dia), False, vacaciones).con_clases)
        self.assertTrue(cal.estado_del_dia(date(2026, 11, 19), False, vacaciones).con_clases)

    def test_validar_dia_de_lista(self):
        hoy = date(2026, 11, 18)
        self.assertEqual(cal.validar_dia_de_lista("2026-11-18", hoy, False, []), "")
        self.assertEqual(cal.validar_dia_de_lista("2026-11-13", hoy, False, []), "")
        self.assertIn("no llega", cal.validar_dia_de_lista("2026-11-19", hoy, False, []))
        self.assertIn("antiguo", cal.validar_dia_de_lista("2024-01-10", hoy, False, []))
        self.assertIn("domingo", cal.validar_dia_de_lista("2026-11-15", hoy, True, []).lower())
        self.assertIn("sábados", cal.validar_dia_de_lista("2026-11-14", hoy, False, []))
        self.assertIn("No hay clases", cal.validar_dia_de_lista("2026-11-17", hoy, False, [evento("2026-11-17")]))
        for malo in ("hoy", "2026-13-01", "18/11/2026", "2026-11-1", ""):
            self.assertNotEqual(cal.validar_dia_de_lista(malo, hoy, False, []), "", malo)

    def test_porcentaje_cuenta_la_justificada_como_inasistencia(self):
        dias = [f"2026-11-{d:02d}" for d in range(2, 12)]            # 10 días con lista
        r = cal.resumen_asistencia(dias, {"2026-11-03": "ausente", "2026-11-05": "justificado"})
        self.assertEqual((r.dias, r.presentes, r.ausentes, r.justificados, r.porcentaje), (10, 8, 1, 1, 80))
        self.assertEqual(r.inasistencias, 2)

    def test_sin_lista_no_hay_porcentaje(self):
        r = cal.resumen_asistencia([], {})
        self.assertFalse(r.hay_datos)
        self.assertIsNone(r.porcentaje)

    def test_redondeo_hacia_arriba_en_la_mitad(self):
        dias = [f"2026-11-{d:02d}" for d in range(2, 10)]            # 8 días, 1 falta = 87,5 %
        self.assertEqual(cal.resumen_asistencia(dias, {dias[0]: "ausente"}).porcentaje, 88)

    def test_inasistencias_seguidas(self):
        dias = [f"2026-11-{d:02d}" for d in (2, 3, 4, 5, 6)]
        r = cal.resumen_asistencia(dias, {dias[2]: "ausente", dias[3]: "justificado", dias[4]: "ausente"})
        self.assertEqual(r.seguidas, 3)
        self.assertTrue(r.alerta_seguidas)
        r = cal.resumen_asistencia(dias, {dias[2]: "ausente", dias[3]: "ausente"})   # el último día vino
        self.assertEqual(r.seguidas, 0)
        self.assertFalse(r.alerta_seguidas)

    def test_dia_con_lista_que_despues_es_feriado_deja_de_contar(self):
        con_lista = {"2026-11-16", "2026-11-17"}
        self.assertEqual(cal.dias_validos_con_lista(con_lista, False, []), ["2026-11-16", "2026-11-17"])
        self.assertEqual(cal.dias_validos_con_lista(con_lista, False, [evento("2026-11-17")]), ["2026-11-16"])
        sabado = {"2026-11-21"}
        self.assertEqual(cal.dias_validos_con_lista(sabado, False, []), [])
        self.assertEqual(cal.dias_validos_con_lista(sabado, True, []), ["2026-11-21"])

    def test_validar_evento(self):
        self.assertEqual(cal.validar_evento("Prueba", "evaluacion", "2026-11-20", "2026-11-20"), "")
        self.assertIn("anterior", cal.validar_evento("X", "otro", "2026-11-20", "2026-11-19"))
        self.assertIn("tipo", cal.validar_evento("X", "inventado", "2026-11-20", "2026-11-20"))
        self.assertIn("título", cal.validar_evento("  ", "otro", "2026-11-20", "2026-11-20"))
        self.assertIn("máximo", cal.validar_evento("X", "otro", "2026-01-01", "2026-12-31"))

    def test_hoy_en_chile_usa_la_zona_de_chile(self):
        # En noviembre Chile está en UTC-3: las 02:00 UTC del 19 son las 23:00 del 18.
        self.assertEqual(cal.hoy_chile(datetime(2026, 11, 19, 2, 0, tzinfo=timezone.utc)), date(2026, 11, 18))
        self.assertEqual(cal.hoy_chile(datetime(2026, 11, 19, 3, 30, tzinfo=timezone.utc)), date(2026, 11, 19))
        # En julio está en UTC-4.
        self.assertEqual(cal.hoy_chile(datetime(2026, 7, 1, 3, 30, tzinfo=timezone.utc)), date(2026, 6, 30))

    def test_calculo_de_respaldo_sin_base_de_zonas_horarias(self):
        """Android y los contenedores mínimos pueden no traer zoneinfo: el cálculo a mano da el mismo día."""
        for momento in (datetime(2026, 11, 19, 2, 0, tzinfo=timezone.utc), datetime(2026, 7, 1, 3, 30, tzinfo=timezone.utc),
                        datetime(2026, 12, 25, 12, 0, tzinfo=timezone.utc), datetime(2026, 4, 20, 1, 0, tzinfo=timezone.utc)):
            self.assertEqual(cal._chile_sin_zoneinfo(momento).date(), cal.hoy_chile(momento), momento)

    def test_cuadricula_del_mes(self):
        semanas = cal.semanas_del_mes(2026, 11)                      # el 1 de noviembre de 2026 es domingo
        self.assertTrue(all(len(s) == 7 for s in semanas))
        self.assertEqual(semanas[0], [None] * 6 + [date(2026, 11, 1)])
        self.assertEqual(sum(1 for s in semanas for d in s if d), 30)
        self.assertEqual(len(cal.semanas_del_mes(2027, 2)), 4)       # febrero de 2027 empieza lunes y tiene 28 días

    def test_mes_vecino_cruza_el_año(self):
        self.assertEqual(cal.mes_vecino(2026, 12, 1), (2027, 1))
        self.assertEqual(cal.mes_vecino(2026, 1, -1), (2025, 12))
        self.assertEqual(cal.mes_vecino(2026, 5, 0), (2026, 5))

    def test_fechas_escritas_a_la_chilena(self):
        self.assertEqual(cal.desde_texto_chileno("8/9/2026"), "2026-09-08")
        self.assertEqual(cal.desde_texto_chileno("18-11-2026"), "2026-11-18")
        self.assertEqual(cal.a_texto_chileno("2026-11-05"), "05/11/2026")
        for malo in ("31/02/2026", "hola", "1/1", ""):
            with self.assertRaises(ValueError, msg=malo):
                cal.desde_texto_chileno(malo)

    def test_texto_de_rangos(self):
        self.assertEqual(cal.texto_rango("2026-11-20", "2026-11-20"), "viernes 20 de noviembre")
        self.assertEqual(cal.texto_rango("2026-11-20", "2026-11-24"), "del 20 al 24 de noviembre")
        self.assertIn("diciembre", cal.texto_rango("2026-11-30", "2026-12-02"))

    def test_feriados_precargados(self):
        self.assertEqual(len(cal.feriados_de(2026)), 16)
        self.assertEqual(len(cal.feriados_de(2027)), 17)
        self.assertEqual(cal.feriados_de(2030), [])
        for anio in cal.anios_con_feriados():
            dias = [d for d, _ in cal.feriados_de(anio)]
            self.assertEqual(len(dias), len(set(dias)))
            self.assertEqual(dias, sorted(dias))
            self.assertTrue(all(d.startswith(f"{anio}-") and cal.parsear_dia(d) for d in dias))
        self.assertIn("2026-12-25", [d for d, _ in cal.feriados_de(2026)])
        self.assertEqual(cal.codigo_feriado(3, "2026-12-25"), "feriado-cl-3-2026-12-25")


# ======================================================================================================
# Servidor: validaciones, permisos y aislamiento entre perfiles y colegios
# ======================================================================================================
class BaseCalendario(BaseApi):
    def setUp(self):
        super().setUp()
        self.carolina = self.id_de("carolina.fuentes")
        self.curso_id = int(self.repo.cursos_de_docente(self.carolina)[0].id)
        self.hoy = cal.hoy_chile()
        self.alumnos = [int(f["id"]) for f in self.repo.estudiantes_de_curso(self.curso_id)]
        self.sofia = self.id_de("sofia.morales")

    def dia_con_clases(self, atras: int = 0) -> str:
        """El día con clases más reciente (hoy o antes) y, si se pide, ``atras`` días con clases más atrás."""
        d, encontrados = self.hoy, 0
        while True:
            eventos = self.repo.eventos_del_colegio(1, [self.curso_id])
            if cal.estado_del_dia(d, False, eventos, self.curso_id).con_clases:
                if encontrados == atras:
                    return cal.a_texto(d)
                encontrados += 1
            d -= timedelta(days=1)

    def ultimo(self, weekday: int) -> str:
        d = self.hoy
        while d.weekday() != weekday:
            d -= timedelta(days=1)
        return cal.a_texto(d)

    def lista(self, usuario: str, fecha: str, ausentes=(), justificados=(), curso=None):
        return self.cambio(usuario, "asistencia_dia", {
            "curso_id": curso or self.curso_id, "fecha": fecha, "ausentes": list(ausentes),
            "justificados": list(justificados), "registrado_en": ahora()})

    def nuevo_evento(self, usuario: str, **extra):
        datos = {"codigo": f"evento-{len(extra)}-{id(extra)}-abcdef", "curso_id": self.curso_id, "titulo": "Prueba de fracciones",
                 "tipo": "evaluacion", "fecha_inicio": cal.a_texto(self.hoy), "fecha_fin": cal.a_texto(self.hoy),
                 "creado_en": ahora()}
        datos.update(extra)
        return self.cambio(usuario, "evento", datos)

    def exceptiones_del_dia(self, fecha: str) -> dict[int, str]:
        return {int(f["estudiante_id"]): f["estado"] for f in self.repo.asistencia_de(self.alumnos)
                if cal.dia_de(f["fecha"]) == fecha}


@unittest.skipUnless(HAY_API, "FastAPI no está instalado")
class PruebasAsistenciaServidor(BaseCalendario):
    def test_la_docente_pasa_lista_y_solo_quedan_los_ausentes(self):
        dia = self.dia_con_clases()
        r = self.lista("carolina.fuentes", dia, ausentes=[self.alumnos[0]], justificados=[self.alumnos[1]])
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.exceptiones_del_dia(dia), {self.alumnos[0]: "ausente", self.alumnos[1]: "justificado"})
        self.assertEqual(self.repo.bd.valor("SELECT COUNT(*) FROM asistencia_dias WHERE curso_id = ? AND fecha = ?",
                                            (self.curso_id, dia)), 1)

    def test_pasar_lista_de_nuevo_reemplaza_el_dia_sin_duplicar(self):
        dia = self.dia_con_clases()
        self.lista("carolina.fuentes", dia, ausentes=[self.alumnos[0], self.alumnos[2]])
        self.lista("carolina.fuentes", dia, ausentes=[self.alumnos[1]])         # corrige: ahora falta otro
        self.assertEqual(self.exceptiones_del_dia(dia), {self.alumnos[1]: "ausente"})
        self.lista("carolina.fuentes", dia)                                     # todos presentes
        self.assertEqual(self.exceptiones_del_dia(dia), {})
        self.assertEqual(self.repo.bd.valor("SELECT COUNT(*) FROM asistencia_dias WHERE curso_id = ? AND fecha = ?",
                                            (self.curso_id, dia)), 1)

    def test_corregir_un_dia_no_toca_los_otros_dias(self):
        antes, hoy_ = self.dia_con_clases(3), self.dia_con_clases()
        self.lista("carolina.fuentes", antes, ausentes=[self.alumnos[0]])
        self.lista("carolina.fuentes", hoy_, ausentes=[self.alumnos[1]])
        self.assertEqual(self.exceptiones_del_dia(antes), {self.alumnos[0]: "ausente"})

    def test_el_domingo_nunca(self):
        r = self.lista("carolina.fuentes", self.ultimo(6))
        self.assertEqual(r.status_code, 422)
        self.assertIn("domingo", r.text.lower())
        self.assertEqual(self.repo.asistencia_dias([self.curso_id])[-1:] and
                         [f for f in self.repo.asistencia_dias([self.curso_id]) if cal.dia_de(f["fecha"]) == self.ultimo(6)], [])

    def test_el_sabado_solo_si_el_curso_lo_activo(self):
        sabado = self.ultimo(5)
        r = self.lista("carolina.fuentes", sabado)
        self.assertEqual((r.status_code, "sábados" in r.text), (422, True))
        self.assertEqual(self.cambio("carolina.fuentes", "curso_sabado",
                                     {"curso_id": self.curso_id, "clases_sabado": True}).status_code, 200)
        self.assertTrue(self.repo.curso(self.curso_id).clases_sabado)
        self.assertEqual(self.lista("carolina.fuentes", sabado, ausentes=[self.alumnos[0]]).status_code, 200)
        self.assertEqual(self.lista("carolina.fuentes", self.ultimo(6)).status_code, 422)        # el domingo sigue sin
        self.cambio("carolina.fuentes", "curso_sabado", {"curso_id": self.curso_id, "clases_sabado": False})
        self.assertEqual(self.lista("carolina.fuentes", sabado).status_code, 422)

    def test_un_feriado_no_permite_pasar_lista(self):
        dia = self.dia_con_clases()
        self.repo.publicar_evento({"codigo": "feriado-de-prueba", "colegio_id": 1, "curso_id": None,
                                   "titulo": "Feriado de prueba", "tipo": "feriado", "fecha_inicio": dia,
                                   "fecha_fin": dia, "hay_clases": 0, "creado_por": None, "creado_en": ahora()})
        r = self.lista("carolina.fuentes", dia)
        self.assertEqual(r.status_code, 422)
        self.assertIn("Feriado de prueba", r.text)
        self.repo.dar_de_baja_evento("feriado-de-prueba")                         # al quitarlo, se puede otra vez
        self.assertEqual(self.lista("carolina.fuentes", dia).status_code, 200)

    def test_no_se_pasa_lista_del_futuro_ni_de_fechas_malas(self):
        for malo in (cal.a_texto(self.hoy + timedelta(days=1)), "2026-02-30", "ayer", "18/11/2026", "2020-01-01"):
            self.assertEqual(self.lista("carolina.fuentes", malo).status_code, 422, malo)

    def test_estados_imposibles_se_rechazan(self):
        dia = self.dia_con_clases()
        a = self.alumnos[0]
        self.assertEqual(self.lista("carolina.fuentes", dia, ausentes=[a], justificados=[a]).status_code, 422)
        self.assertEqual(self.lista("carolina.fuentes", dia, ausentes=[a, a]).status_code, 422)
        self.assertEqual(self.lista("carolina.fuentes", dia, ausentes=["x"]).status_code, 422)
        self.assertEqual(self.lista("carolina.fuentes", dia, ausentes=[True]).status_code, 422)
        self.assertEqual(self.lista("carolina.fuentes", dia, ausentes=[999999]).status_code, 403)

    def test_solo_la_docente_del_curso_pasa_lista(self):
        b = self.colegio_b()
        dia = self.dia_con_clases()
        antes = self.exceptiones_del_dia(dia)                      # la demostración ya trae algunas inasistencias
        self.assertEqual(self.lista("docente.b", dia, curso=self.curso_id).status_code, 403)
        self.assertEqual(self.lista("docente.b", dia, ausentes=[self.alumnos[0]], curso=b["curso"]).status_code, 403)
        for perfil in ("andres.morales", "sofia.morales"):
            self.assertEqual(self.lista(perfil, dia).status_code, 403, perfil)
        self.assertEqual(self.cambio("andres.morales", "curso_sabado",
                                     {"curso_id": self.curso_id, "clases_sabado": True}).status_code, 403)
        self.assertEqual(self.cambio("docente.b", "curso_sabado",
                                     {"curso_id": self.curso_id, "clases_sabado": True}).status_code, 403)
        self.assertEqual(self.exceptiones_del_dia(dia), antes)                # nada cambió

    def test_un_estudiante_de_otro_colegio_no_entra_en_la_lista(self):
        b = self.colegio_b()
        r = self.lista("carolina.fuentes", self.dia_con_clases(), ausentes=[b["estudiante"]])
        self.assertEqual(r.status_code, 403)


@unittest.skipUnless(HAY_API, "FastAPI no está instalado")
class PruebasEventosServidor(BaseCalendario):
    def test_la_docente_crea_un_evento_de_su_curso(self):
        r = self.nuevo_evento("carolina.fuentes", codigo="evento-ok-abcdef")
        self.assertEqual(r.status_code, 200, r.text)
        fila = self.repo.evento_por_codigo("evento-ok-abcdef")
        self.assertEqual((fila["curso_id"], fila["hay_clases"], fila["activo"]), (self.curso_id, 1, 1))
        self.nuevo_evento("carolina.fuentes", codigo="evento-ok-abcdef")        # repetir no duplica
        self.assertEqual(self.repo.bd.valor("SELECT COUNT(*) FROM eventos WHERE codigo = 'evento-ok-abcdef'"), 1)

    def test_un_feriado_de_la_docente_nunca_tiene_clases(self):
        self.nuevo_evento("carolina.fuentes", codigo="evento-feriado-abc", tipo="feriado", hay_clases=True)
        self.assertEqual(self.repo.evento_por_codigo("evento-feriado-abc")["hay_clases"], 0)

    def test_eventos_invalidos(self):
        casos = [{"tipo": "inventado"}, {"titulo": "  "}, {"fecha_fin": "2000-01-01"},
                 {"fecha_inicio": "mañana"}, {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-12-31"},
                 {"titulo": "x" * 121}, {"codigo": "corto"}]
        for i, extra in enumerate(casos):
            r = self.nuevo_evento("carolina.fuentes", **{"codigo": f"evento-malo-{i:03d}-xyz", **extra})
            self.assertEqual(r.status_code, 422, extra)
        self.assertEqual(self.repo.bd.valor("SELECT COUNT(*) FROM eventos WHERE codigo LIKE 'evento-malo-%'"), 0)

    def test_solo_eventos_de_sus_propios_cursos(self):
        b = self.colegio_b()
        self.assertEqual(self.nuevo_evento("carolina.fuentes", codigo="evento-ajeno-abcd", curso_id=b["curso"]).status_code, 403)
        self.assertEqual(self.nuevo_evento("docente.b", codigo="evento-ajeno-efgh").status_code, 403)
        for perfil in ("andres.morales", "sofia.morales"):
            self.assertEqual(self.nuevo_evento(perfil, codigo=f"evento-{perfil[:4]}-abcdef").status_code, 403)

    def test_dar_de_baja_un_evento(self):
        self.nuevo_evento("carolina.fuentes", codigo="evento-baja-abcdef")
        self.assertEqual(self.cambio("docente.b" if False else "andres.morales", "evento_baja",
                                     {"codigo": "evento-baja-abcdef"}).status_code, 403)
        self.assertEqual(self.cambio("carolina.fuentes", "evento_baja", {"codigo": "evento-baja-abcdef"}).status_code, 200)
        self.assertEqual(self.repo.evento_por_codigo("evento-baja-abcdef")["activo"], 0)       # se desactiva, no se borra

    def test_la_docente_no_puede_quitar_un_evento_de_todo_el_colegio(self):
        codigo = cal.codigo_feriado(1, "2026-12-25")
        self.assertIsNotNone(self.repo.evento_por_codigo(codigo))
        self.assertEqual(self.cambio("carolina.fuentes", "evento_baja", {"codigo": codigo}).status_code, 403)
        self.assertEqual(self.repo.evento_por_codigo(codigo)["activo"], 1)

    def test_nadie_quita_el_evento_de_otro_colegio(self):
        b = self.colegio_b()
        self.nuevo_evento("carolina.fuentes", codigo="evento-solo-a-abcdef")
        self.assertEqual(self.cambio("docente.b", "evento_baja", {"codigo": "evento-solo-a-abcdef"}).status_code, 403)
        self.assertEqual(b["colegio"] != 1, True)


@unittest.skipUnless(HAY_API, "FastAPI no está instalado")
class PruebasPaqueteCalendario(BaseCalendario):
    def paquete(self, usuario: str) -> dict:
        r = self.cliente.get("/paquete", headers=self.cabeceras(usuario))
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_cada_perfil_recibe_solo_lo_suyo(self):
        dia = self.dia_con_clases()
        self.lista("carolina.fuentes", dia, ausentes=[self.alumnos[0], self.sofia])
        docente = self.paquete("carolina.fuentes")
        familia = self.paquete("andres.morales")                  # apoderado de Sofía
        estudiante = self.paquete("sofia.morales")
        self.assertIn(self.alumnos[0], {a["estudiante_id"] for a in docente["asistencia"]})
        self.assertEqual({a["estudiante_id"] for a in familia["asistencia"]}, {self.sofia})
        self.assertEqual({a["estudiante_id"] for a in estudiante["asistencia"]}, {self.sofia})
        for paquete in (docente, familia, estudiante):
            self.assertEqual({d["curso_id"] for d in paquete["asistencia_dias"]}, {self.curso_id})

    def test_otro_colegio_no_ve_nada_de_este(self):
        b = self.colegio_b()
        self.lista("carolina.fuentes", self.dia_con_clases(), ausentes=[self.alumnos[0]])
        self.nuevo_evento("carolina.fuentes", codigo="evento-solo-a-xyz123")
        for perfil in ("docente.b", "apoderado.b", "estudiante.b"):
            p = self.paquete(perfil)
            self.assertEqual((p["asistencia_dias"], p["asistencia"], p["eventos"]), ([], [], []), perfil)
        self.repo.publicar_evento({"codigo": "evento-b-123456", "colegio_id": b["colegio"], "curso_id": None,
                                   "titulo": "Solo B", "tipo": "otro", "fecha_inicio": "2026-12-01",
                                   "fecha_fin": "2026-12-01", "hay_clases": 1, "creado_por": None, "creado_en": ahora()})
        self.assertEqual([e["titulo"] for e in self.paquete("docente.b")["eventos"]], ["Solo B"])
        self.assertNotIn("Solo B", str(self.paquete("carolina.fuentes")["eventos"]))

    def test_los_eventos_de_un_curso_no_llegan_a_otro_curso_del_mismo_colegio(self):
        otro = self.curso(self.carolina, 1, "8° Básico B")
        self.repo.publicar_evento({"codigo": "evento-otro-curso-1", "colegio_id": 1, "curso_id": otro,
                                   "titulo": "Solo 8° B", "tipo": "otro", "fecha_inicio": "2026-12-01",
                                   "fecha_fin": "2026-12-01", "hay_clases": 1, "creado_por": None, "creado_en": ahora()})
        self.assertNotIn("Solo 8° B", str(self.paquete("andres.morales")["eventos"]))      # Sofía está en 7° B
        self.assertIn("Solo 8° B", str(self.paquete("carolina.fuentes")["eventos"]))       # su docente sí lo ve

    def test_un_evento_dado_de_baja_deja_de_llegar(self):
        self.nuevo_evento("carolina.fuentes", codigo="evento-temporal-abc")
        self.assertIn("evento-temporal-abc", str(self.paquete("andres.morales")["eventos"]))
        self.cambio("carolina.fuentes", "evento_baja", {"codigo": "evento-temporal-abc"})
        self.assertNotIn("evento-temporal-abc", str(self.paquete("andres.morales")["eventos"]))


@unittest.skipUnless(HAY_API, "FastAPI no está instalado")
class PruebasAdministracionCalendario(BaseCalendario):
    def setUp(self):
        super().setUp()
        self.b = self.colegio_b()
        self.admin_a = self.persona("admin.a", "admin", 1)
        self.admin_b = self.persona("admin.b", "admin", self.b["colegio"])

    def llamar(self, metodo, ruta, usuario, json=None):
        return self.cliente.request(metodo, ruta, json=json, headers=self.cabeceras(usuario))

    def test_solo_administradores_entran(self):
        for perfil in ("carolina.fuentes", "andres.morales", "sofia.morales"):
            self.assertEqual(self.llamar("GET", "/admin/eventos", perfil).status_code, 403, perfil)
            self.assertEqual(self.llamar("POST", "/admin/eventos/feriados", perfil, {"anio": 2027}).status_code, 403)
        self.assertEqual(self.cliente.get("/admin/eventos").status_code, 401)

    def test_cargar_feriados_es_repetible_y_respeta_lo_quitado(self):
        r = self.llamar("POST", "/admin/eventos/feriados", "admin.a", {"anio": 2027})
        self.assertEqual((r.status_code, r.json()["creados"], r.json()["total"]), (200, 17, 17))
        r = self.llamar("POST", "/admin/eventos/feriados", "admin.a", {"anio": 2027})
        self.assertEqual((r.json()["creados"], r.json()["existentes"]), (0, 17))
        lista = self.llamar("GET", "/admin/eventos?anio=2027", "admin.a").json()
        self.assertEqual(len(lista), 17)
        navidad = next(e for e in lista if e["fecha_inicio"] == "2027-12-25")
        self.assertEqual((navidad["hay_clases"], navidad["curso"], navidad["tipo"]), (False, "Todo el colegio", "feriado"))
        self.assertEqual(self.llamar("DELETE", f"/admin/eventos/{navidad['id']}", "admin.a").status_code, 200)
        r = self.llamar("POST", "/admin/eventos/feriados", "admin.a", {"anio": 2027})
        self.assertEqual(r.json()["creados"], 0)                                  # no resucita lo que se quitó
        self.assertEqual(len(self.llamar("GET", "/admin/eventos?anio=2027", "admin.a").json()), 16)

    def test_cargar_feriados_de_un_año_sin_datos_explica_que_hacer(self):
        r = self.llamar("POST", "/admin/eventos/feriados", "admin.a", {"anio": 2031})
        self.assertEqual(r.status_code, 422)
        self.assertIn("a mano", r.text)
        self.assertEqual(self.llamar("POST", "/admin/eventos/feriados", "admin.a", {"anio": 1999}).status_code, 422)

    def test_crear_un_evento_de_todo_el_colegio_o_de_un_curso(self):
        r = self.llamar("POST", "/admin/eventos", "admin.a", {"titulo": "Aniversario", "tipo": "celebracion",
                                                              "fecha_inicio": "2026-12-03"})
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual((r.json()["curso"], r.json()["hay_clases"], r.json()["fecha_fin"]),
                         ("Todo el colegio", True, "2026-12-03"))
        r = self.llamar("POST", "/admin/eventos", "admin.a", {"titulo": "Paseo", "tipo": "sin_clases", "curso_id": self.curso_id,
                                                              "fecha_inicio": "2026-12-04", "fecha_fin": "2026-12-05"})
        self.assertEqual((r.status_code, r.json()["hay_clases"], r.json()["curso"]), (201, False, "7° Básico B"))

    def test_evento_invalido_o_de_un_curso_ajeno(self):
        malo = {"titulo": "X", "tipo": "otro", "fecha_inicio": "2026-12-10", "fecha_fin": "2026-12-01"}
        self.assertEqual(self.llamar("POST", "/admin/eventos", "admin.a", malo).status_code, 422)
        self.assertEqual(self.llamar("POST", "/admin/eventos", "admin.a", {**malo, "fecha_fin": "2026-12-10",
                                                                           "curso_id": self.b["curso"]}).status_code, 422)
        self.assertEqual(self.llamar("POST", "/admin/eventos", "admin.a", {**malo, "tipo": "x" * 13}).status_code, 422)
        self.assertEqual(self.llamar("POST", "/admin/eventos", "admin.a", {**malo, "extra": 1}).status_code, 422)

    def test_cada_administrador_ve_y_toca_solo_su_colegio(self):
        r = self.llamar("POST", "/admin/eventos", "admin.a", {"titulo": "Solo A", "tipo": "otro", "fecha_inicio": "2026-12-03"})
        evento_id = r.json()["id"]
        self.assertEqual(self.llamar("GET", "/admin/eventos?anio=2026", "admin.b").json(), [])
        self.assertEqual(self.llamar("DELETE", f"/admin/eventos/{evento_id}", "admin.b").status_code, 403)
        self.assertEqual(self.repo.evento(evento_id)["activo"], 1)

    def test_el_sabado_se_activa_desde_el_panel(self):
        r = self.llamar("PATCH", f"/admin/cursos/{self.curso_id}", "admin.a", {"clases_sabado": True})
        self.assertEqual(r.status_code, 200, r.text)
        curso = next(c for c in self.llamar("GET", "/admin/cursos", "admin.a").json() if c["id"] == self.curso_id)
        self.assertTrue(curso["clases_sabado"])
        self.assertEqual(self.lista("carolina.fuentes", self.ultimo(5)).status_code, 200)
        self.assertEqual(self.llamar("PATCH", f"/admin/cursos/{self.curso_id}", "admin.b", {"clases_sabado": False}).status_code, 403)


# ======================================================================================================
# La app: sin conexión, sincronización y porcentaje calculado
# ======================================================================================================
@unittest.skipUnless(HAY_API, "FastAPI no está instalado")
class PruebasCalendarioEnLaApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plantilla = Path(tempfile.mkdtemp())
        GestorServidor(ConfigServidor(motor="demo"), cls.plantilla).inicializar()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.plantilla, ignore_errors=True)

    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp())
        shutil.copy(self.plantilla / "servidor_demo.db", self.carpeta / "servidor_demo.db")
        self.gestor = GestorServidor(ConfigServidor(motor="demo"), self.carpeta).inicializar()
        self.monitor = MonitorFalso()
        self.hoy = cal.hoy_chile()

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def telefono(self, nombre: str, usuario: str):
        """Un teléfono nuevo (base local propia) con la persona ya conectada."""
        local = BaseDatosLocal(self.carpeta / f"{nombre}.db")
        sinc = ServicioSincronizacion(local, self.gestor)
        auth = ServicioAutenticacion(local, self.gestor, sinc, self.monitor)
        datos = ServicioDatos(local)
        resultado = auth.ingresar(f"{usuario}@{DatosIniciales.DOMINIO}", CLAVE)
        self.assertTrue(resultado.exito, resultado.mensaje)
        datos.iniciar_sesion(resultado.usuario)
        return local, sinc, datos, resultado.usuario

    def dia_con_clases(self, datos, curso, atras=0) -> str:
        d, n = self.hoy, 0
        while True:
            if datos.calendario_curso(curso.id).estado_dia(d).con_clases:
                if n == atras:
                    return cal.a_texto(d)
                n += 1
            d -= timedelta(days=1)

    def test_pasar_lista_sin_conexion_y_sincronizar(self):
        local, sinc, datos, docente = self.telefono("docente", "carolina.fuentes")
        curso = datos.cursos_docente()[0]
        ids = [f.estudiante.id for f in datos.fichas_curso(curso.id)]
        dia = self.dia_con_clases(datos, curso)
        pendientes = local.cantidad_pendientes()
        self.assertEqual(datos.pasar_lista(curso.id, dia, [ids[0]], [ids[1]]), "")
        self.assertEqual(local.cantidad_pendientes(), pendientes + 1)
        hay, estados = datos.lista_del_dia(curso.id, dia)
        self.assertTrue(hay)
        self.assertEqual((estados[ids[0]], estados[ids[1]], estados[ids[2]]), ("ausente", "justificado", "presente"))
        self.assertTrue(all(int(f["id"]) < 0 for f in local.bd.consultar(
            "SELECT id FROM asistencia WHERE fecha = ?", (dia,))))               # ids locales negativos
        resultado = sinc.sincronizar(docente)
        self.assertEqual((resultado.descargado, local.cantidad_pendientes()), (True, 0))
        servidor = self.gestor.servidor
        en_servidor = {int(f["estudiante_id"]): f["estado"] for f in servidor.asistencia_de(ids)
                       if cal.dia_de(f["fecha"]) == dia}
        self.assertEqual(en_servidor, {ids[0]: "ausente", ids[1]: "justificado"})
        sinc.sincronizar(docente)                                                # repetir no duplica
        self.assertEqual(servidor.bd.valor("SELECT COUNT(*) FROM asistencia WHERE fecha = ? AND estudiante_id = ?",
                                           (dia, ids[0])), 1)
        _hay, estados = datos.lista_del_dia(curso.id, dia)                      # tras bajar el paquete sigue igual
        self.assertEqual((estados[ids[0]], estados[ids[1]]), ("ausente", "justificado"))

    def test_las_reglas_tambien_se_cumplen_en_el_telefono(self):
        _local, _sinc, datos, _docente = self.telefono("docente", "carolina.fuentes")
        curso = datos.cursos_docente()[0]
        d = self.hoy
        while d.weekday() != 6:
            d -= timedelta(days=1)
        self.assertIn("domingo", datos.pasar_lista(curso.id, cal.a_texto(d), [], []).lower())
        self.assertIn("llega", datos.pasar_lista(curso.id, cal.a_texto(self.hoy + timedelta(days=1)), [], []))
        self.assertIn("no corresponden", datos.pasar_lista(curso.id, self.dia_con_clases(datos, curso), [999999], []))
        self.assertIn("no es tuyo", datos.pasar_lista(12345, self.dia_con_clases(datos, curso), [], []))

    def test_la_familia_ve_el_porcentaje_calculado_con_la_lista(self):
        _l, sinc_d, datos_d, docente = self.telefono("docente", "carolina.fuentes")
        curso = datos_d.cursos_docente()[0]
        sofia = next(f for f in datos_d.fichas_curso(curso.id) if f.estudiante.nombre.startswith("Sof"))
        for atras in range(3):                                                   # Sofía falta los últimos 3 días con clases
            datos_d.pasar_lista(curso.id, self.dia_con_clases(datos_d, curso, atras), [sofia.estudiante.id], [])
        sinc_d.sincronizar(docente)

        _l2, _s2, datos_f, apoderado = self.telefono("familia", "andres.morales")
        ficha = datos_f.hijos()[0]
        resumen = ficha.resumen_asistencia
        self.assertTrue(ficha.asistencia_calculada)
        self.assertEqual(ficha.asistencia, resumen.porcentaje)
        self.assertGreaterEqual(resumen.seguidas, 3)
        self.assertTrue(resumen.alerta_seguidas)
        self.assertLess(resumen.porcentaje, 97)                                  # antes del cambio tenía un % fijo más alto
        vista = datos_f.calendario_estudiante(ficha)
        ultimo = self.dia_con_clases(datos_d, curso)
        self.assertEqual(vista.estado_alumno(cal.parsear_dia(ultimo)), "ausente")
        titulo, lineas = vista.describir(cal.parsear_dia(ultimo), self.hoy, "alumno")
        self.assertIn("ausente", " ".join(lineas).lower())

    def test_sin_lista_se_usa_el_porcentaje_fijo_de_antes(self):
        local, _s, datos, _u = self.telefono("familia", "andres.morales")
        local.bd.ejecutar("DELETE FROM asistencia")
        local.bd.ejecutar("DELETE FROM asistencia_dias")
        ficha = datos.hijos()[0]
        self.assertFalse(ficha.asistencia_calculada)
        fijo = local.bd.valor("SELECT asistencia FROM estudiantes WHERE usuario_id = ?", (ficha.estudiante.id,))
        self.assertEqual(ficha.asistencia, int(fijo))

    def test_eventos_y_sabado_desde_el_telefono(self):
        local, sinc, datos, docente = self.telefono("docente", "carolina.fuentes")
        curso = datos.cursos_docente()[0]
        manana = cal.a_texto(self.hoy + timedelta(days=1))
        self.assertEqual(datos.crear_evento(curso.id, "  Salida a terreno ", "otro", manana, None, "Traer colación"), "")
        self.assertIn("anterior", datos.crear_evento(curso.id, "Mal", "otro", manana, "2020-01-01"))
        self.assertIn("título", datos.crear_evento(curso.id, " ", "otro", manana))
        self.assertIn("no es tuyo", datos.crear_evento(9999, "X", "otro", manana))
        self.assertEqual(datos.cambiar_sabado(curso.id, True), "")
        self.assertTrue(datos.calendario_curso(curso.id).clases_sabado)
        sinc.sincronizar(docente)
        servidor = self.gestor.servidor
        creado = next(e for e in servidor.eventos_del_colegio(1) if e["titulo"] == "Salida a terreno")
        self.assertEqual((creado["curso_id"], creado["descripcion"], creado["hay_clases"]), (curso.id, "Traer colación", 1))
        self.assertTrue(servidor.curso(curso.id).clases_sabado)
        # La familia lo ve en su calendario y los próximos eventos salen ordenados.
        _l, _s, datos_f, _a = self.telefono("familia", "andres.morales")
        ficha = datos_f.hijos()[0]
        vista = datos_f.calendario_estudiante(ficha)
        self.assertIn("Salida a terreno", [e["titulo"] for e in vista.eventos_proximos(self.hoy)])
        fechas = [cal.dia_de(e["fecha_inicio"]) for e in vista.eventos_proximos(self.hoy, 50)]
        self.assertEqual(fechas, sorted(fechas))
        # Y la docente puede quitarlo; los de todo el colegio no.
        local_evento = next(e for e in datos.calendario_curso(curso.id).eventos if e["titulo"] == "Salida a terreno")
        self.assertEqual(datos.dar_de_baja_evento(local_evento), "")
        feriado = next(e for e in datos.calendario_curso(curso.id).eventos if e["tipo"] == "feriado")
        self.assertIn("administración", datos.dar_de_baja_evento(feriado))
        sinc.sincronizar(docente)
        self.assertEqual(servidor.evento_por_codigo(creado["codigo"])["activo"], 0)

    def test_describir_un_dia_del_curso(self):
        _l, _s, datos, _u = self.telefono("docente", "carolina.fuentes")
        curso = datos.cursos_docente()[0]
        vista = datos.calendario_curso(curso.id)
        ultimo = cal.parsear_dia(self.dia_con_clases(datos, curso, 1))
        titulo, lineas = vista.describir(ultimo, self.hoy, "curso")
        self.assertTrue(lineas)
        d = ultimo
        while d.weekday() != 6:
            d += timedelta(days=1)
        self.assertIn("domingo", " ".join(vista.describir(d, self.hoy, "curso")[1]).lower())
        self.assertIn("Todavía no llega", " ".join(vista.describir(self.hoy + timedelta(days=3), self.hoy, "curso")[1]))


# ======================================================================================================
# Base de datos: bases antiguas, datos de demostración y SQL de MySQL
# ======================================================================================================
@unittest.skipUnless(HAY_API, "FastAPI no está instalado")
class PruebasBaseDeDatosCalendario(unittest.TestCase):
    def test_una_base_antigua_se_actualiza_sola_y_recibe_el_calendario_de_ejemplo(self):
        carpeta = Path(tempfile.mkdtemp())
        try:
            gestor = GestorServidor(ConfigServidor(motor="demo"), carpeta).inicializar()
            bd = gestor.servidor.bd
            for tabla in ("asistencia", "asistencia_dias", "eventos"):
                bd.ejecutar(f"DROP TABLE {tabla}")
            bd.ejecutar("ALTER TABLE cursos DROP COLUMN clases_sabado")        # así era una base de antes del calendario
            bd.cerrar()
            nueva = GestorServidor(ConfigServidor(motor="demo"), carpeta).inicializar().servidor
            self.assertEqual(nueva.bd.valor("SELECT clases_sabado FROM cursos WHERE id = 1"), 0)
            self.assertGreater(nueva.bd.valor("SELECT COUNT(*) FROM asistencia_dias"), 0)
            self.assertGreater(nueva.bd.valor("SELECT COUNT(*) FROM eventos"), 0)
            self.assertFalse(nueva.curso(1).clases_sabado)
            nueva.bd.cerrar()
        finally:
            shutil.rmtree(carpeta, ignore_errors=True)

    def test_los_datos_de_demostracion_respetan_las_reglas(self):
        for hoy in (date(2026, 11, 18), date(2026, 11, 22), date(2027, 3, 1)):          # también en domingo o lunes
            datos = DatosIniciales(hoy).calendario()
            eventos = datos["eventos"]
            for fila in datos["asistencia_dias"]:
                dia = cal.parsear_dia(fila["fecha"])
                self.assertTrue(cal.estado_del_dia(dia, False, eventos, 1).con_clases, fila["fecha"])
                self.assertLess(dia, hoy)                                                # hoy queda para probar «Pasar lista»
            dias = {f["fecha"] for f in datos["asistencia_dias"]}
            self.assertTrue(all(f["fecha"] in dias for f in datos["asistencia"]))
            self.assertEqual(len({(f["estudiante_id"], f["fecha"]) for f in datos["asistencia"]}), len(datos["asistencia"]))

    def test_el_sql_de_mysql_trae_el_calendario(self):
        from herramientas.generar_sql_mysql import generar, generar_migracion_calendario
        for produccion in (False, True):
            sql = generar(produccion=produccion)
            for tabla in ("asistencia_dias", "asistencia", "eventos"):
                self.assertIn(f"CREATE TABLE IF NOT EXISTS {tabla}", sql)
            self.assertIn("clases_sabado INT NOT NULL DEFAULT 0", sql)
        self.assertNotIn("INSERT INTO eventos", generar(produccion=True))          # producción no trae datos de prueba
        migracion = generar_migracion_calendario()
        self.assertIn("ALTER TABLE cursos ADD COLUMN clases_sabado", migracion)
        self.assertIn("CREATE TABLE IF NOT EXISTS eventos", migracion)
        self.assertNotIn("DROP", migracion)                                          # nunca borra nada


if __name__ == "__main__":
    unittest.main()
