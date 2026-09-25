import os
import re

from kivy.app import App
from kivy.metrics import dp
from kivy.properties import StringProperty, BooleanProperty, ListProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.textinput import TextInput
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line
from kivy.clock import Clock
from kivy.core.text import LabelBase

# ------------------------------------------------------------
# Fuentes
# ------------------------------------------------------------

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

LabelBase.register(
    name="Poppins",
    fn_regular=os.path.join(FONT_DIR, "Poppins-Regular.ttf"),
    fn_bold=os.path.join(FONT_DIR, "Poppins-Bold.ttf"),
)
LabelBase.register(
    name="Emoji",
    fn_regular=os.path.join(FONT_DIR, "NotoEmoji-Regular.ttf"),
)

# Rango de códigos Unicode que cubren los emojis usados en la app. El texto
# que cae dentro de estos rangos se envuelve con [font=Emoji] para que se
# dibuje con la fuente que sí tiene esos glifos; el resto sigue con Poppins.
_EMOJI_RANGES = (
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U00002190-\U000021FF"
    "\U00002B00-\U00002BFF"
    "\U00002100-\U0000214F"
    "\U000025A0-\U000025FF"
    "\U0001F1E6-\U0001F1FF"
    "\U0000FE0F\U0000200D"
)
_EMOJI_PATTERN = re.compile(f"[{_EMOJI_RANGES}]+")


def with_emoji_font(text):
    """Envuelve los emojis de un texto para que usen la fuente Emoji."""
    text = str(text)
    return _EMOJI_PATTERN.sub(lambda m: f"[font=Emoji]{m.group(0)}[/font]", text)


# ------------------------------------------------------------
# Temas (paleta de colores centralizada)
# ------------------------------------------------------------
# Definir los colores como constantes permite reutilizarlos en todas las
# pantallas y mantener una identidad visual coherente. Si más adelante se
# quiere cambiar el tema, basta con editar estos valores.

BG = "#F8FAFC"        # Fondo general de la app
WHITE = "#FFFFFF"     # Superficie de tarjetas
TEXT = "#0F172A"      # Texto principal (casi negro)
MUTED = "#64748B"     # Texto secundario / descripciones
BLUE = "#2563EB"      # Acento principal (estudiante)
PURPLE = "#7C3AED"    # Acento apoderado
GREEN = "#10B981"     # Éxito / online
ORANGE = "#F59E0B"    # Advertencia
RED = "#EF4444"       # Alerta / error
BORDER = "#E2E8F0"    # Bordes suaves de tarjetas


