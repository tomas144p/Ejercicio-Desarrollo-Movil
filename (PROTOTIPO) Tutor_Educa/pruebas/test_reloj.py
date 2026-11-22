"""
Pruebas del reloj del servidor.

El «hoy» y la hora de registro salen del servidor, no del teléfono; y si el reloj del servidor se atrasa (reinicio,
corte de luz) no se registra asistencia hasta corregirlo, porque se guardaría con un día equivocado.
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI))

from services import calendario as cal  # noqa: E402
from test_backend import HAY_API  # noqa: E402
from test_calendario import BaseCalendario  # noqa: E402

if HAY_API:
    from backend.reloj import INTERVALO_ANOTAR, TOLERANCIA, VigilanteReloj, duracion_legible  # noqa: E402


class PruebasUtilidades(unittest.TestCase):
    def test_duracion_legible(self):
        self.assertEqual(duracion_legible(timedelta(minutes=12)), "12 minutos")
        self.assertEqual(duracion_legible(timedelta(minutes=0)), "1 minuto")
        self.assertEqual(duracion_legible(timedelta(hours=3)), "3 horas")
        self.assertEqual(duracion_legible(timedelta(days=5)), "5 días")

    def test_hora_de_chile_sin_zona(self):
        # 19 de noviembre, 02:30 UTC = 18 de noviembre, 23:30 en Chile (verano, UTC-3)
        chile = cal.ahora_chile(datetime(2026, 11, 19, 2, 30, tzinfo=timezone.utc))
        self.assertEqual(chile.strftime("%Y-%m-%d %H:%M"), "2026-11-18 23:30")
        self.assertIsNone(chile.tzinfo)


@unittest.skipUnless(HAY_API, "FastAPI no está instalado")
class PruebasReloj(BaseCalendario):
    def setUp(self):
        super().setUp()
        self.t = datetime.now(timezone.utc).replace(microsecond=0)
        self.repo.reloj_utc = lambda: self.t
        self.hoy = cal.hoy_chile(self.t)

    def tocar(self, usuario="carolina.fuentes"):
        """Cualquier petición con sesión: el servidor anota la hora que ve."""
        self.assertEqual(self.cliente.get("/paquete", headers=self.cabeceras(usuario)).status_code, 200)

    def marca(self):
        return self.repo.ultima_hora_vista()

    # --- la hora de registro es del servidor ---------------------------------------------------------
    def test_la_hora_de_registro_la_pone_el_servidor_y_no_el_telefono(self):
        dia = self.dia_con_clases()
        for falsa in ("1999-01-01 00:00:00", "2099-12-31 23:59:59", "no es una fecha"):
            r = self.cambio("carolina.fuentes", "asistencia_dia", {
                "curso_id": self.curso_id, "fecha": dia, "ausentes": [], "justificados": [], "registrado_en": falsa})
            self.assertEqual(r.status_code, 200, (falsa, r.text))
            fila = self.repo.bd.consultar_uno("SELECT registrado_en FROM asistencia_dias WHERE curso_id = ? AND fecha = ?",
                                              (self.curso_id, dia))
            self.assertTrue(str(fila["registrado_en"]).startswith(cal.a_texto(self.hoy)), (falsa, fila))
        r = self.nuevo_evento("carolina.fuentes", codigo="evento-hora-servidor", creado_en="1999-01-01 00:00:00")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(str(self.repo.evento_por_codigo("evento-hora-servidor")["creado_en"]).startswith(cal.a_texto(self.hoy)))

    def test_el_hoy_lo_define_el_servidor(self):
        """Un servidor «en 2026-11-18» rechaza el día siguiente aunque el teléfono diga otra cosa."""
        self.t = datetime(2026, 11, 18, 18, 0, tzinfo=timezone.utc)          # 15:00 en Chile
        self.tocar()
        self.assertEqual(self.lista("carolina.fuentes", "2026-11-18").status_code, 200)
        r = self.lista("carolina.fuentes", "2026-11-19")
        self.assertEqual(r.status_code, 422)
        self.assertIn("no llega", r.text)

    # --- reloj atrasado ----------------------------------------------------------------------------
    def test_con_el_reloj_atrasado_no_se_registra_asistencia(self):
        dia = self.dia_con_clases()
        antes = self.exceptiones_del_dia(dia)
        self.tocar()
        referencia = self.marca()
        self.assertIsNotNone(referencia)
        self.t -= timedelta(hours=2)                                          # corte de luz: arrancó con la hora vieja
        r = self.lista("carolina.fuentes", dia, ausentes=[self.alumnos[0]])
        self.assertEqual(r.status_code, 503, r.text)                          # 503: el teléfono reintenta solo
        self.assertIn("atrasado", r.text)
        self.assertEqual(self.exceptiones_del_dia(dia), antes)                # no se guardó nada
        self.assertEqual(self.marca(), referencia)                            # y la marca NO retrocedió
        self.tocar()                                                          # leer sigue funcionando
        self.assertEqual(self.marca(), referencia)

    def test_pequenos_ajustes_de_hora_no_cuentan_como_atraso(self):
        self.tocar()
        self.t -= TOLERANCIA - timedelta(minutes=1)
        self.assertEqual(self.lista("carolina.fuentes", self.dia_con_clases()).status_code, 200)

    def test_otros_cambios_no_se_bloquean_con_el_reloj_atrasado(self):
        self.tocar()
        self.t -= timedelta(hours=5)
        self.assertEqual(self.nuevo_evento("carolina.fuentes", codigo="evento-con-reloj-malo").status_code, 200)
        self.assertEqual(self.cambio("carolina.fuentes", "curso_sabado",
                                     {"curso_id": self.curso_id, "clases_sabado": False}).status_code, 200)

    def test_al_corregirse_el_reloj_todo_vuelve_a_funcionar(self):
        self.tocar()
        reloj_bueno = self.t
        self.t -= timedelta(hours=2)
        self.assertEqual(self.lista("carolina.fuentes", self.dia_con_clases()).status_code, 503)
        self.t = reloj_bueno + timedelta(minutes=5)                           # se corrigió y siguió avanzando
        self.assertEqual(self.lista("carolina.fuentes", self.dia_con_clases()).status_code, 200)
        self.tocar()
        self.assertGreaterEqual(self.marca(), reloj_bueno + timedelta(minutes=5))

    def test_la_marca_sobrevive_a_un_reinicio(self):
        self.tocar()
        nuevo = VigilanteReloj(lambda: self.repo)                             # proceso nuevo: no recuerda nada en memoria
        self.assertFalse(nuevo.estado()["atrasado"])
        self.t -= timedelta(hours=3)
        estado = nuevo.estado()
        self.assertTrue(estado["atrasado"])
        self.assertEqual(estado["atraso"], "3 horas")

    def test_solo_escribe_en_la_base_una_vez_por_minuto(self):
        vigilante = VigilanteReloj(lambda: self.repo)
        escrituras = []
        original = self.repo.anotar_hora_vista
        self.repo.anotar_hora_vista = lambda ahora: (escrituras.append(ahora), original(ahora))
        for _ in range(5):
            vigilante.anotar()
            self.t += timedelta(seconds=10)
        self.assertEqual(len(escrituras), 1)
        self.t += INTERVALO_ANOTAR
        vigilante.anotar()
        self.assertEqual(len(escrituras), 2)

    def test_la_marca_nunca_retrocede(self):
        vigilante = VigilanteReloj(lambda: self.repo)
        vigilante.anotar()
        mayor = self.marca()
        self.t -= timedelta(hours=1)
        vigilante.anotar()
        self.assertEqual(self.marca(), mayor)

    # --- panel de administración ---------------------------------------------------------------------
    def test_el_panel_ve_la_hora_y_el_estado(self):
        admin = self.persona("admin.reloj", "admin", 1)
        self.tocar()
        r = self.cliente.get("/admin/servidor/hora", headers=self.cabeceras("admin.reloj"))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual((r.json()["atrasado"], r.json()["atraso"]), (False, ""))
        self.assertIn("hora de Chile", r.json()["texto"])
        self.t -= timedelta(hours=4)
        r = self.cliente.get("/admin/servidor/hora", headers=self.cabeceras("admin.reloj")).json()
        self.assertEqual((r["atrasado"], r["atraso"]), (True, "4 horas"))
        for perfil in ("carolina.fuentes", "andres.morales"):
            self.assertEqual(self.cliente.get("/admin/servidor/hora", headers=self.cabeceras(perfil)).status_code, 403)
        self.assertEqual(self.cliente.get("/admin/servidor/hora").status_code, 401)
        self.assertIsNotNone(admin)

    def test_solo_el_superadministrador_confirma_la_hora(self):
        self.persona("admin.reloj", "admin", 1)
        self.persona("super.reloj", "superadmin", None)
        self.tocar()
        self.t -= timedelta(hours=3)
        self.assertEqual(self.lista("carolina.fuentes", self.dia_con_clases()).status_code, 503)
        for perfil in ("admin.reloj", "carolina.fuentes", "andres.morales"):
            self.assertEqual(self.cliente.post("/admin/servidor/hora/confirmar",
                                               headers=self.cabeceras(perfil)).status_code, 403, perfil)
        self.assertEqual(self.lista("carolina.fuentes", self.dia_con_clases()).status_code, 503)
        r = self.cliente.post("/admin/servidor/hora/confirmar", headers=self.cabeceras("super.reloj"))
        self.assertEqual((r.status_code, r.json()["atrasado"]), (200, False))
        self.assertEqual(self.lista("carolina.fuentes", self.dia_con_clases()).status_code, 200)

    def test_un_reloj_que_estaba_adelantado_y_se_corrigio_se_destraba_con_la_confirmacion(self):
        self.persona("super.reloj", "superadmin", None)
        self.t += timedelta(days=30)                                          # por error, el servidor marcó un mes adelante
        self.tocar()
        self.t -= timedelta(days=30)                                          # se corrigió
        self.assertEqual(self.lista("carolina.fuentes", self.dia_con_clases()).status_code, 503)
        self.cliente.post("/admin/servidor/hora/confirmar", headers=self.cabeceras("super.reloj"))
        self.assertEqual(self.lista("carolina.fuentes", self.dia_con_clases()).status_code, 200)


if __name__ == "__main__":
    unittest.main()
