"""
Ventanas emergentes para activar una cuenta con un código y para que la docente gestione a sus estudiantes y apoderados.

Todo lo que cambia cuentas pasa por el servidor del colegio (``app.gestion`` y ``app.autenticacion``) y se hace en segundo
plano. Los mensajes de error se muestran DENTRO de la ventana, que no se cierra hasta que todo salió bien, para que la
persona pueda corregir sin volver a escribir todo.
"""

from __future__ import annotations

from kivy.metrics import dp

from models.modelos import Rol
from services.gestion_docente import MENSAJE_SIN_SERVIDOR, Codigo, ResultadoGestion
from services.validaciones import validar_clave_nueva, validar_correo
from views.componentes import Avatar, Boton, CampoTexto, Columna, Etiqueta, FilaLista, Separador, Superficie, Texto
from views.dialogos import Dialogo
from views.estilo import Paleta, Tipografia, color

ACENTO_DOCENTE = Paleta.POR_ROL[Rol.DOCENTE][0]


def _iniciales(nombre: str) -> str:
    return "".join(p[0] for p in nombre.split()[:2]).upper() or "?"


def copiar(app, texto: str, aviso: str) -> None:
    """Copia al portapapeles (para pegar en WhatsApp o un correo). Si el dispositivo no lo permite, lo dice."""
    try:
        from kivy.core.clipboard import Clipboard
        Clipboard.copy(texto)
    except Exception:       # noqa: BLE001 - depende del sistema: no debe romper la app
        app.notificador.mostrar("Este dispositivo no permite copiar. Anota el código en papel.", "aviso")
        return
    app.notificador.mostrar(aviso, "exito")


class _Formulario:
    """Línea de error/progreso y control de «ya se está enviando» para los diálogos con formulario."""

    def __init__(self, app):
        self.app = app
        self.error = Texto("", tamano=13.5, color_texto=Paleta.ROJO)
        self.ocupado = False
        self.dialogo: Dialogo | None = None

    def mostrar_error(self, texto: str) -> None:
        self.error.color = color(Paleta.ROJO)
        self.error.cambiar(texto)

    def mostrar_progreso(self, texto: str) -> None:
        self.error.color = color(Paleta.TINTA_SUAVE)
        self.error.cambiar(texto)

    def lanzar(self, trabajo, al_terminar, progreso: str) -> bool:
        """Ejecuta ``trabajo`` en segundo plano. Siempre devuelve False: el diálogo lo cierra ``al_terminar`` si todo salió bien."""
        if self.ocupado:
            return False
        self.ocupado = True
        self.mostrar_progreso(progreso)

        def listo(resultado):
            self.ocupado = False
            al_terminar(resultado)

        def fallo(error):
            self.ocupado = False
            self.mostrar_error(f"Ocurrió un problema inesperado: {error}")

        self.app.ejecutor_datos.enviar(trabajo, listo, fallo)
        return False

    def cerrar(self) -> None:
        if self.dialogo is not None:
            self.dialogo.dismiss()


def _sin_servidor(app) -> bool:
    """Si la app no está conectada a un servidor del colegio, lo explica y devuelve True."""
    if app.gestion.disponible:
        return False
    Dialogo.informar("Falta el servidor del colegio", MENSAJE_SIN_SERVIDOR, icono="server", tinta=Paleta.AMBAR)
    return True


