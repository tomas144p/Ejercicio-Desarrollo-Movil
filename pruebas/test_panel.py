"""
Pruebas del panel web de administración.

- Servido por la API con cabeceras de seguridad estrictas y solo con sus tres archivos.
- Sin código «inline», sin recursos de otros sitios y sin formas inseguras de escribir en la página.
- Punta a punta (opcional): se abre el panel REAL en jsdom contra un servidor real y se recorren los flujos de
  administrador y superadministradora. Necesita Node y ``npm install`` dentro de ``pruebas/panel``; si no, se omite.
"""

from __future__ import annotations

import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(AQUI))

from test_backend import CLAVE, HAY_API, BaseApi, ahora, correo  # noqa: E402

if HAY_API:
    from backend.ajustes import Ajustes  # noqa: E402
    from backend.app import crear_app  # noqa: E402
    from fastapi.testclient import TestClient  # noqa: E402

PANEL = RAIZ / "backend" / "panel_web"


class PruebasPanelEstatico(BaseApi):
    def test_el_panel_se_sirve_con_cabeceras_de_seguridad(self):
        for ruta, tipo in (("/panel", "text/html"), ("/panel/", "text/html"), ("/panel/panel.js", "text/javascript"),
                           ("/panel/panel.css", "text/css")):
            r = self.cliente.get(ruta)
            self.assertEqual(r.status_code, 200, ruta)
            self.assertTrue(r.headers["content-type"].startswith(tipo), (ruta, r.headers["content-type"]))
            self.assertEqual(r.headers["cache-control"], "no-store")
            self.assertEqual(r.headers["x-frame-options"], "DENY")
            self.assertEqual(r.headers["referrer-policy"], "no-referrer")
        csp = self.cliente.get("/panel").headers["content-security-policy"]
        for regla in ("default-src 'none'", "script-src 'self'", "style-src 'self'", "connect-src 'self'",
                      "frame-ancestors 'none'", "base-uri 'none'"):
            self.assertIn(regla, csp)
        self.assertNotIn("unsafe-inline", csp)
        self.assertNotIn("unsafe-eval", csp)

    def test_solo_se_sirven_los_archivos_del_panel(self):
        for ruta in ("/panel/otro.txt", "/panel/..%2Fapp.py", "/panel/%2e%2e/app.py", "/panel/index.html.bak",
                     "/panel/panel_web", "/panel/__init__.py"):
            self.assertEqual(self.cliente.get(ruta).status_code, 404, ruta)
        self.assertNotIn("jwt", self.cliente.get("/panel/panel.js").text.lower().replace("jwt_", ""))

    def test_el_panel_se_puede_apagar(self):
        ajustes = Ajustes(carpeta_datos=self.carpeta / "sin_panel", panel_activo=False).validado()
        app = crear_app(ajustes)
        try:
            with TestClient(app) as cliente:
                self.assertEqual(cliente.get("/panel").status_code, 404)
                self.assertEqual(cliente.get("/salud").status_code, 200)
        finally:
            app.state.gestor.servidor.bd.cerrar()

    def test_la_pagina_no_tiene_codigo_inline_ni_recursos_externos(self):
        html = (PANEL / "index.html").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"<script(?![^>]*\bsrc=)", html), [], "script inline")
        self.assertNotRegex(html, r"<style|\sstyle=|\son[a-z]+\s*=", "estilos o manejadores inline")
        enlaces = re.findall(r'(?:src|href)="([^"]+)"', html)
        self.assertTrue(enlaces and all(e.startswith("/panel/") for e in enlaces), enlaces)
        js, css = (PANEL / "panel.js").read_text(encoding="utf-8"), (PANEL / "panel.css").read_text(encoding="utf-8")
        self.assertNotRegex(css, r"@import|url\(\s*['\"]?https?:", "recursos externos en el CSS")
        self.assertNotRegex(js, r"https?://", "direcciones externas en el JS")

    def test_el_javascript_no_usa_formas_inseguras_de_escribir_en_la_pagina(self):
        js = (PANEL / "panel.js").read_text(encoding="utf-8")
        for peligro in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function",
                        "setAttribute(\"style\"", "localStorage", "dangerouslySet"):
            self.assertNotIn(peligro, js, peligro)
        self.assertNotIn("clave_hash", js)

    def test_la_lista_de_personas_acepta_un_limite_acotado(self):
        admin = self.persona("admin.a", "admin", 1)
        self.assertTrue(admin)
        cab = self.cabeceras("admin.a")
        todas = self.cliente.get("/admin/usuarios", headers=cab)
        self.assertEqual(todas.status_code, 200)
        dos = self.cliente.get("/admin/usuarios?limite=2", headers=cab)
        self.assertEqual(len(dos.json()), 2)
        self.assertEqual(self.cliente.get("/admin/usuarios?limite=0", headers=cab).status_code, 422)
        self.assertEqual(self.cliente.get("/admin/usuarios?limite=1001", headers=cab).status_code, 422)
        self.assertGreaterEqual(len(self.cliente.get("/admin/usuarios?limite=1000", headers=cab).json()), len(todas.json()))

    def test_el_panel_no_abre_datos_sin_sesion(self):
        for ruta in ("/admin/usuarios", "/admin/cursos", "/admin/colegios"):
            self.assertEqual(self.cliente.get(ruta).status_code, 401, ruta)


