"""
Pruebas de administración: roles, códigos de invitación y gestión de cuentas, cursos y colegios.

Lo más importante que verifican: cada perfil hace SOLO lo que le corresponde y solo dentro de su colegio, nadie recibe
una contraseña ajena, y los códigos de invitación sirven una vez, vencen y no se pueden adivinar.
"""

from __future__ import annotations

import contextlib
import io
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI))          # para poder importar test_backend sin importar cómo se ejecuten las pruebas

from test_backend import CLAVE, HAY_API, BaseApi, ahora, correo  # noqa: E402

if HAY_API:
    from backend.cuentas import Cuentas, ErrorAlta  # noqa: E402
    from backend.crear_usuario import main as consola_crear_usuario  # noqa: E402
    from services.seguridad import CLAVE_PENDIENTE, CodigosInvitacion  # noqa: E402

CLAVE_NUEVA = "Clave-larga-2026"


class BaseAdmin(BaseApi):
    """Escenario: Colegio Demo (id 1, con su admin) y Escuela Rural B (con su admin), más una superadmin."""

    def setUp(self):
        super().setUp()
        self.b = self.colegio_b()
        self.admin_a = self.persona("admin.a", "admin", 1)
        self.admin_b = self.persona("admin.b", "admin", self.b["colegio"])
        self.persona("super", "superadmin", None)
        self.sofia, self.andres = self.id_de("sofia.morales"), self.id_de("andres.morales")
        self.carolina = self.id_de("carolina.fuentes")

    def llamar(self, metodo: str, ruta: str, usuario: str | None = None, json=None):
        cabeceras = self.cabeceras(usuario) if usuario else {}
        return self.cliente.request(metodo, ruta, json=json, headers=cabeceras)

    def curso_de_carolina(self) -> int:
        return int(self.repo.cursos_de_docente(self.carolina)[0].id)

    def crear(self, usuario: str, datos: dict):
        return self.llamar("POST", "/admin/usuarios", usuario, datos)

    def activar(self, correo_: str, codigo: str, clave: str = CLAVE_NUEVA):
        return self.cliente.post("/activar", json={"correo": correo_, "codigo": codigo, "clave": clave})