# ======================================================================================================
# Activar una cuenta con el código de invitación
# ======================================================================================================
def abrir_activacion(app, correo: str = "") -> None:
    formulario = _Formulario(app)
    campo_correo = CampoTexto("Tu correo", icono="mail", texto=correo)
    campo_correo.entrada.input_type = "mail"
    campo_codigo = CampoTexto("Código (por ejemplo ABCDE-FGHJK)")
    campo_clave = CampoTexto("Elige tu contraseña", icono="lock", clave=True)
    campo_repite = CampoTexto("Repite tu contraseña", icono="lock", clave=True, al_confirmar=lambda: activar())

    contenido = Columna(spacing=dp(10))
    for widget in (campo_correo, campo_codigo, campo_clave, campo_repite):
        contenido.add_widget(widget)
    contenido.add_widget(Texto("Mínimo 10 caracteres, con letras y números. Solo tú la conocerás: ni el colegio la ve.",
                               tamano=12.5, color_texto=Paleta.TINTA_SUAVE))
    contenido.add_widget(formulario.error)

    def activar():
        try:
            correo_valido = validar_correo(campo_correo.texto)
            codigo = campo_codigo.texto.strip()
            if not codigo:
                raise ValueError("Escribe el código que te dio tu colegio.")
            clave = validar_clave_nueva(campo_clave.texto)
            if clave != campo_repite.texto:
                raise ValueError("Las dos contraseñas no son iguales.")
        except ValueError as error:
            formulario.mostrar_error(str(error))
            return False

        def terminado(resultado):
            if resultado.exito:
                formulario.cerrar()
                app.iniciar_sesion(resultado)
            else:
                formulario.mostrar_error(resultado.mensaje)

        return formulario.lanzar(lambda: app.autenticacion.activar_cuenta(correo_valido, codigo, clave, True),
                                 terminado, "Activando tu cuenta…")

    formulario.dialogo = Dialogo(
        "Activar mi cuenta", "Tu colegio te entregó un código de un solo uso. Con él eliges tu propia contraseña.",
        contenido=contenido, icono="key-round", cerrar_al_tocar_fuera=False,
        botones=[("Cancelar", None, "contorno"), ("Activar y entrar", activar, "primario", "log-in")])
    formulario.dialogo.open()


# ======================================================================================================
# Mostrar códigos de invitación (una sola vez)
# ======================================================================================================
def _tarjeta_codigo(app, codigo: Codigo) -> Superficie:
    rol = "Estudiante" if codigo.rol == Rol.ESTUDIANTE else "Apoderado/a"
    tarjeta = Superficie(padding=dp(14), spacing=dp(8), radio=dp(14), color_fondo=color(Paleta.AZUL_SUAVE),
                         color_borde=color(Paleta.LINEA))
    tarjeta.add_widget(Texto(f"{codigo.para} · {rol}", tamano=14, fuente=Tipografia.MEDIA))
    tarjeta.add_widget(Texto(codigo.correo, tamano=12.5, color_texto=Paleta.TINTA_SUAVE))
    tarjeta.add_widget(Texto(codigo.codigo, tamano=28, fuente=Tipografia.SEMI, color_texto=Paleta.AZUL, alinear="center"))
    vence = codigo.mensaje.split("vence el ")[-1].split(")")[0] if "vence el " in codigo.mensaje else ""
    tarjeta.add_widget(Texto(f"Sirve una sola vez{f' · vence el {vence}' if vence else ''}", tamano=12,
                             color_texto=Paleta.TINTA_SUAVE, alinear="center"))
    tarjeta.add_widget(Boton("Copiar mensaje para enviar", icono="clipboard-copy", variante="contorno", alto=42, tamano=13.5,
                             al_presionar=lambda: copiar(app, codigo.mensaje,
                                                         "Mensaje copiado. Pégalo en WhatsApp o en un correo.")))
    return tarjeta


def mostrar_codigos(app, resultado: ResultadoGestion, titulo: str) -> None:
    """Los códigos solo se muestran ahora: el servidor guarda únicamente su huella."""
    contenido = Columna(spacing=dp(12))
    if resultado.apoderado_existente:
        contenido.add_widget(Texto(f"{resultado.apoderado_existente} ya tenía cuenta: quedó vinculado/a y no necesita un "
                                   "código nuevo.", tamano=13.5, color_texto=Paleta.TINTA_SUAVE))
    for codigo in resultado.codigos:
        contenido.add_widget(_tarjeta_codigo(app, codigo))
    if resultado.codigos:
        contenido.add_widget(Texto("Este código se muestra solo ahora. Si se pierde, genera uno nuevo desde la ficha del "
                                   "estudiante.", tamano=12.5, color_texto=Paleta.AMBAR))
    Dialogo(titulo, "Entrega a cada persona su código. Con él elegirá su propia contraseña." if resultado.codigos else "",
            contenido=contenido, icono="ticket", tinta=Paleta.VERDE, cerrar_al_tocar_fuera=False,
            botones=[("Listo", None, "primario", "check")]).open()