def _hay_jsdom() -> bool:
    return bool(shutil.which("node")) and (AQUI / "panel" / "node_modules" / "jsdom").is_dir()


@unittest.skipUnless(HAY_API, "FastAPI no está instalado")
@unittest.skipUnless(_hay_jsdom(), "Para la prueba de navegador: cd pruebas/panel && npm install (necesita Node)")
class PruebaPanelEnNavegador(BaseApi):
    def setUp(self):
        super().setUp()
        import uvicorn
        self.persona("admin.a", "admin", 1)
        self.persona("super", "superadmin", None)
        base = {"colegio_id": 1, "rol": "estudiante", "creado_en": ahora(), "version": "0.1.0", "plataforma": "android",
                "pantalla": "leccion", "tipo": "KeyError", "mensaje": "<b>negrita</b> curso_id",
                "traza": "views/leccion_screen.py:10 en abrir", "huella": "aaaaaaaaaaaa"}
        for n in range(3):                                   # una causa frecuente y otra aislada
            self.repo.registrar_error_app({**base, "codigo": f"e2e-a-{n:04d}-codigo"})
        self.repo.registrar_error_app({**base, "codigo": "e2e-b-0001-codigo", "tipo": "ValueError", "huella": "bbbbbbbbbbbb",
                                       "mensaje": "otro", "pantalla": "docente"})
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.puerto = s.getsockname()[1]
        self.servidor = uvicorn.Server(uvicorn.Config(self.app, host="127.0.0.1", port=self.puerto, log_level="error"))
        self.hilo = threading.Thread(target=self.servidor.run, daemon=True)
        self.hilo.start()
        inicio = time.time()
        while not self.servidor.started and time.time() - inicio < 10:
            time.sleep(0.05)
        self.assertTrue(self.servidor.started, "el servidor de prueba no arrancó")

    def tearDown(self):
        self.servidor.should_exit = True
        self.hilo.join(timeout=10)
        super().tearDown()

    def test_recorrido_completo_del_panel(self):
        proceso = subprocess.run(
            ["node", str(AQUI / "panel" / "e2e.js"), f"http://127.0.0.1:{self.puerto}", correo("admin.a"), CLAVE,
             correo("super")], capture_output=True, text=True, timeout=240, cwd=str(AQUI / "panel"))
        self.assertEqual(proceso.returncode, 0, f"\n--- salida ---\n{proceso.stdout}\n--- errores ---\n{proceso.stderr}")
        self.assertIn("TODO BIEN", proceso.stdout)


if __name__ == "__main__":
    unittest.main()