# ======================================================================================================
class PruebasInvitaciones(BaseAdmin):
    def nueva_docente(self) -> dict:
        r = self.crear("admin.a", {"correo": "nueva@colegio.cl", "nombre": "Nueva Docente", "rol": "docente"})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def test_cuenta_nueva_queda_pendiente_y_se_activa_con_el_codigo(self):
        creada = self.nueva_docente()
        self.assertTrue(creada["usuario"]["pendiente"])
        self.assertEqual(self.ingresar("nueva").status_code, 401)           # sin contraseña nadie entra
        self.assertEqual(self.cliente.post("/login", json={"correo": "nueva@colegio.cl", "clave": ""}).status_code, 422)
        self.assertEqual(self.cliente.post("/login", json={"correo": "nueva@colegio.cl",
                                                           "clave": CLAVE_PENDIENTE}).status_code, 401)
        r = self.activar("nueva@colegio.cl", creada["codigo"])
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["usuario"]["rol"], "docente")
        self.assertEqual(r.json()["usuario"]["colegio"], "Colegio Demo")
        cabeceras = {"Authorization": f"Bearer {r.json()['token_acceso']}"}
        self.assertEqual(self.cliente.get("/paquete", headers=cabeceras).status_code, 200)
        entra = self.cliente.post("/login", json={"correo": "nueva@colegio.cl", "clave": CLAVE_NUEVA})
        self.assertEqual(entra.status_code, 200)                              # ya puede ingresar con su contraseña

    def test_el_codigo_sirve_una_sola_vez_y_acepta_variantes_al_escribirlo(self):
        creada = self.nueva_docente()
        escrito = creada["codigo"].lower().replace("-", " ")                  # minúsculas y espacio en vez de guion
        self.assertEqual(self.activar("NUEVA@colegio.cl", escrito).status_code, 200)
        self.assertEqual(self.activar("nueva@colegio.cl", creada["codigo"], "Otra-clave-larga-1").status_code, 422)

    def test_errores_del_codigo_son_todos_iguales_y_no_revelan_nada(self):
        creada = self.nueva_docente()
        mensajes = {
            self.activar("nueva@colegio.cl", "ZZZZZ-ZZZZZ").json()["detail"],            # código equivocado
            self.activar("fantasma@colegio.cl", creada["codigo"]).json()["detail"],        # correo inexistente
            self.activar("nueva@colegio.cl", "abcde").json()["detail"],                    # no tiene formato de código
        }
        self.assertEqual(len(mensajes), 1)
        self.assertIn("código", mensajes.pop())

    def test_la_contrasena_nueva_debe_ser_razonable(self):
        creada = self.nueva_docente()
        for floja in ("corta1", "12345678901234", "!!!!!!!!!!!!!!"):
            r = self.activar("nueva@colegio.cl", creada["codigo"], floja)
            self.assertEqual(r.status_code, 422, floja)
            self.assertIn("contraseña", r.json()["detail"])
        self.assertEqual(self.activar("nueva@colegio.cl", creada["codigo"]).status_code, 200)   # el código seguía vivo

    def test_codigo_vencido(self):
        creada = self.nueva_docente()
        self.repo.bd.ejecutar("UPDATE invitaciones SET vence_en = '2020-01-01 00:00:00'")
        self.assertEqual(self.activar("nueva@colegio.cl", creada["codigo"]).status_code, 422)

    def test_adivinar_codigos_se_bloquea(self):
        creada = self.nueva_docente()
        for _ in range(self.ajustes.login_max_fallos):
            self.assertEqual(self.activar("nueva@colegio.cl", "ZZZZZ-ZZZZZ").status_code, 422)
        r = self.activar("nueva@colegio.cl", creada["codigo"])               # ni el código correcto pasa mientras dura
        self.assertEqual(r.status_code, 429)
        self.assertIn("Retry-After", r.headers)

    def test_solo_se_guarda_la_huella_del_codigo(self):
        creada = self.nueva_docente()
        for fila in self.repo.bd.consultar("SELECT * FROM invitaciones"):
            self.assertNotIn(CodigosInvitacion.normalizar(creada["codigo"]), CodigosInvitacion.normalizar(str(fila.values())))
        self.assertEqual(self.repo.bd.valor("SELECT codigo_hash FROM invitaciones WHERE usuario_id = ?",
                                            (creada["usuario"]["id"],)), CodigosInvitacion.huella(creada["codigo"]))

    def test_reiniciar_contrasena_deja_sin_efecto_la_anterior_y_los_codigos_viejos(self):
        self.assertEqual(self.ingresar("andres.morales").status_code, 200)
        primero = self.llamar("POST", f"/admin/usuarios/{self.andres}/invitacion", "admin.a").json()
        self.assertEqual(self.ingresar("andres.morales").status_code, 401)   # la contraseña anterior ya no sirve
        segundo = self.llamar("POST", f"/admin/usuarios/{self.andres}/invitacion", "admin.a").json()
        self.assertNotEqual(primero["codigo"], segundo["codigo"])
        self.assertEqual(self.activar(correo("andres.morales"), primero["codigo"]).status_code, 422)   # el viejo murió
        self.assertEqual(self.activar(correo("andres.morales"), segundo["codigo"]).status_code, 200)
        self.assertEqual(self.cliente.post("/login", json={"correo": correo("andres.morales"),
                                                           "clave": CLAVE_NUEVA}).status_code, 200)

    def test_cuenta_desactivada_no_se_activa_ni_recibe_codigo(self):
        creada = self.nueva_docente()
        self.llamar("PATCH", f"/admin/usuarios/{creada['usuario']['id']}", "admin.a", {"activo": False})
        self.assertEqual(self.activar("nueva@colegio.cl", creada["codigo"]).status_code, 422)
        r = self.llamar("POST", f"/admin/usuarios/{creada['usuario']['id']}/invitacion", "admin.a")
        self.assertEqual(r.status_code, 422)

    def test_los_registros_de_auditoria_no_contienen_codigos(self):
        with self.assertLogs("tutor.auditoria", level="INFO") as registro:
            creada = self.nueva_docente()
            self.activar("nueva@colegio.cl", creada["codigo"])
        texto = "\n".join(registro.output)
        self.assertNotIn(creada["codigo"], texto)
        self.assertNotIn(CodigosInvitacion.normalizar(creada["codigo"]), CodigosInvitacion.normalizar(texto))
        self.assertIn("usuarios.crear", texto)