# ======================================================================================================
# Agregar un estudiante (y su apoderado)
# ======================================================================================================
def abrir_estudiante_nuevo(app, curso) -> None:
    if _sin_servidor(app):
        return
    formulario = _Formulario(app)
    nombre = CampoTexto("Nombre completo del estudiante", icono="pencil")
    correo = CampoTexto("Correo del estudiante")
    correo.entrada.input_type = "mail"
    correo_apo = CampoTexto("Correo del apoderado/a (opcional)", icono="mail")
    correo_apo.entrada.input_type = "mail"
    nombre_apo = CampoTexto("Nombre del apoderado/a (si aún no tiene cuenta)", icono="pencil",
                            al_confirmar=lambda: agregar())

    contenido = Columna(spacing=dp(10))
    contenido.add_widget(nombre)
    contenido.add_widget(correo)
    contenido.add_widget(Separador())
    contenido.add_widget(Texto("Apoderado/a", tamano=14, fuente=Tipografia.MEDIA))
    contenido.add_widget(correo_apo)
    contenido.add_widget(nombre_apo)
    contenido.add_widget(Texto("Si ese apoderado/a ya tiene cuenta, solo se vincula. Si no, se crea y recibe su propio "
                               "código.", tamano=12.5, color_texto=Paleta.TINTA_SUAVE))
    contenido.add_widget(formulario.error)

    def agregar():
        nombre_estudiante = nombre.texto.strip()
        if len(nombre_estudiante) < 3:
            formulario.mostrar_error("Escribe el nombre completo del estudiante.")
            return False

        def terminado(resultado: ResultadoGestion):
            if not resultado.exito:
                formulario.mostrar_error(resultado.mensaje)
                return
            formulario.cerrar()
            app.datos_modificados()
            mostrar_codigos(app, resultado, resultado.mensaje)

        return formulario.lanzar(
            lambda: app.gestion.agregar_estudiante(app.usuario, int(curso.id), nombre_estudiante, correo.texto,
                                                   correo_apo.texto, nombre_apo.texto),
            terminado, "Creando la cuenta…")

    formulario.dialogo = Dialogo(f"Agregar a {curso.nombre}", contenido=contenido, icono="user-plus",
                                 tinta=ACENTO_DOCENTE, cerrar_al_tocar_fuera=False,
                                 botones=[("Cancelar", None, "contorno"), ("Agregar", agregar, "primario", "user-plus")])
    formulario.dialogo.open()


# ======================================================================================================
# Gestionar a un estudiante ya existente
# ======================================================================================================
def abrir_gestion_estudiante(app, ficha) -> None:
    """Menú de acciones sobre un estudiante: apoderado, códigos, curso y baja."""
    if _sin_servidor(app):
        return
    estudiante = ficha.estudiante
    primero = estudiante.nombre.split()[0]
    cursos = app.datos.cursos_docente()
    contenido = Columna(spacing=0)
    dialogo: Dialogo | None = None

    def hacer(accion):
        def ejecutar():
            dialogo.dismiss()
            accion()
        return ejecutar

    def fila(titulo, subtitulo, icono, accion, tinta=ACENTO_DOCENTE):
        from views.componentes import InsigniaIcono
        contenido.add_widget(FilaLista(titulo, subtitulo, inicio=InsigniaIcono(icono, tinta=tinta, lado=38),
                                       al_presionar=hacer(accion)))

    fila("Cambiar apoderado/a", ficha.apoderado_nombre or "Todavía no tiene apoderado/a", "users",
         lambda: abrir_cambiar_apoderado(app, ficha))
    fila(f"Código nuevo para {primero}", "Si olvidó su contraseña o nunca activó su cuenta", "key-round",
         lambda: _confirmar_codigo(app, estudiante.id, Rol.ESTUDIANTE, estudiante.nombre))
    if ficha.apoderado_id:
        fila("Código nuevo para su apoderado/a", ficha.apoderado_nombre, "key-round",
             lambda: _confirmar_codigo(app, ficha.apoderado_id, Rol.APODERADO, ficha.apoderado_nombre))
    otros_cursos = [c for c in cursos if ficha.curso is None or int(c.id) != int(ficha.curso.id)]
    if otros_cursos:
        fila("Cambiar de curso", f"Ahora en {ficha.curso.nombre}" if ficha.curso else "", "arrow-left-right",
             lambda: _elegir_curso(app, ficha, otros_cursos))
    if ficha.apoderado_id:
        fila("Quitar apoderado/a", "El estudiante quedará sin apoderado/a", "user-minus",
             lambda: _confirmar_quitar_apoderado(app, ficha))
    fila(f"Dar de baja a {primero}", "Deja de aparecer en tus listas. Sus datos se conservan.", "user-x",
         lambda: _confirmar_baja(app, ficha), tinta=Paleta.ROJO)

    dialogo = Dialogo(f"Gestionar a {estudiante.nombre}", contenido=contenido, icono="settings", tinta=ACENTO_DOCENTE,
                      botones=[("Cerrar", None, "contorno")])
    dialogo.open()