def rgba(hex_color, alpha=1):
    """Convierte un color hexadecimal (#RRGGBB) a una tupla RGBA de Kivy."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4)) + (alpha,)


class Card(BoxLayout):
    """BoxLayout con fondo redondeado y, opcionalmente, borde.

    Se usa como bloque visual para agrupar contenido (tarjetas, banners,
    estadísticas, etc.). El fondo se dibuja en el canvas 'before' para que
    quede por detrás de los hijos.
    """

    def __init__(self, bg=WHITE, radius=16, border=None, **kwargs):
        # bg: color de fondo, radius: radio de las esquinas, border: color del borde
        # kwargs: argumentos adicionales que se pasan al BoxLayout (padding, etc.)
        super().__init__(**kwargs)
        self.padding = dp(16)  # Espaciado interno por defecto
        with self.canvas.before: # type: ignore
            # Fondo redondeado
            Color(*rgba(bg))
            self.rect = RoundedRectangle(pos=self.pos, size=self.size,
                                        radius=[dp(radius)])
            # Borde opcional (solo si se especifica color de borde)
            if border:
                Color(*rgba(border))
                self.line = Line(
                    rounded_rectangle=(self.x, self.y, self.width, self.height, dp(radius)),
                    width=1
                )
        # Se redibuja cuando cambian posición o tamaño
        self.bind(pos=self._update, size=self._update)  # type: ignore

    def _update(self, *_):
        """Sincroniza el rectángulo (y el borde) con la posición/tamaño actuales."""
        self.rect.pos = self.pos
        self.rect.size = self.size
        if hasattr(self, "line"):
            self.line.rounded_rectangle = (
                self.x, self.y, self.width, self.height, dp(16)
            )


def lbl(text="", size=16, color=TEXT, bold=False, **kwargs):
    # Valores por defecto que pueden ser sobrescritos por kwargs.
    kwargs.setdefault("halign", "left")
    kwargs.setdefault("valign", "middle")
    kwargs.setdefault("text_size", (None, None))
    kwargs.setdefault("font_name", "Poppins")
    kwargs.setdefault("markup", True)
    return Label(
        text=with_emoji_font(text), font_size=dp(size), color=rgba(color),
        bold=bold, **kwargs
    )

def make_button(text, bg=BLUE, color=WHITE, height=46, radius=12, **kwargs):
    """Botón con fondo redondeado y feedback visual al presionar."""
    b = Button(
        text=with_emoji_font(text), font_size=dp(14), bold=True,
        font_name="Poppins", markup=True, color=rgba(color),
        background_normal="", background_down="", background_color=(0, 0, 0, 0),
        size_hint_y=None, height=dp(height),
        **kwargs
    )
    # Fondo redondeado propio (en vez del rectángulo plano por defecto de
    # Kivy) para que combine con las tarjetas, más un leve oscurecido al
    # presionar para que se sienta interactivo.
    b._bg_color = rgba(bg)
    with b.canvas.before:  # type: ignore
        b._bg_instr = Color(*b._bg_color)
        b._bg_rect = RoundedRectangle(pos=b.pos, size=b.size, radius=[dp(radius)])

    def _update(instance, *_):
        """Mantiene el rectángulo de fondo alineado con el botón."""
        instance._bg_rect.pos = instance.pos
        instance._bg_rect.size = instance.size

    def _on_state(instance, value):
        """Oscurece el fondo mientras el botón está presionado."""
        r, g, bl, a = instance._bg_color
        if instance.disabled:
            return
        if value == "down":
            instance._bg_instr.rgba = (r * 0.85, g * 0.85, bl * 0.85, a)
        else:
            instance._bg_instr.rgba = instance._bg_color

    def _on_disabled(instance, value):
        """Atenúa el botón cuando está deshabilitado."""
        r, g, bl, a = instance._bg_color
        instance._bg_instr.rgba = (r, g, bl, a * 0.55) if value else (r, g, bl, a)

    b.bind(pos=_update, size=_update, state=_on_state, disabled=_on_disabled)  # type: ignore
    return b


def add_title(parent, title, subtitle=None):
    """Agrega un bloque de título + subtítulo opcional a un contenedor."""
    box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(82),
                    spacing=dp(4))
    box.add_widget(lbl(title, 27, TEXT, True))
    if subtitle:
        box.add_widget(lbl(subtitle, 13, MUTED))
    parent.add_widget(box)


class Header(BoxLayout):
    """Cabecera reutilizable: botón atrás + logo + título + estado online."""

    def __init__(self, app, title, back=True, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(64),
                         padding=(dp(16), dp(10)), spacing=dp(12), **kwargs)
        if back:
            # Botón pequeño para volver al login
            b = make_button("‹", "#E2E8F0", TEXT, 42, size_hint_x=None, width=dp(44))
            b.bind(on_release=lambda *_: app.go("login"))  # type: ignore
            self.add_widget(b)
        else:
            # Espaciador para mantener alineación cuando no hay botón atrás
            self.add_widget(BoxLayout(size_hint_x=None, width=dp(44)))
        # Logo pequeño (ícono de libro dentro de una tarjeta)
        logo = Card(bg="#EFF6FF", radius=12, size_hint_x=None, width=dp(44), padding=0)
        logo.add_widget(lbl("📖", 23, BLUE, True, halign="center"))
        self.add_widget(logo)
        # Título de la pantalla
        self.add_widget(lbl(title, 19, TEXT, True))
        # Botón de estado Online/Offline que permite simular la conexión
        online = make_button(
            "🟢 Online" if app.is_online else "⚪ Offline",
            GREEN if app.is_online else "#CBD5E1",
            WHITE if app.is_online else "#475569",
            36, size_hint_x=None, width=dp(98)
        )
        online.bind(on_release=lambda *_: app.toggle_online())  # type: ignore
        self.add_widget(online)


class BaseScreen(Screen):
    """Clase base para todas las pantallas: fondo + scroll reutilizables."""

    def body(self):
        """Crea el contenedor raíz con fondo pintado por canvas.

        BoxLayout no tiene background_color en Kivy, así que dibujamos el
        fondo directamente con un Rectangle en el canvas.
        """
        root = BoxLayout(orientation="vertical")
        with root.canvas.before:  # type: ignore
            bg_color = Color(*rgba(BG))
            bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(  # type: ignore
            pos=lambda instance, value: setattr(bg_rect, "pos", value),
            size=lambda instance, value: setattr(bg_rect, "size", value),
        )
        self.add_widget(root)
        return root

    def scroll(self):
        """Devuelve un ScrollView + contenedor vertical con scroll habilitado."""
        s = ScrollView()
        content = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(18),
                            size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))  # type: ignore
        s.add_widget(content)
        return s, content


# ------------------------------------------------------------
# Login
# ------------------------------------------------------------

class LoginScreen(BaseScreen):
    """Pantalla inicial: selección de perfil y cambio de estado online."""

    def on_pre_enter(self, *args):
        self.clear_widgets()
        root = self.body()
        root.padding = dp(24)

        # Bloque superior con el nombre de la app y su lema
        top = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(145),
                        spacing=dp(8))
        top.add_widget(lbl("Tutor Educa", 34, TEXT, True, halign="center"))
        top.add_widget(lbl(
            "Aprendizaje conectado entre colegio, familia y estudiante",
            15, MUTED, halign="center"
        ))
        root.add_widget(top)

        # Tarjeta principal con las opciones de ingreso
        card = Card(radius=24, padding=dp(28), orientation="vertical",
                    size_hint=(1, None), height=dp(360), spacing=dp(16))
        card.add_widget(lbl("¿Cómo quieres ingresar?", 22, TEXT, True,
                            halign="center", size_hint_y=None, height=dp(45)))
        card.add_widget(lbl("Elige el perfil para explorar el prototipo.", 14, MUTED,
                            halign="center", size_hint_y=None, height=dp(35)))

        # Botón: ingresar como apoderado
        g = make_button("👪  Ingresar como Apoderado", PURPLE, WHITE, 56)
        g.bind(on_release=lambda *_: self.manager.app.go("guardian"))  # type: ignore
        card.add_widget(g)

        # Botón: ingresar como estudiante
        st = make_button("🎓  Ingresar como Estudiante", BLUE, WHITE, 56)
        st.bind(on_release=lambda *_: self.manager.app.go("student"))  # type: ignore
        card.add_widget(st)

        # Botón: vista profesor
        te = make_button("🏫  Vista Profesor", "#0F172A", WHITE, 50)
        te.bind(on_release=lambda *_: self.manager.app.go("teacher"))  # type: ignore
        card.add_widget(te)

        # Botón para simular conexión online/offline
        offline = make_button(
            "Cambiar estado: " + ("Online" if App.get_running_app().is_online else "Offline"),  # type: ignore
            "#F1F5F9", TEXT, 44
        )
        offline.bind(on_release=lambda *_: self.manager.app.toggle_online())  # type: ignore
        card.add_widget(offline)

        root.add_widget(card)
        root.add_widget(BoxLayout())  # Espaciador flexible
        root.add_widget(lbl(
            "Prototipo educativo • 5° a 8° básico • Chile",
            12, MUTED, halign="center", size_hint_y=None, height=dp(35)
        ))


# ------------------------------------------------------------
# Guardian (apoderado)
# ------------------------------------------------------------

class GuardianScreen(BaseScreen):
    """Panel del apoderado: resumen, tareas, IA, seguimiento y avisos."""

    active_tab = StringProperty("home")

    def on_pre_enter(self, *args):
        self.render()

    def render(self):
        """Reconstruye la pantalla según la pestaña activa."""
        self.clear_widgets()
        root = self.body()
        root.add_widget(Header(self.manager.app, "Panel Apoderado", back=True))

        # Barra de pestañas horizontales
        tabs = BoxLayout(size_hint_y=None, height=dp(50),
                        padding=(dp(12), dp(6)), spacing=dp(6))
        for key, text in [("home", "Inicio"), ("tasks", "Tareas"), ("chat", "IA"),
                        ("tracking", "Seguimiento"), ("notifications", "Avisos")]:
            b = make_button(text, PURPLE if self.active_tab == key else "#EDE9FE",
                            WHITE if self.active_tab == key else PURPLE, 40)
            b.bind(on_release=lambda _, k=key: self.set_tab(k))  # type: ignore
            tabs.add_widget(b)
        root.add_widget(tabs)

        # Contenido con scroll según pestaña
        scroll, content = self.scroll()
        root.add_widget(scroll)
        if self.active_tab == "home":
            self.home(content)
        elif self.active_tab == "tasks":
            self.tasks_view(content)
        elif self.active_tab == "chat":
            self.chat_view(content)
        elif self.active_tab == "tracking":
            self.tracking(content)
        else:
            self.notifications(content)

    def set_tab(self, key):
        """Cambia la pestaña activa y vuelve a dibujar."""
        self.active_tab = key
        self.render()

    # --- Pestaña: Inicio --------------------------------------------
    def home(self, c):
        add_title(c, "Hola, apoderado 👋",
                "Resumen del aprendizaje de Sofía Morales • 7° Básico B")

        # Banner destacado con resumen del día
        banner = Card(bg="#F5F3FF", border="#DDD6FE", size_hint_y=None,
                    height=dp(100), orientation="vertical")
        banner.add_widget(lbl("Resumen de hoy", 17, PURPLE, True))
        banner.add_widget(lbl(
            "Sofía mantiene un promedio general de 6.2 y 96% de asistencia.",
            14, "#4C1D95"
        ))
        c.add_widget(banner)

        # Cuadrícula de indicadores clave
        grid = GridLayout(cols=2, spacing=dp(12), size_hint_y=None, height=dp(150))
        for title, value, sub in [
            ("Promedio general", "6.2", "Escala 1.0–7.0"),
            ("Asistencia", "96%", "Este semestre"),
            ("Estudio semanal", "14 h", "Últimos 7 días"),
            ("Tareas pendientes", "2", "Requieren revisión"),
        ]:
            card = Card(size_hint_y=None, height=dp(145), orientation="vertical")
            card.add_widget(lbl(title, 13, MUTED))
            card.add_widget(lbl(value, 28, TEXT, True))
            card.add_widget(lbl(sub, 12, MUTED))
            grid.add_widget(card)
        c.add_widget(grid)

        # Tarjeta con barras de progreso por asignatura
        card = Card(size_hint_y=None, height=dp(315), orientation="vertical",
                    spacing=dp(7))
        card.add_widget(lbl("Rendimiento por asignatura", 18, TEXT, True,
                            size_hint_y=None, height=dp(30)))
        for name, avg, prog in [
            ("🔢 Matemáticas", "6.5", 85), ("📚 Lenguaje", "5.8", 78),
            ("🔬 Ciencias", "5.3", 65), ("🗺️ Historia", "6.8", 91),
            ("🌍 Inglés", "5.5", 72)
        ]:
            row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
            row.add_widget(lbl(name, 13, TEXT, True, size_hint_x=.38))
            bar = ProgressBar(max=100, value=prog, size_hint_x=.42)
            row.add_widget(bar)
            row.add_widget(lbl(avg, 14, TEXT, True, size_hint_x=.15, halign="right"))
            card.add_widget(row)
        c.add_widget(card)

        # Tarjeta con la próxima tarea a revisar
        task = Card(bg="#EFF6FF", border="#BFDBFE", size_hint_y=None, height=dp(160),
                    orientation="vertical", spacing=dp(5))
        task.add_widget(lbl("📋 Próxima tarea", 17, BLUE, True))
        task.add_widget(lbl("Ejercicios de Fracciones", 15, TEXT, True))
        task.add_widget(lbl("Matemáticas • OA7 • 45 min • Dificultad media",
                            13, MUTED))
        view = make_button("Revisar tarea antes de asignar", BLUE, WHITE, 42)
        view.bind(on_release=lambda *_: self.task_detail())  # type: ignore
        task.add_widget(view)
        c.add_widget(task)

    # --- Popup: detalle de tarea ------------------------------------
    def task_detail(self):
        """Muestra un popup con el detalle de la tarea y acciones posibles."""
        box = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))
        box.add_widget(lbl("Ejercicios de Fracciones", 21, TEXT, True))
        box.add_widget(lbl(
            "Objetivo: resolver operaciones con fracciones mixtas (OA7)\n"
            "Tiempo estimado: 45 min\n"
            "Dificultad: Medio\n"
            "Fecha límite: Viernes 12 julio",
            14, MUTED
        ))
        box.add_widget(lbl(
            "El apoderado puede revisar la actividad antes de asignarla al estudiante.",
            13, "#4C1D95"
        ))
        actions = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        p = make_button("Posponer", "#F1F5F9", TEXT, 44)
        a = make_button("✅ Aprobar y asignar", PURPLE, WHITE, 44)
        actions.add_widget(p)
        actions.add_widget(a)
        box.add_widget(actions)
        pop = Popup(title="Revisar tarea", content=box,
                    size_hint=(.88, None), height=dp(360))
        a.bind(on_release=lambda *_: pop.dismiss())  # type: ignore
        p.bind(on_release=lambda *_: pop.dismiss())  # type: ignore
        pop.open()

    # --- Pestaña: Tareas --------------------------------------------
    def tasks_view(self, c):
        add_title(c, "Tareas",
                "Revisa cada actividad antes de que llegue al estudiante.")
        tasks = [
            ("🔢", "Ejercicios de Fracciones", "Matemáticas", "45 min", "Medio", "pending"),
            ("📚", "Lectura: El Principito cap. 5–8", "Lenguaje", "30 min", "Fácil", "approved"),
            ("🔬", "Mapa conceptual: Ecosistemas", "Ciencias", "60 min", "Difícil", "pending"),
            ("🗺️", "Línea de tiempo: República de Chile", "Historia", "40 min", "Medio", "done"),
        ]
        for emoji, name, subject, time, diff, status in tasks:
            card = Card(size_hint_y=None, height=dp(145), orientation="vertical",
                        spacing=dp(5))
            card.add_widget(lbl(f"{emoji}  {name}", 16, TEXT, True))
            card.add_widget(lbl(f"{subject} • {time} • {diff}", 13, MUTED))
            status_text = {
                "pending": "Pendiente de aprobación",
                "approved": "Asignada al estudiante",
                "done": "Completada fuera de la plataforma"
            }[status]
            card.add_widget(lbl(status_text, 13,
                                PURPLE if status == "pending" else GREEN))
            if status == "pending":
                b = make_button("Ver y aprobar", PURPLE, WHITE, 40)
                b.bind(on_release=lambda *_: self.task_detail())  # type: ignore
                card.add_widget(b)
            c.add_widget(card)

    # --- Pestaña: Chat IA -------------------------------------------
    def chat_view(self, c):
        add_title(c, "Asistente IA",
                    "Modo apoderado: entiende qué está aprendiendo tu hijo/a y cómo apoyarlo.")
        card = Card(size_hint_y=None, height=dp(260), orientation="vertical",
                    spacing=dp(10))
        card.add_widget(lbl("🤖 Asistente Educativo", 17, PURPLE, True))
        card.add_widget(lbl(
            "Hola, soy el Asistente Educativo de Tutor Educa. "
            "Puedo explicarte contenidos, recomendar estrategias y señalar "
            "áreas de refuerzo.",
            14, TEXT
        ))
        # Preguntas sugeridas
        for q in ["¿Cómo ayudar con fracciones?",
                    "¿Qué debería reforzar esta semana?",
                    "¿Qué significa este objetivo?"]:
            b = make_button(q, "#F3E8FF", PURPLE, 40)
            b.bind(on_release=lambda _, query=q: self.ai_answer(query))  # type: ignore
            card.add_widget(b)
        c.add_widget(card)

    def ai_answer(self, query):
        """Muestra la respuesta de la IA en un popup."""
        Popup(title="Asistente IA", content=lbl(
            f"Consulta: {query}\n\n"
            "Para apoyar a Sofía, puedes practicar el contenido con situaciones "
            "cotidianas y dedicar 15–20 minutos diarios. Tutor Educa puede adaptar "
            "la explicación al nivel del estudiante.",
            14, TEXT), size_hint=(.88, None), height=dp(280)).open()

    # --- Pestaña: Seguimiento ---------------------------------------
    def tracking(self, c):
        add_title(c, "Seguimiento del aprendizaje",
                  "Una visión simple del progreso para acompañar desde casa.")
        for title, value, detail in [
            ("Horas de estudio", "14 h", "Esta semana"),
            ("Actividades completadas", "18", "De 22 asignadas"),
            ("Áreas de refuerzo", "Ciencias", "Promedio actual 5.3"),
            ("Racha de estudio", "7 días", "Actividad constante"),
        ]:
            card = Card(size_hint_y=None, height=dp(95), orientation="vertical")
            card.add_widget(lbl(title, 13, MUTED))
            card.add_widget(lbl(value, 23, TEXT, True))
            card.add_widget(lbl(detail, 12, MUTED))
            c.add_widget(card)

    # --- Pestaña: Notificaciones ------------------------------------
    def notifications(self, c):
        add_title(c, "Notificaciones",
                  "Información relevante sobre el proceso de aprendizaje.")
        items = [
            ("ℹ", "Nueva tarea asignada: Ejercicios de Fracciones", BLUE),
            ("✅", "Sofía completó el objetivo semanal de Matemáticas", GREEN),
            ("⚠", "Bajo rendimiento detectado en Ciencias Naturales (5.3)", ORANGE),
            ("❗", "Evaluación de Matemáticas programada para el viernes", RED),
            ("✅", "Sofía completó la actividad de Historia", GREEN),
            ("ℹ", "El profesor recomienda reforzar Ciencias en casa", BLUE),
        ]
        for icon, text, color in items:
            card = Card(size_hint_y=None, height=dp(72),
                        orientation="horizontal", spacing=dp(10))
            card.add_widget(lbl(icon, 22, color, True, size_hint_x=None,
                                width=dp(35), halign="center"))
            card.add_widget(lbl(text, 13, TEXT))
            c.add_widget(card)


# ------------------------------------------------------------
# Student (estudiante)
# ------------------------------------------------------------

class StudentScreen(BaseScreen):
    """Vista principal del estudiante: asignaturas y accesos rápidos."""

    def on_pre_enter(self, *args):
        self.render()

    def render(self):
        self.clear_widgets()
        root = self.body()
        root.add_widget(Header(self.manager.app, "Tutor Matemático"))
        scroll, c = self.scroll()
        root.add_widget(scroll)

        add_title(c, "Aprende matemáticas a tu ritmo.",
                  "Contenido disponible incluso sin internet.")

        # Banner de estado de conexión
        online = Card(bg="#EFF6FF", border="#BFDBFE", size_hint_y=None,
                      height=dp(88), orientation="vertical")
        online.add_widget(lbl(
            ("🟢 Modo Online" if self.manager.app.is_online else "⚪ Modo Offline"),
            16, BLUE, True
        ))
        online.add_widget(lbl(
            "Las asignaturas visibles son administradas por tu profesor. " +
            ("" if self.manager.app.is_online else "Algunas funciones requieren conexión."),
            13, "#1E40AF"
        ))
        c.add_widget(online)

        # Cuadrícula con las asignaturas registradas por el profesor
        grid = GridLayout(cols=2, spacing=dp(12), size_hint_y=None)
        subjects = self.manager.app.subjects
        for s in subjects:
            h = dp(150)
            card = Card(size_hint_y=None, height=h, orientation="vertical",
                        spacing=dp(6))
            icon = lbl(s["emoji"], 30, TEXT, halign="center",
                       size_hint_y=None, height=dp(40))
            card.add_widget(icon)
            card.add_widget(lbl(s["name"], 15, TEXT, True, halign="center"))
            if s["active"]:
                b = make_button(
                    "Entrar" if s["id"] == "math" else "Contenido próximamente",
                    BLUE if s["id"] == "math" else "#E2E8F0",
                    WHITE if s["id"] == "math" else MUTED, 38
                )
                if s["id"] == "math":
                    b.bind(on_release=lambda *_: self.manager.app.go("topic"))  # type: ignore
                else:
                    b.disabled = True
            else:
                b = make_button("🔒 No disponible", "#E2E8F0", MUTED, 38)
                b.disabled = True
            card.add_widget(b)
            grid.add_widget(card)
        grid.bind(minimum_height=grid.setter("height"))  # type: ignore
        c.add_widget(grid)

        # Bloque de accesos rápidos a otras secciones
        quick = Card(size_hint_y=None, height=dp(185), orientation="vertical",
                     spacing=dp(7))
        quick.add_widget(lbl("Accesos rápidos", 18, TEXT, True))
        for text, screen in [("▶ Continuar: Ecuaciones lineales", "topic"),
                             ("📈 Practicar ejercicios", "topic"),
                             ("🧠 Preguntar a la IA", "ai")]:
            b = make_button(text, "#F8FAFC", TEXT, 40)
            b.bind(on_release=lambda _, s=screen: self.manager.app.go(s))  # type: ignore
            quick.add_widget(b)
        c.add_widget(quick)


# ------------------------------------------------------------
# Topic (contenido de una asignatura)
# ------------------------------------------------------------

class TopicScreen(BaseScreen):
    """Pantalla de contenido de Matemáticas: explicación, ejemplos y práctica."""

    section = StringProperty("explanation")

    def on_pre_enter(self, *args):
        self.render()

    def render(self):
        self.clear_widgets()
        root = self.body()
        root.add_widget(Header(self.manager.app, "Matemáticas"))

        # Pestañas internas de la asignatura
        tabs = BoxLayout(size_hint_y=None, height=dp(50),
                         padding=(dp(10), dp(5)), spacing=dp(6))
        for key, text in [("explanation", "Explicación"),
                          ("examples", "Ejemplos"),
                          ("exercises", "Ejercicios")]:
            b = make_button(text, BLUE if self.section == key else "#E2E8F0",
                            WHITE if self.section == key else TEXT, 40)
            b.bind(on_release=lambda _, k=key: self.change(k))  # type: ignore
            tabs.add_widget(b)
        root.add_widget(tabs)

        scroll, c = self.scroll()
        root.add_widget(scroll)
        if self.section == "explanation":
            self.explanation(c)
        elif self.section == "examples":
            self.examples(c)
        else:
            self.exercises(c)

    def change(self, k):
        self.section = k
        self.render()

    # --- Explicación -------------------------------------------------
    def explanation(self, c):
        add_title(c, "¿Qué es una ecuación lineal?")
        card = Card(size_hint_y=None, height=dp(150), orientation="vertical")
        card.add_widget(lbl(
            "Una ecuación lineal es una igualdad matemática donde existe una "
            "variable desconocida (generalmente x) que buscamos resolver. Se "
            "llama lineal porque su gráfica forma una línea recta.",
            15, TEXT
        ))
        c.add_widget(card)

        # Ejemplo paso a paso
        ex = Card(bg="#EFF6FF", border="#BFDBFE", size_hint_y=None,
                  height=dp(180), orientation="vertical", spacing=dp(6))
        ex.add_widget(lbl("Ejemplo básico", 18, TEXT, True))
        ex.add_widget(lbl(
            "Encuentra x:\n\n2x + 3 = 7\n// Restamos 3 de ambos lados\n"
            "2x = 4\n// Dividimos entre 2\nx = 2",
            15, TEXT
        ))
        c.add_widget(ex)

        # Regla mnemotécnica
        rule = Card(bg="#FFFBEB", border="#FDE68A", size_hint_y=None,
                    height=dp(105), orientation="vertical")
        rule.add_widget(lbl("💡 Regla de oro", 17, TEXT, True))
        rule.add_widget(lbl(
            "Lo que hagas en un lado de la ecuación, debes hacerlo en el otro "
            "lado para mantener el equilibrio.",
            14, TEXT
        ))
        c.add_widget(rule)

    # --- Ejemplos resueltos -----------------------------------------
    def examples(self, c):
        add_title(c, "Ejemplos resueltos")
        for title, eq in [
            ("Ejemplo 1", "x + 5 = 12\nx = 12 - 5\nx = 7"),
            ("Ejemplo 2", "3x = 15\nx = 15 ÷ 3\nx = 5"),
            ("Ejemplo 3", "4x - 8 = 16\n4x = 24\nx = 6")
        ]:
            card = Card(size_hint_y=None, height=dp(125), orientation="vertical")
            card.add_widget(lbl(title, 17, TEXT, True))
            card.add_widget(lbl(eq, 15, TEXT))  
            c.add_widget(card)

    # --- Ejercicios interactivos ------------------------------------
    def exercises(self, c):
        add_title(c, "Practica")
        card = Card(size_hint_y=None, height=dp(280), orientation="vertical",
                    spacing=dp(10))
        card.add_widget(lbl("Resuelve: 3x - 5 = 10", 24, TEXT, True, halign="center"))
        inp = TextInput(hint_text="Tu respuesta (valor de x)", multiline=False,
                        size_hint_y=None, height=dp(46))
        card.add_widget(inp)
        msg = lbl("", 14, TEXT, size_hint_y=None, height=dp(50))
        card.add_widget(msg)
        actions = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        verify = make_button("Verificar", BLUE, WHITE, 44)
        hint = make_button("Ver pista", PURPLE, WHITE, 44)
        actions.add_widget(verify)
        actions.add_widget(hint)
        card.add_widget(actions)
        # Validación simple de la respuesta del estudiante
        verify.bind(on_release=lambda *_: setattr(msg, "text",  # type: ignore
            "¡Correcto! Excelente trabajo." if inp.text.strip() == "5"
            else "Intenta de nuevo. Recuerda: primero suma 5 a ambos lados."))
        hint.bind(on_release=lambda *_: self.manager.app.go("ai"))  # type: ignore
        c.add_widget(card)


# ------------------------------------------------------------
# AI Chat (asistente con dos modos)
# ------------------------------------------------------------

class AIChatScreen(BaseScreen):
    """Chat de IA con modos Estudiante y Apoderado."""

    def on_pre_enter(self, *args):
        # Se inicializa el modo y el historial cada vez que se entra
        self.mode = "student"
        self.messages = []
        self.render()

    def render(self):
        self.clear_widgets()
        root = self.body()
        root.add_widget(Header(self.manager.app, "Asistente IA"))

        # Selector de modo (estudiante/apoderado)
        modes = BoxLayout(size_hint_y=None, height=dp(50),
                            padding=(dp(10), dp(5)), spacing=dp(6))
        for m, t in [("student", "🎓 Modo Estudiante"),
                    ("guardian", "👪 Modo Apoderado")]:
            b = make_button(t, BLUE if self.mode == m else "#E2E8F0",
                            WHITE if self.mode == m else TEXT, 40)
            b.bind(on_release=lambda _, x=m: self.set_mode(x))  # type: ignore
            modes.add_widget(b)
        root.add_widget(modes)

        scroll, c = self.scroll()
        root.add_widget(scroll)

        # Mensaje de bienvenida según el modo
        intro = ("¡Hola! Soy tu asistente de matemáticas. ¿En qué puedo ayudarte hoy?"
                if self.mode == "student" else
                "Hola, soy el Asistente Educativo de Tutor Educa. Puedo explicarte "
                "qué está aprendiendo tu hijo/a, entregar recomendaciones y "
                "sugerir estrategias de estudio.")
        intro_card = Card(bg=WHITE, border=BORDER, size_hint_y=None,
                        height=dp(100), orientation="vertical")
        intro_card.add_widget(lbl("🤖 " + intro, 14, TEXT))
        c.add_widget(intro_card)

        # Historial de mensajes (burbujas)
        for role, text in self.messages:
            bubble = Card(
                bg=BLUE if role == "user" else WHITE,
                border=None if role == "user" else BORDER,
                size_hint_y=None, height=dp(75), orientation="vertical",
            )
            bubble.add_widget(lbl(("Tú: " if role == "user" else "IA: ") + text,
                                    14, WHITE if role == "user" else TEXT))
            c.add_widget(bubble)

        # Preguntas sugeridas solo en modo apoderado
        if self.mode == "guardian":
            for q in ["¿Cómo ayudar con fracciones?",
                    "¿Qué reforzar esta semana?",
                    "¿Qué significa este objetivo?"]:
                b = make_button(q, "#F3E8FF", PURPLE, 38)
                b.bind(on_release=lambda _, x=q: self.send_message(x))  # type: ignore
                c.add_widget(b)

        root.add_widget(self.input_bar())

    def input_bar(self):
        """Barra inferior con campo de texto y botón enviar."""
        box = BoxLayout(size_hint_y=None, height=dp(62),
                        padding=dp(8), spacing=dp(8))
        inp = TextInput(
            hint_text="Escribe tu duda..." if self.manager.app.is_online
            else "Sin conexión a internet",
            multiline=False
        )
        send = make_button("Enviar", BLUE, WHITE, 44,
                        size_hint_x=None, width=dp(90))

        def go(_):
            # Solo envía si hay texto y hay conexión
            if inp.text.strip() and self.manager.app.is_online:
                self.send_message(inp.text.strip())

        send.bind(on_release=go)  # type: ignore
        box.add_widget(inp)
        box.add_widget(send)
        return box

    def set_mode(self, m):
        """Cambia entre modo estudiante y apoderado, reiniciando el chat."""
        self.mode = m
        self.messages = []
        self.render()

    def send_message(self, text):
        """Agrega el mensaje del usuario y simula una respuesta de la IA."""
        if not self.manager.app.is_online:
            return
        self.messages.append(("user", text))
        reply = ("Excelente pregunta. Déjame explicártelo paso a paso con un "
                "ejemplo concreto..."
                if self.mode == "student" else
                "Para apoyar a tu hijo/a, puedes practicar con situaciones "
                "cotidianas y dedicar 15–20 minutos diarios. También puedo "
                "ayudarte a interpretar su progreso.")
        self.messages.append(("ai", reply))
        self.render()


# ------------------------------------------------------------
# Progress (progreso del estudiante)
# ------------------------------------------------------------

class ProgressScreen(BaseScreen):
    """Pantalla de progreso personal del estudiante."""

    def on_pre_enter(self, *args):
        self.render()

    def render(self):
        self.clear_widgets()
        root = self.body()
        root.add_widget(Header(self.manager.app, "Mi Progreso"))
        scroll, c = self.scroll()
        root.add_widget(scroll)

        # Cabecera destacada con mensaje motivacional
        hero = Card(bg=BLUE, size_hint_y=None, height=dp(125),
                    orientation="vertical")
        hero.add_widget(lbl("¡Buen trabajo! 🏆", 25, WHITE, True)) # type = ignore
        hero.add_widget(lbl("Ya dominaste ecuaciones básicas.", 15, "#DBEAFE"))
        c.add_widget(hero)

        # Barra de progreso general
        card = Card(size_hint_y=None, height=dp(110), orientation="vertical")
        card.add_widget(lbl("Progreso general • 68%", 18, TEXT, True))
        card.add_widget(ProgressBar(max=100, value=68,
                                    size_hint_y=None, height=dp(15)))
        c.add_widget(card)

        # Tres tarjetas con métricas rápidas
        grid = GridLayout(cols=3, size_hint_y=None, height=dp(145),
                            spacing=dp(10))
        for a, b, d in [("Temas completados", "12", "De 18"),
                        ("Promedio", "6.5", "Escala 1–7"),
                        ("Estudio", "8.5h", "Esta semana")]:
            x = Card(size_hint_y=None, height=dp(135), orientation="vertical")
            x.add_widget(lbl(b, 27, TEXT, True))
            x.add_widget(lbl(a, 13, TEXT, True))
            x.add_widget(lbl(d, 11, MUTED))
            grid.add_widget(x)
        c.add_widget(grid)

        # Listado de actividad reciente
        recent = Card(size_hint_y=None, height=dp(230),
                    orientation="vertical", spacing=dp(8))
        recent.add_widget(lbl("Actividad reciente", 18, TEXT, True))
        for x in ["✅ Ecuaciones lineales — completado",
                "↗ Operaciones básicas — 75% en progreso",
                "🏆 Logro: Estudiante dedicado"]:
            recent.add_widget(lbl(x, 14, TEXT, size_hint_y=None, height=dp(52)))
        c.add_widget(recent)


# ------------------------------------------------------------
# Teacher (panel del profesor)
# ------------------------------------------------------------

class TeacherScreen(BaseScreen):
    """Panel del profesor: materias, estudiantes, rendimiento y avisos."""

    tab = StringProperty("subjects")

    def on_pre_enter(self, *args):
        self.render()

    def render(self):
        self.clear_widgets()
        root = self.body()
        root.add_widget(Header(self.manager.app, "Panel Profesor"))

        # Pestañas del panel
        tabs = BoxLayout(size_hint_y=None, height=dp(50),
                            padding=(dp(10), dp(5)), spacing=dp(6))
        for k, t in [("subjects", "Materias"), ("students", "Estudiantes"),
                        ("performance", "Rendimiento"), ("notices", "Avisos")]:
            b = make_button(t, BLUE if self.tab == k else "#E2E8F0",
                            WHITE if self.tab == k else TEXT, 40)
            b.bind(on_release=lambda _, x=k: self.set_tab(x))  # type: ignore
            tabs.add_widget(b)
        root.add_widget(tabs)

        scroll, c = self.scroll()
        root.add_widget(scroll)
        if self.tab == "subjects":
            self.subjects_view(c)
        elif self.tab == "students":
            self.students_view(c)
        elif self.tab == "performance":
            self.performance(c)
        else:
            self.notices(c)

    def set_tab(self, k):
        self.tab = k
        self.render()

    # --- Materias ----------------------------------------------------
    def subjects_view(self, c):
        add_title(c, "Administración de Asignaturas",
                    "Los cambios se reflejan automáticamente para los estudiantes.")
        for s in self.manager.app.subjects:
            card = Card(size_hint_y=None, height=dp(100),
                        orientation="horizontal", spacing=dp(10))
            card.add_widget(lbl(s["emoji"], 24, TEXT, size_hint_x=None,
                                width=dp(40), halign="center"))
            info = BoxLayout(orientation="vertical")
            info.add_widget(lbl(s["name"], 15, TEXT, True))
            info.add_widget(lbl("✅ Activa" if s["active"] else "🔒 Desactivada",
                                12, GREEN if s["active"] else MUTED))
            card.add_widget(info)
            # Botón para activar/desactivar la asignatura
            toggle = make_button("ACTIVA" if s["active"] else "ACTIVAR",
                                GREEN if s["active"] else "#E2E8F0",
                                WHITE if s["active"] else TEXT,
                                40, size_hint_x=None, width=dp(95))
            toggle.bind(on_release=lambda _, sid=s["id"]: self.toggle_subject(sid))  # type: ignore
            card.add_widget(toggle)
            c.add_widget(card)
        c.add_widget(lbl(
            "💡 Al activar o desactivar una asignatura, la vista del estudiante "
            "se actualiza al volver a ella.",
            13, MUTED, size_hint_y=None, height=dp(55)
        ))

    def toggle_subject(self, sid):
        """Invierte el estado activo de una asignatura y refresca la vista."""
        for s in self.manager.app.subjects:
            if s["id"] == sid:
                s["active"] = not s["active"]
        self.render()

    # --- Estudiantes -------------------------------------------------
    def students_view(self, c):
        add_title(c, "Lista de Estudiantes", "Rendimiento general del curso.")
        rows = [
            ("Sofía Morales", "Matemáticas", "85%", "6.5"),
            ("Tomás Rojas", "Lenguaje", "78%", "5.8"),
            ("Camila Pérez", "Ciencias", "65%", "5.3"),
            ("Diego Soto", "Historia", "91%", "6.8")
        ]
        for name, sub, prog, avg in rows:
            card = Card(size_hint_y=None, height=dp(76),
                        orientation="horizontal", spacing=dp(8))
            card.add_widget(lbl(name, 14, TEXT, True, size_hint_x=.38))
            card.add_widget(lbl(sub, 13, MUTED, size_hint_x=.28))
            card.add_widget(lbl(prog, 13, BLUE, size_hint_x=.16))
            card.add_widget(lbl(avg, 14, TEXT, True, size_hint_x=.12))
            c.add_widget(card)

    # --- Rendimiento -------------------------------------------------
    def performance(self, c):
        add_title(c, "Rendimiento", "Indicadores generales del curso.")
        for name, val in [("Promedio del curso", "6.1"), ("Asistencia", "94%"),
                            ("Actividades completadas", "82%"),
                            ("Estudiantes que requieren refuerzo", "4")]:
            card = Card(size_hint_y=None, height=dp(82), orientation="vertical")
            card.add_widget(lbl(name, 13, MUTED))
            card.add_widget(lbl(val, 22, TEXT, True))
            c.add_widget(card)

    # --- Avisos ------------------------------------------------------
    def notices(self, c):
        add_title(c, "Avisos al Apoderado",
                    "Mensajes que pueden acompañar el proceso de aprendizaje.")
        inp = TextInput(hint_text="Escribe un aviso...", multiline=True,
                        size_hint_y=None, height=dp(110))
        c.add_widget(inp)
        b = make_button("Enviar aviso", BLUE, WHITE, 46)
        b.bind(on_release=lambda *_: self.notice_sent(inp))  # type: ignore
        c.add_widget(b)

    def notice_sent(self, inp):
        """Muestra confirmación y limpia el campo de texto."""
        Popup(title="Aviso enviado",
            content=lbl("El aviso fue registrado para los apoderados.", 14, TEXT),
            size_hint=(.8, None), height=dp(180)).open()
        inp.text = ""


# ------------------------------------------------------------
# App / routing
# ------------------------------------------------------------

class TutorEducaApp(App):
    """Aplicación principal: registra pantallas y gestiona la navegación."""

    # Estado simulado de conexión (afecta a varias vistas)
    is_online = BooleanProperty(True)

    # Catálogo de asignaturas: el profesor puede activar/desactivar.
    # Los cambios se reflejan en la vista del estudiante.
    subjects = ListProperty([
        {"id": "math", "name": "Matemáticas", "emoji": "🔢", "active": True},
        {"id": "language", "name": "Lenguaje y Comunicación", "emoji": "📚", "active": True},
        {"id": "science", "name": "Ciencias Naturales", "emoji": "🔬", "active": True},
        {"id": "history", "name": "Historia, Geografía y CC.SS.", "emoji": "🗺️", "active": True},
        {"id": "english", "name": "Inglés", "emoji": "🌍", "active": True},
        {"id": "technology", "name": "Tecnología", "emoji": "💻", "active": False},
        {"id": "arts", "name": "Artes Visuales", "emoji": "🎨", "active": False},
        {"id": "music", "name": "Música", "emoji": "🎵", "active": False},
        {"id": "pe", "name": "Educación Física y Salud", "emoji": "⚽", "active": False},
    ])

    def build(self):
        """Registra todas las pantallas en el ScreenManager."""
        sm = ScreenManager()
        self.screens = {}
        for name, cls in [
            ("login", LoginScreen),
            ("guardian", GuardianScreen),
            ("student", StudentScreen),
            ("topic", TopicScreen),
            ("ai", AIChatScreen),
            ("progress", ProgressScreen),
            ("teacher", TeacherScreen),
        ]:
            s = cls(name=name)
            sm.add_widget(s)
            self.screens[name] = s
        sm.app = self  # type: ignore
        return sm

    def go(self, screen):
        """Navega a una pantalla y fuerza su renderizado previo."""
        self.root.current = screen  # type: ignore
        self.root.get_screen(screen).on_pre_enter()  # type: ignore

    def toggle_online(self):
        """Alterna entre modo online y offline y refresca la pantalla actual."""
        self.is_online = not self.is_online
        current = self.root.current  # type: ignore
        self.root.get_screen(current).on_pre_enter()  # type: ignore


if __name__ == "__main__":
    TutorEducaApp().run()