# ======================================================================================================
class PruebasAdministracion(BaseAdmin):
    def test_solo_los_administradores_entran_a_las_rutas_de_administracion(self):
        self.assertEqual(self.llamar("GET", "/admin/usuarios").status_code, 401)
        for perfil in ("carolina.fuentes", "andres.morales", "sofia.morales"):
            self.assertEqual(self.llamar("GET", "/admin/usuarios", perfil).status_code, 403, perfil)
            self.assertEqual(self.llamar("GET", "/admin/cursos", perfil).status_code, 403, perfil)
            self.assertEqual(self.llamar("GET", "/admin/colegios", perfil).status_code, 403, perfil)

    def test_el_admin_ve_solo_su_colegio(self):
        r = self.llamar("GET", "/admin/usuarios", "admin.a")
        self.assertEqual(r.status_code, 200)
        self.assertEqual({u["colegio_id"] for u in r.json()}, {1})
        self.assertNotIn(correo("docente.b"), r.text)
        self.assertNotIn("clave_hash", r.text)
        self.assertEqual(self.llamar("GET", f"/admin/usuarios?colegio_id={self.b['colegio']}", "admin.a").status_code, 403)
        self.assertEqual([c["nombre"] for c in self.llamar("GET", "/admin/colegios", "admin.a").json()], ["Colegio Demo"])
        de_b = self.llamar("GET", f"/admin/usuarios?colegio_id={self.b['colegio']}", "super")
        self.assertEqual(de_b.status_code, 200)
        self.assertIn("Docente B", de_b.text)                                   # la superadmin sí ve cualquier colegio

    def test_filtros_de_la_lista(self):
        docentes = self.llamar("GET", "/admin/usuarios?rol=docente", "admin.a").json()
        self.assertEqual([d["rol"] for d in docentes], ["docente"] * len(docentes))
        sofia = self.llamar("GET", "/admin/usuarios?buscar=Sofía", "admin.a").json()
        self.assertEqual([u["nombre"] for u in sofia], ["Sofía Morales"])
        self.assertIsNotNone(sofia[0]["curso_id"])
        self.assertEqual(self.llamar("GET", "/admin/usuarios?rol=director", "admin.a").status_code, 422)

    def test_solo_la_superadmin_crea_y_cambia_colegios(self):
        self.assertEqual(self.llamar("POST", "/admin/colegios", "admin.a", {"nombre": "Colegio Nuevo"}).status_code, 403)
        r = self.llamar("POST", "/admin/colegios", "super", {"nombre": "  Colegio   Nuevo "})
        self.assertEqual((r.status_code, r.json()["nombre"]), (201, "Colegio Nuevo"))
        self.assertEqual(self.llamar("POST", "/admin/colegios", "super", {"nombre": "Colegio Nuevo"}).status_code, 422)
        self.assertEqual(self.llamar("POST", "/admin/colegios", "super", {"nombre": "ab"}).status_code, 422)
        self.assertEqual(self.llamar("PATCH", f"/admin/colegios/{r.json()['id']}", "admin.a",
                                     {"activo": False}).status_code, 403)
        self.assertEqual(len(self.llamar("GET", "/admin/colegios", "super").json()), 3)

    def test_suspender_un_colegio_desde_la_api_deja_sin_acceso_a_su_gente(self):
        self.assertEqual(self.llamar("GET", "/paquete", "docente.b").status_code, 200)
        self.cabeceras("admin.b")                                                # ya tiene la sesión abierta
        r = self.llamar("PATCH", f"/admin/colegios/{self.b['colegio']}", "super", {"activo": False})
        self.assertEqual((r.status_code, r.json()["activo"]), (200, False))
        self.assertEqual(self.llamar("GET", "/paquete", "docente.b").status_code, 403)
        self.assertEqual(self.llamar("GET", "/admin/usuarios", "admin.b").status_code, 403)
        self.assertEqual(self.llamar("GET", "/admin/usuarios", "admin.a").status_code, 200)    # el otro colegio sigue

    def test_la_superadmin_crea_al_primer_admin_de_un_colegio(self):
        datos = {"correo": "directora@colegio.cl", "nombre": "Marta Rojas", "rol": "admin",
                 "colegio_id": self.b["colegio"]}
        self.assertEqual(self.crear("admin.a", datos).status_code, 403)                 # un admin no crea admins
        self.assertEqual(self.crear("super", {**datos, "colegio_id": None}).status_code, 422)   # falta el colegio
        r = self.crear("super", datos)
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json()["usuario"]["colegio_id"], self.b["colegio"])
        self.assertEqual(self.activar("directora@colegio.cl", r.json()["codigo"]).status_code, 200)

    def test_nadie_crea_superadmins_por_la_api(self):
        datos = {"correo": "otra.super@x.cl", "nombre": "Otra Super", "rol": "superadmin"}
        self.assertEqual(self.crear("super", datos).status_code, 403)
        self.assertEqual(self.crear("admin.a", datos).status_code, 403)

    def test_las_contrasenas_no_se_pueden_entregar_por_la_api(self):
        r = self.crear("admin.a", {"correo": "x@colegio.cl", "nombre": "Una Docente", "rol": "docente",
                                   "clave": "Clave-larga-2026"})
        self.assertEqual(r.status_code, 422)                     # campo desconocido: se rechaza, no se ignora

    def test_el_admin_crea_docente_con_curso_y_asigna_cursos(self):
        r = self.crear("admin.a", {"correo": "prof@colegio.cl", "nombre": "Profe Nueva", "rol": "docente",
                                   "curso_nuevo": {"nombre": "6° A", "nivel": "6° Básico"}})
        self.assertEqual(r.status_code, 201, r.text)
        docente = r.json()["usuario"]["id"]
        cursos = self.llamar("GET", "/admin/cursos", "admin.a").json()
        nuevo = next(c for c in cursos if c["docente_id"] == docente)
        self.assertEqual((nuevo["nombre"], nuevo["estudiantes"]), ("6° A", 0))
        otro = self.llamar("POST", "/admin/cursos", "admin.a", {"nombre": "6° B", "nivel": "6° Básico",
                                                                "docente_id": docente})
        self.assertEqual(otro.status_code, 201, otro.text)
        # reasignar el curso de Carolina a la nueva docente
        cambio = self.llamar("PATCH", f"/admin/cursos/{self.curso_de_carolina()}", "admin.a", {"docente_id": docente})
        self.assertEqual((cambio.status_code, cambio.json()["docente_id"]), (200, docente))
        self.assertEqual(self.llamar("GET", "/paquete", "carolina.fuentes").json()["curso_ids"], [])

    def test_los_cursos_no_cruzan_de_colegio(self):
        mala = {"nombre": "9° A", "nivel": "9°", "docente_id": self.b["docente"]}        # docente de otro colegio
        self.assertEqual(self.llamar("POST", "/admin/cursos", "admin.a", mala).status_code, 422)
        self.assertEqual(self.llamar("PATCH", f"/admin/cursos/{self.b['curso']}", "admin.a",
                                     {"nombre": "Mío ahora"}).status_code, 403)
        self.assertEqual(self.llamar("GET", f"/admin/cursos?colegio_id={self.b['colegio']}", "admin.a").status_code, 403)
        self.assertEqual(self.llamar("PATCH", f"/admin/cursos/{self.curso_de_carolina()}", "admin.a",
                                     {"docente_id": self.b["docente"]}).status_code, 422)
        self.assertEqual(self.llamar("PATCH", f"/admin/cursos/{self.curso_de_carolina()}", "admin.a", {}).status_code, 422)

    def test_baja_y_alta_de_cuentas_sin_borrar_nada(self):
        self.cabeceras("carolina.fuentes")                                       # ya tiene la sesión abierta
        r = self.llamar("PATCH", f"/admin/usuarios/{self.carolina}", "admin.a", {"activo": False})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["usuario"]["activo"])
        self.assertTrue(r.json()["advertencias"])                            # avisa que le quedan cursos a cargo
        self.assertEqual(self.llamar("GET", "/paquete", "carolina.fuentes").status_code, 401)    # su sesión muere
        self.assertEqual(self.ingresar("carolina.fuentes").status_code, 403)
        self.llamar("PATCH", f"/admin/usuarios/{self.carolina}", "admin.a", {"activo": True})
        self.assertEqual(self.ingresar("carolina.fuentes").status_code, 200)
        self.assertIsNotNone(self.repo.usuario_por_id(self.carolina))        # nunca se borró

    def test_limites_entre_administradores(self):
        yo = self.admin_a
        self.assertEqual(self.llamar("PATCH", f"/admin/usuarios/{yo}", "admin.a", {"activo": False}).status_code, 403)
        self.assertEqual(self.llamar("PATCH", f"/admin/usuarios/{self.admin_b}", "admin.a",
                                     {"activo": False}).status_code, 403)    # ni de otro colegio…
        otro_admin = self.persona("admin.a2", "admin", 1)
        self.assertEqual(self.llamar("PATCH", f"/admin/usuarios/{otro_admin}", "admin.a",
                                     {"activo": False}).status_code, 403)    # …ni otro admin del suyo
        self.assertEqual(self.llamar("PATCH", f"/admin/usuarios/{otro_admin}", "super",
                                     {"activo": False}).status_code, 200)    # solo la superadmin
        super_id = self.id_de("super")
        self.assertEqual(self.llamar("PATCH", f"/admin/usuarios/{super_id}", "super", {"nombre": "Otro Nombre"}).status_code, 403)
        self.assertEqual(self.llamar("POST", f"/admin/usuarios/{super_id}/invitacion", "admin.a").status_code, 403)
        self.assertEqual(self.llamar("PATCH", f"/admin/usuarios/{self.b['docente']}", "admin.a",
                                     {"activo": False}).status_code, 403)

    def test_los_administradores_no_usan_la_app(self):
        for perfil in ("admin.a", "super"):
            self.assertEqual(self.llamar("GET", "/paquete", perfil).status_code, 403)
            cambio = {"aviso_codigo": "demo-aviso-1", "fecha": ahora()}
            self.assertEqual(self.cambio(perfil, "aviso_leido", cambio).status_code, 403)
            chat = {"sistema": "x", "mensajes": [{"role": "user", "content": "hola"}]}
            self.assertEqual(self.llamar("POST", "/ia/chat", perfil, chat).status_code, 403)

    def test_el_estudiante_toma_el_colegio_de_su_curso(self):
        datos = {"correo": "nuevo.est@colegio.cl", "nombre": "Nuevo Estudiante", "rol": "estudiante",
                 "curso_id": self.b["curso"]}
        self.assertEqual(self.crear("admin.a", datos).status_code, 403)         # curso de otro colegio
        r = self.crear("admin.b", datos)
        self.assertEqual((r.status_code, r.json()["usuario"]["colegio_id"]), (201, self.b["colegio"]))
        self.assertEqual(self.crear("admin.b", {**datos, "correo": "otro@colegio.cl", "colegio_id": 1}).status_code, 422)