def _ejecutar_simple(app, trabajo, exito_texto: str | None = None, volver_a_lista: bool = False) -> None:
    """Gestión sin formulario: se ejecuta, se avisa el resultado y se refresca la pantalla."""
    def terminado(resultado: ResultadoGestion):
        if not resultado.exito:
            Dialogo.informar("No se pudo hacer", resultado.mensaje, icono="circle-alert", tinta=Paleta.ROJO)
            return
        app.datos_modificados()
        if resultado.codigos:
            mostrar_codigos(app, resultado, "Código nuevo")
        else:
            app.notificador.mostrar(exito_texto or resultado.mensaje, "exito")
        if volver_a_lista:
            app.volver()

    app.notificador.mostrar("Un momento…", "info")
    app.ejecutor_datos.enviar(trabajo, terminado,
                              lambda error: app.notificador.mostrar(f"Ocurrió un problema inesperado: {error}", "error"))


def _confirmar_codigo(app, usuario_id: int, rol: str, nombre: str) -> None:
    Dialogo.confirmar(
        f"Código nuevo para {nombre}",
        "Se generará un código de un solo uso. Su contraseña actual dejará de servir y elegirá una nueva al entrar.",
        "Generar código", lambda: _ejecutar_simple(app, lambda: app.gestion.codigo_nuevo(app.usuario, usuario_id, rol)),
        icono="key-round", tinta=ACENTO_DOCENTE)


def _confirmar_baja(app, ficha) -> None:
    nombre = ficha.estudiante.nombre
    Dialogo.confirmar(
        f"¿Dar de baja a {nombre}?",
        "Dejará de aparecer en tus listas y en las de su apoderado/a, y no podrá ingresar. No se borra nada: sus notas se "
        "conservan y puedes reactivarlo/a cuando quieras desde «Estudiantes dados de baja».",
        "Dar de baja", lambda: _ejecutar_simple(app, lambda: app.gestion.dar_de_baja(app.usuario, ficha.estudiante.id),
                                                f"{nombre} fue dado/a de baja.", volver_a_lista=True),
        peligro=True, icono="user-x")


def _confirmar_quitar_apoderado(app, ficha) -> None:
    Dialogo.confirmar(
        "¿Quitar al apoderado/a?", f"{ficha.apoderado_nombre} dejará de ver a {ficha.estudiante.nombre.split()[0]}. "
        "Su cuenta no se borra.", "Quitar",
        lambda: _ejecutar_simple(app, lambda: app.gestion.quitar_apoderado(app.usuario, ficha.estudiante.id)),
        peligro=True, icono="user-minus")


def _elegir_curso(app, ficha, cursos) -> None:
    contenido = Columna(spacing=0)
    dialogo: Dialogo | None = None

    def elegir(curso):
        dialogo.dismiss()
        _ejecutar_simple(app, lambda: app.gestion.cambiar_curso(app.usuario, ficha.estudiante.id, int(curso.id)),
                         f"{ficha.estudiante.nombre.split()[0]} ahora está en {curso.nombre}.", volver_a_lista=True)

    for curso in cursos:
        contenido.add_widget(FilaLista(curso.nombre, curso.nivel, al_presionar=lambda c=curso: elegir(c)))
    dialogo = Dialogo("Cambiar de curso", f"¿A qué curso pasa {ficha.estudiante.nombre.split()[0]}?", contenido=contenido,
                      icono="arrow-left-right", tinta=ACENTO_DOCENTE, botones=[("Cancelar", None, "contorno")])
    dialogo.open()


def abrir_cambiar_apoderado(app, ficha) -> None:
    formulario = _Formulario(app)
    correo = CampoTexto("Correo del apoderado/a", icono="mail")
    correo.entrada.input_type = "mail"
    nombre = CampoTexto("Nombre (solo si aún no tiene cuenta)", icono="pencil", al_confirmar=lambda: guardar())
    contenido = Columna(spacing=dp(10))
    contenido.add_widget(correo)
    contenido.add_widget(nombre)
    contenido.add_widget(Texto("Si ya tiene cuenta, solo se vincula a este estudiante. Si no, se crea y recibe un código.",
                               tamano=12.5, color_texto=Paleta.TINTA_SUAVE))
    contenido.add_widget(formulario.error)

    def guardar():
        def terminado(resultado: ResultadoGestion):
            if not resultado.exito:
                formulario.mostrar_error(resultado.mensaje)
                return
            formulario.cerrar()
            app.datos_modificados()
            if resultado.codigos or resultado.apoderado_existente:
                mostrar_codigos(app, resultado, resultado.mensaje)
            else:
                app.notificador.mostrar(resultado.mensaje, "exito")

        return formulario.lanzar(lambda: app.gestion.cambiar_apoderado(app.usuario, ficha.estudiante.id, correo.texto,
                                                                       nombre.texto), terminado, "Guardando…")

    formulario.dialogo = Dialogo(f"Apoderado/a de {ficha.estudiante.nombre.split()[0]}", contenido=contenido,
                                 icono="users", tinta=ACENTO_DOCENTE, cerrar_al_tocar_fuera=False,
                                 botones=[("Cancelar", None, "contorno"), ("Guardar", guardar, "primario", "check")])
    formulario.dialogo.open()


# ======================================================================================================
# Estudiantes dados de baja (para reactivarlos)
# ======================================================================================================
def abrir_bajas(app) -> None:
    if _sin_servidor(app):
        return
    contenido = Columna(spacing=0)
    contenido.add_widget(Texto("Buscando…", tamano=14, color_texto=Paleta.TINTA_SUAVE))
    dialogo = Dialogo("Estudiantes dados de baja", "No aparecen en tus listas, pero sus datos se conservan.",
                      contenido=contenido, icono="archive", tinta=ACENTO_DOCENTE, botones=[("Cerrar", None, "contorno")])
    dialogo.open()

    def reactivar(estudiante: dict):
        dialogo.dismiss()
        _ejecutar_simple(app, lambda: app.gestion.reactivar(app.usuario, int(estudiante["id"])),
                         f"{estudiante['nombre']} fue reactivado/a.")

    def listo(resultado: ResultadoGestion):
        contenido.clear_widgets()
        if not resultado.exito:
            contenido.add_widget(Texto(resultado.mensaje, tamano=14, color_texto=Paleta.ROJO))
            return
        if not resultado.datos:
            contenido.add_widget(Texto("No hay estudiantes dados de baja.", tamano=14, color_texto=Paleta.TINTA_SUAVE))
            return
        for estudiante in resultado.datos:
            contenido.add_widget(FilaLista(
                estudiante["nombre"], estudiante["curso"], flecha=False,
                inicio=Avatar(_iniciales(estudiante["nombre"]), tinta=Paleta.TINTA_TENUE, lado=38),
                fin=Boton("Reactivar", icono="archive-restore", variante="contorno", alto=36, tamano=12.5,
                          size_hint_x=None, width=dp(118), al_presionar=lambda e=estudiante: reactivar(e))))

    app.ejecutor_datos.enviar(lambda: app.gestion.dados_de_baja(app.usuario), listo,
                              lambda error: listo(ResultadoGestion(False, f"Ocurrió un problema inesperado: {error}")))