# ======================================================================================================
class PruebasDocenteGestionaSusEstudiantes(BaseAdmin):
    def nuevo(self, **extra):
        datos = {"correo": "luis@correo.cl", "nombre": "Luis Pérez", "curso_id": self.curso_de_carolina(),
                 "apoderado_correo": "mama.luis@correo.cl", "apoderado_nombre": "Rosa Pérez"}
        datos.update(extra)
        return self.llamar("POST", "/docente/estudiantes", "carolina.fuentes", datos)

    def test_crea_un_estudiante_con_su_apoderado_y_ambos_activan_sus_cuentas(self):
        r = self.nuevo()
        self.assertEqual(r.status_code, 201, r.text)
        datos = r.json()
        self.assertTrue(datos["usuario"]["pendiente"] and datos["codigo"])
        self.assertFalse(datos["apoderado"]["existente"])
        self.assertTrue(datos["apoderado"]["codigo"])
        self.assertEqual(datos["usuario"]["colegio_id"], 1)
        estudiante_id = datos["usuario"]["id"]
        self.assertIn(estudiante_id, self.llamar("GET", "/paquete", "carolina.fuentes").json()["estudiante_ids"])
        mama = self.activar("mama.luis@correo.cl", datos["apoderado"]["codigo"])
        self.assertEqual(mama.status_code, 200, mama.text)
        cabeceras = {"Authorization": f"Bearer {mama.json()['token_acceso']}"}
        self.assertEqual(self.cliente.get("/paquete", headers=cabeceras).json()["estudiante_ids"], [estudiante_id])
        self.assertEqual(self.activar("luis@correo.cl", datos["codigo"]).status_code, 200)

    def test_vincula_a_un_apoderado_que_ya_existe_sin_crearle_otra_cuenta(self):
        r = self.nuevo(apoderado_correo=correo("andres.morales"), apoderado_nombre=None)
        self.assertEqual(r.status_code, 201, r.text)
        self.assertTrue(r.json()["apoderado"]["existente"])
        self.assertIsNone(r.json()["apoderado"]["codigo"])               # no se le toca la contraseña
        paquete = self.llamar("GET", "/paquete", "andres.morales").json()
        self.assertEqual(sorted(paquete["estudiante_ids"]), sorted([self.sofia, r.json()["usuario"]["id"]]))
        self.assertEqual(self.ingresar("andres.morales").status_code, 200)

    def test_no_puede_salirse_de_sus_cursos_ni_de_su_colegio(self):
        self.assertEqual(self.nuevo(curso_id=self.b["curso"]).status_code, 403)                 # curso de otro colegio
        otra = self.persona("otra.docente", "docente", 1)
        otro_curso = self.curso(otra, 1, "8° Básico A")
        self.assertEqual(self.nuevo(curso_id=otro_curso).status_code, 403)                      # curso de otra docente
        self.assertEqual(self.nuevo(apoderado_correo=correo("apoderado.b"), apoderado_nombre="X Yz").status_code, 422)
        self.assertEqual(self.nuevo(apoderado_correo=correo("carolina.fuentes")).status_code, 422)   # no es apoderado
        self.assertEqual(self.nuevo(apoderado_correo="nuevo@correo.cl", apoderado_nombre=None).status_code, 422)
        self.assertIsNone(self.repo.usuario_por_correo("luis@correo.cl"))        # nada quedó a medias
        self.assertIsNone(self.repo.usuario_por_correo("nuevo@correo.cl"))

    def test_una_docente_no_crea_docentes_ni_administra_otros_perfiles(self):
        self.assertEqual(self.llamar("POST", "/admin/usuarios", "carolina.fuentes",
                                     {"correo": "d@x.cl", "nombre": "Docente Dos", "rol": "docente"}).status_code, 403)
        self.assertEqual(self.llamar("POST", f"/docente/usuarios/{self.admin_a}/invitacion",
                                     "carolina.fuentes").status_code, 403)
        otra = self.persona("otra.docente", "docente", 1)
        self.assertEqual(self.llamar("POST", f"/docente/usuarios/{otra}/invitacion", "carolina.fuentes").status_code, 403)
        self.assertEqual(self.llamar("PATCH", f"/docente/estudiantes/{self.b['estudiante']}", "carolina.fuentes",
                                     {"activo": False}).status_code, 403)
        for perfil in ("andres.morales", "sofia.morales"):
            self.assertEqual(self.llamar("POST", "/docente/estudiantes", perfil, {
                "correo": "z@x.cl", "nombre": "Zeta Zeta", "curso_id": self.curso_de_carolina()}).status_code, 403)

    def test_baja_de_un_estudiante_lo_saca_de_las_listas_y_se_puede_reactivar(self):
        self.assertEqual(self.llamar("GET", "/paquete", "sofia.morales").status_code, 200)
        r = self.llamar("PATCH", f"/docente/estudiantes/{self.sofia}", "carolina.fuentes", {"activo": False})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertNotIn(self.sofia, self.llamar("GET", "/paquete", "carolina.fuentes").json()["estudiante_ids"])
        self.assertEqual(self.llamar("GET", "/paquete", "andres.morales").json()["estudiante_ids"], [])
        self.assertEqual(self.llamar("GET", "/paquete", "sofia.morales").status_code, 401)     # su sesión murió
        self.assertEqual(self.ingresar("sofia.morales").status_code, 403)
        self.assertIsNotNone(self.repo.usuario_por_id(self.sofia))                              # el historial se conserva
        self.assertTrue(self.repo.bd.valor("SELECT COUNT(*) FROM calificaciones WHERE estudiante_id = ?", (self.sofia,)))
        self.llamar("PATCH", f"/docente/estudiantes/{self.sofia}", "carolina.fuentes", {"activo": True})
        self.assertIn(self.sofia, self.llamar("GET", "/paquete", "carolina.fuentes").json()["estudiante_ids"])
        self.assertEqual(self.ingresar("sofia.morales").status_code, 200)

    def test_cambiar_de_curso_y_de_apoderado(self):
        otro_curso = self.curso(self.carolina, 1, "7° Básico C")                  # otro curso de la misma docente
        r = self.llamar("PATCH", f"/docente/estudiantes/{self.sofia}", "carolina.fuentes", {"curso_id": otro_curso})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.repo.estudiante(self.sofia)["curso_id"], otro_curso)
        ajeno = self.curso(self.persona("otra.docente", "docente", 1), 1, "8° A")
        self.assertEqual(self.llamar("PATCH", f"/docente/estudiantes/{self.sofia}", "carolina.fuentes",
                                     {"curso_id": ajeno}).status_code, 403)
        self.assertEqual(self.llamar("PATCH", f"/docente/estudiantes/{self.sofia}", "carolina.fuentes",
                                     {"curso_id": self.b["curso"]}).status_code, 422)
        nuevo = self.llamar("PATCH", f"/docente/estudiantes/{self.sofia}", "carolina.fuentes",
                            {"apoderado_correo": "tia@correo.cl", "apoderado_nombre": "Tía Sofía"})
        self.assertEqual(nuevo.status_code, 200, nuevo.text)
        self.assertTrue(nuevo.json()["apoderado"]["codigo"])
        self.assertEqual(self.llamar("GET", "/paquete", "andres.morales").json()["estudiante_ids"], [])   # ya no es su hijo
        quitar = self.llamar("PATCH", f"/docente/estudiantes/{self.sofia}", "carolina.fuentes", {"quitar_apoderado": True})
        self.assertEqual(quitar.status_code, 200)
        self.assertIsNone(self.repo.estudiante(self.sofia)["apoderado_id"])
        self.assertEqual(self.llamar("PATCH", f"/docente/estudiantes/{self.sofia}", "carolina.fuentes", {}).status_code, 422)

    def test_la_docente_reinicia_el_acceso_de_su_apoderado(self):
        r = self.llamar("POST", f"/docente/usuarios/{self.andres}/invitacion", "carolina.fuentes")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.ingresar("andres.morales").status_code, 401)
        self.assertEqual(self.activar(correo("andres.morales"), r.json()["codigo"]).status_code, 200)

    def test_campos_desconocidos_se_rechazan(self):
        r = self.llamar("PATCH", f"/docente/estudiantes/{self.sofia}", "carolina.fuentes", {"rol": "admin"})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(self.repo.usuario_por_id(self.sofia)["rol"], "estudiante")


# ======================================================================================================
class PruebasElTelefonoOlvida(BaseAdmin):
    """Lo que el colegio retira (baja, cambio de curso, curso reasignado) también debe desaparecer del teléfono."""

    def setUp(self):
        super().setUp()
        import shutil
        import tempfile
        from models.datos.local import BaseDatosLocal
        self.carpeta_local = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.carpeta_local, True)
        self.local = BaseDatosLocal(self.carpeta_local / "local.db")
        self.cuentas = Cuentas(self.repo)

    def descargar(self, usuario: str):
        fila = self.repo.usuario_por_correo(correo(usuario))
        from models.modelos import Usuario
        yo = Usuario.desde_fila(fila)
        self.assertTrue(self.local.aplicar_paquete(self.repo.paquete_para(yo)))
        return yo

    def test_estudiante_dado_de_baja_desaparece_con_sus_notas(self):
        docente = self.descargar("carolina.fuentes")
        self.assertTrue(self.local.estudiantes_de_curso(self.curso_de_carolina()))
        self.assertTrue(self.local.bd.valor("SELECT COUNT(*) FROM calificaciones WHERE estudiante_id = ?", (self.sofia,)))
        self.cuentas.cambiar_cuenta(docente, self.sofia, activo=False)
        self.descargar("carolina.fuentes")
        self.assertNotIn(self.sofia, [f["id"] for f in self.local.estudiantes_de_curso(self.curso_de_carolina())])
        for tabla in ("calificaciones", "refuerzos", "intentos"):
            self.assertEqual(self.local.bd.valor(f"SELECT COUNT(*) FROM {tabla} WHERE estudiante_id = ?", (self.sofia,)), 0, tabla)
        self.assertEqual(self.repo.bd.valor("SELECT COUNT(*) FROM calificaciones WHERE estudiante_id = ?", (self.sofia,)) > 0, True)
        self.cuentas.cambiar_cuenta(docente, self.sofia, activo=True)           # reactivar la trae de vuelta
        self.descargar("carolina.fuentes")
        self.assertIn(self.sofia, [f["id"] for f in self.local.estudiantes_de_curso(self.curso_de_carolina())])

    def test_el_apoderado_deja_de_ver_al_hijo_que_ya_no_es_suyo(self):
        docente = self.descargar("carolina.fuentes")
        self.descargar("andres.morales")
        self.assertEqual([h["id"] for h in self.local.hijos_de_apoderado(self.andres)], [self.sofia])
        self.cuentas.cambiar_estudiante(docente, self.sofia, apoderado_correo="tia@correo.cl", apoderado_nombre="Tía Sofía")
        self.descargar("andres.morales")
        self.assertEqual(self.local.hijos_de_apoderado(self.andres), [])
        self.assertEqual(self.local.bd.valor("SELECT COUNT(*) FROM calificaciones WHERE estudiante_id = ?", (self.sofia,)), 0)

    def test_el_curso_reasignado_deja_de_aparecer_en_el_telefono_de_la_docente(self):
        self.descargar("carolina.fuentes")
        nueva = self.persona("nueva.docente", "docente", 1)
        admin = self.descargar("admin.a")
        self.cuentas.actualizar_curso(admin, self.curso_de_carolina(), docente_id=nueva)
        self.descargar("carolina.fuentes")
        self.assertEqual(self.local.cursos_de_docente(self.carolina), [])

    def test_un_estudiante_movido_a_otra_docente_sale_del_telefono_de_la_anterior(self):
        docente = self.descargar("carolina.fuentes")
        otra = self.persona("otra.docente", "docente", 1)
        curso_otra = self.curso(otra, 1, "8° A")
        admin = self.descargar("admin.a")
        self.cuentas.cambiar_estudiante(admin, self.sofia, curso_id=curso_otra)
        self.descargar("carolina.fuentes")
        self.assertNotIn(self.sofia, [f["id"] for f in self.local.estudiantes_de_curso(self.curso_de_carolina())])
        self.assertEqual(docente.id, self.carolina)


class PruebasListaDeBajas(BaseAdmin):
    def test_la_docente_ve_y_reactiva_a_sus_estudiantes_dados_de_baja(self):
        self.assertEqual(self.llamar("GET", "/docente/estudiantes/bajas", "carolina.fuentes").json(), [])
        self.llamar("PATCH", f"/docente/estudiantes/{self.sofia}", "carolina.fuentes", {"activo": False})
        bajas = self.llamar("GET", "/docente/estudiantes/bajas", "carolina.fuentes").json()
        self.assertEqual([b["id"] for b in bajas], [self.sofia])
        self.assertEqual(set(bajas[0]), {"id", "nombre", "correo", "curso_id", "curso"})
        self.assertEqual(self.llamar("GET", "/docente/estudiantes/bajas", "admin.a").status_code, 403)
        self.assertEqual(self.llamar("GET", "/docente/estudiantes/bajas", "andres.morales").status_code, 403)
        self.llamar("PATCH", f"/docente/estudiantes/{self.sofia}", "carolina.fuentes", {"activo": True})
        self.assertEqual(self.llamar("GET", "/docente/estudiantes/bajas", "carolina.fuentes").json(), [])

    def test_no_ve_las_bajas_de_otras_docentes_ni_de_otros_colegios(self):
        self.llamar("PATCH", f"/admin/usuarios/{self.b['estudiante']}", "admin.b", {"activo": False})
        self.assertEqual(self.llamar("GET", "/docente/estudiantes/bajas", "carolina.fuentes").json(), [])
        self.assertEqual([b["id"] for b in self.llamar("GET", "/docente/estudiantes/bajas", "docente.b").json()],
                         [self.b["estudiante"]])


@unittest.skipUnless(HAY_API, "FastAPI no está instalado")
class PruebasConsola(unittest.TestCase):
    def ejecutar(self, *argumentos: str, env=None) -> tuple[int, str]:
        import shutil
        import tempfile
        carpeta = tempfile.mkdtemp()
        entorno = {"TUTOR_DATOS": carpeta, **(env or {})}
        salida = io.StringIO()
        try:
            with mock.patch.dict(os.environ, entorno), contextlib.redirect_stdout(salida):
                codigo = consola_crear_usuario(list(argumentos))
        finally:
            shutil.rmtree(carpeta, ignore_errors=True)
        return codigo, salida.getvalue()

    def test_crea_cuentas_con_invitacion_y_muestra_el_codigo_una_vez(self):
        codigo, texto = self.ejecutar("superadmin", "plataforma@x.cl", "Equipo Plataforma", "--invitacion")
        self.assertEqual(codigo, 0, texto)
        self.assertIn("CÓDIGO DE INVITACIÓN:", texto)
        coincide = [p for p in texto.split() if CodigosInvitacion.tiene_formato(p) and "-" in p]
        self.assertEqual(len(coincide), 1)

    def test_un_admin_necesita_colegio(self):
        codigo, texto = self.ejecutar("admin", "dir@x.cl", "Dirección Colegio", "--invitacion")
        self.assertEqual(codigo, 1)
        self.assertIn("colegio", texto.lower())
        codigo, texto = self.ejecutar("admin", "dir@x.cl", "Dirección Colegio", "--invitacion", "--colegio-id", "1")
        self.assertEqual(codigo, 0, texto)                    # el colegio 1 existe en la base de demostración
        self.assertIn("CÓDIGO DE INVITACIÓN:", texto)


if __name__ == "__main__":
    unittest.main()
