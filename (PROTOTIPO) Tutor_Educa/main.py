
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


# ------------------------------------------------------------
# Theme / helpers
# ------------------------------------------------------------

BG = "#F8FAFC"
WHITE = "#FFFFFF"
TEXT = "#0F172A"
MUTED = "#64748B"
BLUE = "#2563EB"
PURPLE = "#7C3AED"
GREEN = "#10B981"
ORANGE = "#F59E0B"
RED = "#EF4444"
BORDER = "#E2E8F0"


def rgba(hex_color, alpha=1):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16)/255 for i in (0, 2, 4)) + (alpha,)


class Card(BoxLayout):
    def __init__(self, bg=WHITE, radius=16, border=None, **kwargs):
        super().__init__(**kwargs)
        self.padding = dp(16)
        with self.canvas.before:
            Color(*rgba(bg))
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(radius)])
            if border:
                Color(*rgba(border))
                self.line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(radius)), width=1)
        self.bind(pos=self._update, size=self._update)

    def _update(self, *_):
        self.rect.pos = self.pos
        self.rect.size = self.size
        if hasattr(self, "line"):
            self.line.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(16))


def lbl(text="", size=16, color=TEXT, bold=False, **kwargs):
    # Valores por defecto que pueden ser sobrescritos por kwargs.
    kwargs.setdefault("halign", "left")
    kwargs.setdefault("valign", "middle")
    kwargs.setdefault("text_size", (None, None))
    return Label(
        text=text, font_size=dp(size), color=rgba(color),
        bold=bold, **kwargs
    )


def make_button(text, bg=BLUE, color=WHITE, height=46, **kwargs):
    b = Button(
        text=text, font_size=dp(14), bold=True,
        color=rgba(color), background_normal="", background_down="",
        background_color=rgba(bg), size_hint_y=None, height=dp(height),
        **kwargs
    )
    return b


def add_title(parent, title, subtitle=None):
    box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(82), spacing=dp(4))
    box.add_widget(lbl(title, 27, TEXT, True))
    if subtitle:
        box.add_widget(lbl(subtitle, 13, MUTED))
    parent.add_widget(box)


class Header(BoxLayout):
    def __init__(self, app, title, back=True, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(64),
                         padding=(dp(16), dp(10)), spacing=dp(12), **kwargs)
        if back:
            b = make_button("‹", "#E2E8F0", TEXT, 42, size_hint_x=None, width=dp(44))
            b.bind(on_release=lambda *_: app.go("login"))
            self.add_widget(b)
        else:
            self.add_widget(BoxLayout(size_hint_x=None, width=dp(44)))
        logo = Card(bg="#EFF6FF", radius=12, size_hint_x=None, width=dp(44), padding=0)
        logo.add_widget(lbl("📖", 23, BLUE, True, halign="center"))
        self.add_widget(logo)
        self.add_widget(lbl(title, 19, TEXT, True))
        online = make_button(
            "● Online" if app.is_online else "○ Offline",
            GREEN if app.is_online else "#CBD5E1",
            WHITE if app.is_online else "#475569",
            36, size_hint_x=None, width=dp(98)
        )
        online.bind(on_release=lambda *_: app.toggle_online())
        self.add_widget(online)


class BaseScreen(Screen):
    def body(self):
        # BoxLayout no tiene la propiedad background_color en Kivy.
        # Dibujamos el fondo mediante canvas para mantener el diseño.
        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            bg_color = Color(*rgba(BG))
            bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(
            pos=lambda instance, value: setattr(bg_rect, "pos", value),
            size=lambda instance, value: setattr(bg_rect, "size", value),
        )
        self.add_widget(root)
        return root

    def scroll(self):
        s = ScrollView()
        content = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(18),
                            size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        s.add_widget(content)
        return s, content


# ------------------------------------------------------------
# Login
# ------------------------------------------------------------

class LoginScreen(BaseScreen):
    def on_pre_enter(self, *args):
        self.clear_widgets()
        root = self.body()
        root.padding = dp(24)
        top = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(145),
                        spacing=dp(8))
        top.add_widget(lbl("Tutor Educa", 34, TEXT, True, halign="center"))
        top.add_widget(lbl("Aprendizaje conectado entre colegio, familia y estudiante", 15, MUTED, halign="center"))
        root.add_widget(top)

        card = Card(radius=24, padding=dp(28), orientation="vertical",
                    size_hint=(1, None), height=dp(360), spacing=dp(16))
        card.add_widget(lbl("¿Cómo quieres ingresar?", 22, TEXT, True, halign="center", size_hint_y=None, height=dp(45)))
        card.add_widget(lbl("Elige el perfil para explorar el prototipo.", 14, MUTED, halign="center", size_hint_y=None, height=dp(35)))

        g = make_button("👨‍👩‍👧  Ingresar como Apoderado", PURPLE, WHITE, 56)
        g.bind(on_release=lambda *_: self.manager.app.go("guardian"))
        card.add_widget(g)

        st = make_button("🎓  Ingresar como Estudiante", BLUE, WHITE, 56)
        st.bind(on_release=lambda *_: self.manager.app.go("student"))
        card.add_widget(st)

        te = make_button("👨‍🏫  Vista Profesor", "#0F172A", WHITE, 50)
        te.bind(on_release=lambda *_: self.manager.app.go("teacher"))
        card.add_widget(te)

        offline = make_button(
            "Cambiar estado: " + ("Online" if App.get_running_app().is_online else "Offline"),
            "#F1F5F9", TEXT, 44
        )
        offline.bind(on_release=lambda *_: self.manager.app.toggle_online())
        card.add_widget(offline)

        root.add_widget(card)
        root.add_widget(BoxLayout())
        root.add_widget(lbl("Prototipo educativo • 5° a 8° básico • Chile", 12, MUTED, halign="center", size_hint_y=None, height=dp(35)))


# ------------------------------------------------------------
# Guardian
# ------------------------------------------------------------

class GuardianScreen(BaseScreen):
    active_tab = StringProperty("home")

    def on_pre_enter(self, *args):
        self.render()

    def render(self):
        self.clear_widgets()
        root = self.body()
        root.add_widget(Header(self.manager.app, "Panel Apoderado", back=True))

        tabs = BoxLayout(size_hint_y=None, height=dp(50), padding=(dp(12), dp(6)), spacing=dp(6))
        for key, text in [("home","Inicio"),("tasks","Tareas"),("chat","IA"),("tracking","Seguimiento"),("notifications","Avisos")]:
            b = make_button(text, PURPLE if self.active_tab == key else "#EDE9FE",
                            WHITE if self.active_tab == key else PURPLE, 40)
            b.bind(on_release=lambda _, k=key: self.set_tab(k))
            tabs.add_widget(b)
        root.add_widget(tabs)

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
        self.active_tab = key
        self.render()

    def home(self, c):
        add_title(c, "Hola, apoderado 👋", "Resumen del aprendizaje de Sofía Morales • 7° Básico B")
        banner = Card(bg="#F5F3FF", border="#DDD6FE", size_hint_y=None, height=dp(100), orientation="vertical")
        banner.add_widget(lbl("Resumen de hoy", 17, PURPLE, True))
        banner.add_widget(lbl("Sofía mantiene un promedio general de 6.2 y 96% de asistencia.", 14, "#4C1D95"))
        c.add_widget(banner)

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

        card = Card(size_hint_y=None, height=dp(315), orientation="vertical", spacing=dp(7))
        card.add_widget(lbl("Rendimiento por asignatura", 18, TEXT, True, size_hint_y=None, height=dp(30)))
        for name, avg, prog in [
            ("🔢 Matemáticas", "6.5", 85), ("📚 Lenguaje", "5.8", 78),
            ("🔬 Ciencias", "5.3", 65), ("🗺️ Historia", "6.8", 91), ("🌍 Inglés", "5.5", 72)
        ]:
            row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
            row.add_widget(lbl(name, 13, TEXT, True, size_hint_x=.38))
            bar = ProgressBar(max=100, value=prog, size_hint_x=.42)
            row.add_widget(bar)
            row.add_widget(lbl(avg, 14, TEXT, True, size_hint_x=.15, halign="right"))
            card.add_widget(row)
        c.add_widget(card)

        task = Card(bg="#EFF6FF", border="#BFDBFE", size_hint_y=None, height=dp(160), orientation="vertical", spacing=dp(5))
        task.add_widget(lbl("📋 Próxima tarea", 17, BLUE, True))
        task.add_widget(lbl("Ejercicios de Fracciones", 15, TEXT, True))
        task.add_widget(lbl("Matemáticas • OA7 • 45 min • Dificultad media", 13, MUTED))
        view = make_button("Revisar tarea antes de asignar", BLUE, WHITE, 42)
        view.bind(on_release=lambda *_: self.task_detail())
        task.add_widget(view)
        c.add_widget(task)

    def task_detail(self):
        box = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))
        box.add_widget(lbl("Ejercicios de Fracciones", 21, TEXT, True))
        box.add_widget(lbl("Objetivo: resolver operaciones con fracciones mixtas (OA7)\nTiempo estimado: 45 min\nDificultad: Medio\nFecha límite: Viernes 12 julio", 14, MUTED))
        box.add_widget(lbl("El apoderado puede revisar la actividad antes de asignarla al estudiante.", 13, "#4C1D95"))
        actions = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        p = make_button("Posponer", "#F1F5F9", TEXT, 44)
        a = make_button("✓ Aprobar y asignar", PURPLE, WHITE, 44)
        actions.add_widget(p); actions.add_widget(a)
        box.add_widget(actions)
        pop = Popup(title="Revisar tarea", content=box, size_hint=(.88, None), height=dp(360))
        a.bind(on_release=lambda *_: pop.dismiss())
        p.bind(on_release=lambda *_: pop.dismiss())
        pop.open()

    def tasks_view(self, c):
        add_title(c, "Tareas", "Revisa cada actividad antes de que llegue al estudiante.")
        tasks = [
            ("🔢", "Ejercicios de Fracciones", "Matemáticas", "45 min", "Medio", "pending"),
            ("📚", "Lectura: El Principito cap. 5–8", "Lenguaje", "30 min", "Fácil", "approved"),
            ("🔬", "Mapa conceptual: Ecosistemas", "Ciencias", "60 min", "Difícil", "pending"),
            ("🗺️", "Línea de tiempo: República de Chile", "Historia", "40 min", "Medio", "done"),
        ]
        for emoji, name, subject, time, diff, status in tasks:
            card = Card(size_hint_y=None, height=dp(145), orientation="vertical", spacing=dp(5))
            card.add_widget(lbl(f"{emoji}  {name}", 16, TEXT, True))
            card.add_widget(lbl(f"{subject} • {time} • {diff}", 13, MUTED))
            status_text = {"pending":"Pendiente de aprobación", "approved":"Asignada al estudiante", "done":"Completada fuera de la plataforma"}[status]
            card.add_widget(lbl(status_text, 13, PURPLE if status=="pending" else GREEN))
            if status == "pending":
                b = make_button("Ver y aprobar", PURPLE, WHITE, 40)
                b.bind(on_release=lambda *_: self.task_detail())
                card.add_widget(b)
            c.add_widget(card)

    def chat_view(self, c):
        add_title(c, "Asistente IA", "Modo apoderado: entiende qué está aprendiendo tu hijo/a y cómo apoyarlo.")
        card = Card(size_hint_y=None, height=dp(260), orientation="vertical", spacing=dp(10))
        card.add_widget(lbl("🤖 Asistente Educativo", 17, PURPLE, True))
        card.add_widget(lbl("Hola, soy el Asistente Educativo de Tutor Educa. Puedo explicarte contenidos, recomendar estrategias y señalar áreas de refuerzo.", 14, TEXT))
        for q in ["¿Cómo ayudar con fracciones?", "¿Qué debería reforzar esta semana?", "¿Qué significa este objetivo?"]:
            b = make_button(q, "#F3E8FF", PURPLE, 40)
            b.bind(on_release=lambda _, query=q: self.ai_answer(query))
            card.add_widget(b)
        c.add_widget(card)

    def ai_answer(self, query):
        Popup(title="Asistente IA", content=lbl(
            f"Consulta: {query}\n\nPara apoyar a Sofía, puedes practicar el contenido con situaciones cotidianas y dedicar 15–20 minutos diarios. Tutor Educa puede adaptar la explicación al nivel del estudiante.",
            14, TEXT), size_hint=(.88, None), height=dp(280)).open()

    def tracking(self, c):
        add_title(c, "Seguimiento del aprendizaje", "Una visión simple del progreso para acompañar desde casa.")
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

    def notifications(self, c):
        add_title(c, "Notificaciones", "Información relevante sobre el proceso de aprendizaje.")
        items = [
            ("ℹ", "Nueva tarea asignada: Ejercicios de Fracciones", BLUE),
            ("✓", "Sofía completó el objetivo semanal de Matemáticas", GREEN),
            ("⚠", "Bajo rendimiento detectado en Ciencias Naturales (5.3)", ORANGE),
            ("!", "Evaluación de Matemáticas programada para el viernes", RED),
            ("✓", "Sofía completó la actividad de Historia", GREEN),
            ("ℹ", "El profesor recomienda reforzar Ciencias en casa", BLUE),
        ]
        for icon, text, color in items:
            card = Card(size_hint_y=None, height=dp(72), orientation="horizontal", spacing=dp(10))
            card.add_widget(lbl(icon, 22, color, True, size_hint_x=None, width=dp(35), halign="center"))
            card.add_widget(lbl(text, 13, TEXT))
            c.add_widget(card)


# ------------------------------------------------------------
# Student
# ------------------------------------------------------------

class StudentScreen(BaseScreen):
    def on_pre_enter(self, *args):
        self.render()

    def render(self):
        self.clear_widgets()
        root = self.body()
        root.add_widget(Header(self.manager.app, "Tutor Matemático"))
        scroll, c = self.scroll()
        root.add_widget(scroll)
        add_title(c, "Aprende matemáticas a tu ritmo.", "Contenido disponible incluso sin internet.")
        online = Card(bg="#EFF6FF", border="#BFDBFE", size_hint_y=None, height=dp(88), orientation="vertical")
        online.add_widget(lbl(("🟢 Modo Online" if self.manager.app.is_online else "⚪ Modo Offline"), 16, BLUE, True))
        online.add_widget(lbl("Las asignaturas visibles son administradas por tu profesor. " +
                              ("" if self.manager.app.is_online else "Algunas funciones requieren conexión."), 13, "#1E40AF"))
        c.add_widget(online)

        grid = GridLayout(cols=2, spacing=dp(12), size_hint_y=None)
        subjects = self.manager.app.subjects
        for s in subjects:
            h = dp(150)
            card = Card(size_hint_y=None, height=h, orientation="vertical", spacing=dp(6))
            icon = lbl(s["emoji"], 30, TEXT, halign="center", size_hint_y=None, height=dp(40))
            card.add_widget(icon)
            card.add_widget(lbl(s["name"], 15, TEXT, True, halign="center"))
            if s["active"]:
                b = make_button("Entrar" if s["id"]=="math" else "Contenido próximamente", BLUE if s["id"]=="math" else "#E2E8F0",
                                WHITE if s["id"]=="math" else MUTED, 38)
                if s["id"] == "math":
                    b.bind(on_release=lambda *_: self.manager.app.go("topic"))
                else:
                    b.disabled = True
            else:
                b = make_button("🔒 No disponible", "#E2E8F0", MUTED, 38)
                b.disabled = True
            card.add_widget(b)
            grid.add_widget(card)
        grid.bind(minimum_height=grid.setter("height"))
        c.add_widget(grid)

        quick = Card(size_hint_y=None, height=dp(185), orientation="vertical", spacing=dp(7))
        quick.add_widget(lbl("Accesos rápidos", 18, TEXT, True))
        for text, screen in [("▶ Continuar: Ecuaciones lineales", "topic"),
                             ("📈 Practicar ejercicios", "topic"),
                             ("🧠 Preguntar a la IA", "ai")]:
            b = make_button(text, "#F8FAFC", TEXT, 40)
            b.bind(on_release=lambda _, s=screen: self.manager.app.go(s))
            quick.add_widget(b)
        c.add_widget(quick)


# ------------------------------------------------------------
# Topic
# ------------------------------------------------------------

class TopicScreen(BaseScreen):
    section = StringProperty("explanation")

    def on_pre_enter(self, *args):
        self.render()

    def render(self):
        self.clear_widgets()
        root = self.body()
        root.add_widget(Header(self.manager.app, "Matemáticas"))
        tabs = BoxLayout(size_hint_y=None, height=dp(50), padding=(dp(10), dp(5)), spacing=dp(6))
        for key, text in [("explanation","Explicación"),("examples","Ejemplos"),("exercises","Ejercicios")]:
            b = make_button(text, BLUE if self.section==key else "#E2E8F0", WHITE if self.section==key else TEXT, 40)
            b.bind(on_release=lambda _, k=key: self.change(k))
            tabs.add_widget(b)
        root.add_widget(tabs)
        scroll,c=self.scroll()
        root.add_widget(scroll)
        if self.section=="explanation":
            self.explanation(c)
        elif self.section=="examples":
            self.examples(c)
        else:
            self.exercises(c)

    def change(self, k):
        self.section=k
        self.render()

    def explanation(self,c):
        add_title(c,"¿Qué es una ecuación lineal?")
        card = Card(size_hint_y=None, height=dp(150), orientation="vertical")
        card.add_widget(lbl("Una ecuación lineal es una igualdad matemática donde existe una variable desconocida (generalmente x) que buscamos resolver. Se llama lineal porque su gráfica forma una línea recta.",15,TEXT))
        c.add_widget(card)
        ex=Card(bg="#EFF6FF",border="#BFDBFE",size_hint_y=None,height=dp(180),orientation="vertical",spacing=dp(6))
        ex.add_widget(lbl("Ejemplo básico",18,TEXT,True))
        ex.add_widget(lbl("Encuentra x:\n\n2x + 3 = 7\n// Restamos 3 de ambos lados\n2x = 4\n// Dividimos entre 2\nx = 2",15,TEXT))
        c.add_widget(ex)
        rule=Card(bg="#FFFBEB",border="#FDE68A",size_hint_y=None,height=dp(105),orientation="vertical")
        rule.add_widget(lbl("💡 Regla de oro",17,TEXT,True))
        rule.add_widget(lbl("Lo que hagas en un lado de la ecuación, debes hacerlo en el otro lado para mantener el equilibrio.",14,TEXT))
        c.add_widget(rule)

    def examples(self,c):
        add_title(c,"Ejemplos resueltos")
        for title, eq in [
            ("Ejemplo 1","x + 5 = 12\nx = 12 - 5\nx = 7"),
            ("Ejemplo 2","3x = 15\nx = 15 ÷ 3\nx = 5"),
            ("Ejemplo 3","4x - 8 = 16\n4x = 24\nx = 6")]:
            card=Card(size_hint_y=None,height=dp(125),orientation="vertical")
            card.add_widget(lbl(title,17,TEXT,True))
            card.add_widget(lbl(eq,15,TEXT))
            c.add_widget(card)

    def exercises(self,c):
        add_title(c,"Practica")
        card=Card(size_hint_y=None,height=dp(280),orientation="vertical",spacing=dp(10))
        card.add_widget(lbl("Resuelve: 3x - 5 = 10",24,TEXT,True,halign="center"))
        inp=TextInput(hint_text="Tu respuesta (valor de x)",multiline=False,size_hint_y=None,height=dp(46))
        card.add_widget(inp)
        msg=lbl("",14,TEXT,size_hint_y=None,height=dp(50))
        card.add_widget(msg)
        actions=BoxLayout(size_hint_y=None,height=dp(46),spacing=dp(8))
        verify=make_button("Verificar",BLUE,WHITE,44)
        hint=make_button("Ver pista",PURPLE,WHITE,44)
        actions.add_widget(verify); actions.add_widget(hint); card.add_widget(actions)
        verify.bind(on_release=lambda *_: setattr(msg,"text",
            "¡Correcto! Excelente trabajo." if inp.text.strip()=="5"
            else "Intenta de nuevo. Recuerda: primero suma 5 a ambos lados."))
        hint.bind(on_release=lambda *_: self.manager.app.go("ai"))
        c.add_widget(card)


# ------------------------------------------------------------
# AI Chat
# ------------------------------------------------------------

class AIChatScreen(BaseScreen):
    def on_pre_enter(self,*args):
        self.mode="student"
        self.messages=[]
        self.render()

    def render(self):
        self.clear_widgets()
        root=self.body()
        root.add_widget(Header(self.manager.app,"Asistente IA"))
        modes=BoxLayout(size_hint_y=None,height=dp(50),padding=(dp(10),dp(5)),spacing=dp(6))
        for m,t in [("student","🎓 Modo Estudiante"),("guardian","👨‍👩‍👧 Modo Apoderado")]:
            b=make_button(t, BLUE if self.mode==m else "#E2E8F0", WHITE if self.mode==m else TEXT,40)
            b.bind(on_release=lambda _,x=m:self.set_mode(x))
            modes.add_widget(b)
        root.add_widget(modes)

        scroll,c=self.scroll()
        root.add_widget(scroll)
        intro = ("¡Hola! Soy tu asistente de matemáticas. ¿En qué puedo ayudarte hoy?"
                 if self.mode=="student" else
                 "Hola, soy el Asistente Educativo de Tutor Educa. Puedo explicarte qué está aprendiendo tu hijo/a, entregar recomendaciones y sugerir estrategias de estudio.")
        c.add_widget(Card(size_hint_y=None,height=dp(100),orientation="vertical").__class__() if False else lbl("🤖 "+intro,14,TEXT,size_hint_y=None,height=dp(100)))
        for role,text in self.messages:
            color=BLUE if role=="user" else "#FFFFFF"
            c.add_widget(Card(bg=color,size_hint_y=None,height=dp(75),orientation="vertical").__class__() if False else
                          lbl(("Tú: " if role=="user" else "IA: ")+text,14,WHITE if role=="user" else TEXT,size_hint_y=None,height=dp(75)))
        if self.mode=="guardian":
            for q in ["¿Cómo ayudar con fracciones?","¿Qué reforzar esta semana?","¿Qué significa este objetivo?"]:
                b=make_button(q,"#F3E8FF",PURPLE,38)
                b.bind(on_release=lambda _,x=q:self.send_message(x))
                c.add_widget(b)
        root.add_widget(self.input_bar())

    def input_bar(self):
        box=BoxLayout(size_hint_y=None,height=dp(62),padding=dp(8),spacing=dp(8))
        inp=TextInput(hint_text="Escribe tu duda..." if self.manager.app.is_online else "Sin conexión a internet",
                      multiline=False)
        send=make_button("Enviar",BLUE,WHITE,44,size_hint_x=None,width=dp(90))
        def go(_):
            if inp.text.strip() and self.manager.app.is_online:
                self.send_message(inp.text.strip())
        send.bind(on_release=go)
        box.add_widget(inp); box.add_widget(send)
        return box

    def set_mode(self,m):
        self.mode=m
        self.messages=[]
        self.render()

    def send_message(self,text):
        if not self.manager.app.is_online:
            return
        self.messages.append(("user",text))
        reply=("Excelente pregunta. Déjame explicártelo paso a paso con un ejemplo concreto..."
               if self.mode=="student" else
               "Para apoyar a tu hijo/a, puedes practicar con situaciones cotidianas y dedicar 15–20 minutos diarios. También puedo ayudarte a interpretar su progreso.")
        self.messages.append(("ai",reply))
        self.render()


# ------------------------------------------------------------
# Progress
# ------------------------------------------------------------

class ProgressScreen(BaseScreen):
    def on_pre_enter(self,*args):
        self.render()

    def render(self):
        self.clear_widgets()
        root=self.body()
        root.add_widget(Header(self.manager.app,"Mi Progreso"))
        scroll,c=self.scroll(); root.add_widget(scroll)
        hero=Card(bg=BLUE,size_hint_y=None,height=dp(125),orientation="vertical")
        hero.add_widget(lbl("¡Buen trabajo! 🏆",25,WHITE,True))
        hero.add_widget(lbl("Ya dominaste ecuaciones básicas.",15,"#DBEAFE"))
        c.add_widget(hero)
        card=Card(size_hint_y=None,height=dp(110),orientation="vertical")
        card.add_widget(lbl("Progreso general • 68%",18,TEXT,True))
        card.add_widget(ProgressBar(max=100,value=68,size_hint_y=None,height=dp(15)))
        c.add_widget(card)
        grid=GridLayout(cols=3,size_hint_y=None,height=dp(145),spacing=dp(10))
        for a,b,d in [("Temas completados","12","De 18"),("Promedio","6.5","Escala 1–7"),("Estudio","8.5h","Esta semana")]:
            x=Card(size_hint_y=None,height=dp(135),orientation="vertical")
            x.add_widget(lbl(b,27,TEXT,True));x.add_widget(lbl(a,13,TEXT,True));x.add_widget(lbl(d,11,MUTED));grid.add_widget(x)
        c.add_widget(grid)
        recent=Card(size_hint_y=None,height=dp(230),orientation="vertical",spacing=dp(8))
        recent.add_widget(lbl("Actividad reciente",18,TEXT,True))
        for x in ["✓ Ecuaciones lineales — completado", "↗ Operaciones básicas — 75% en progreso", "🏆 Logro: Estudiante dedicado"]:
            recent.add_widget(lbl(x,14,TEXT,size_hint_y=None,height=dp(52)))
        c.add_widget(recent)


# ------------------------------------------------------------
# Teacher
# ------------------------------------------------------------

class TeacherScreen(BaseScreen):
    tab=StringProperty("subjects")
    def on_pre_enter(self,*args):
        self.render()

    def render(self):
        self.clear_widgets()
        root=self.body(); root.add_widget(Header(self.manager.app,"Panel Profesor"))
        tabs=BoxLayout(size_hint_y=None,height=dp(50),padding=(dp(10),dp(5)),spacing=dp(6))
        for k,t in [("subjects","Materias"),("students","Estudiantes"),("performance","Rendimiento"),("notices","Avisos")]:
            b=make_button(t,BLUE if self.tab==k else "#E2E8F0",WHITE if self.tab==k else TEXT,40)
            b.bind(on_release=lambda _,x=k:self.set_tab(x)); tabs.add_widget(b)
        root.add_widget(tabs)
        scroll,c=self.scroll(); root.add_widget(scroll)
        if self.tab=="subjects": self.subjects_view(c)
        elif self.tab=="students": self.students_view(c)
        elif self.tab=="performance": self.performance(c)
        else: self.notices(c)

    def set_tab(self,k): self.tab=k; self.render()

    def subjects_view(self,c):
        add_title(c,"Administración de Asignaturas","Los cambios se reflejan automáticamente para los estudiantes.")
        for s in self.manager.app.subjects:
            card=Card(size_hint_y=None,height=dp(100),orientation="horizontal",spacing=dp(10))
            card.add_widget(lbl(s["emoji"],24,TEXT,size_hint_x=None,width=dp(40),halign="center"))
            info=BoxLayout(orientation="vertical")
            info.add_widget(lbl(s["name"],15,TEXT,True))
            info.add_widget(lbl("✓ Activa" if s["active"] else "🔒 Desactivada",12,GREEN if s["active"] else MUTED))
            card.add_widget(info)
            toggle=make_button("ACTIVA" if s["active"] else "ACTIVAR",
                               GREEN if s["active"] else "#E2E8F0",
                               WHITE if s["active"] else TEXT,40,size_hint_x=None,width=dp(95))
            toggle.bind(on_release=lambda _,sid=s["id"]: self.toggle_subject(sid))
            card.add_widget(toggle)
            c.add_widget(card)
        c.add_widget(lbl("💡 Al activar o desactivar una asignatura, la vista del estudiante se actualiza al volver a ella.",13,MUTED,size_hint_y=None,height=dp(55)))

    def toggle_subject(self,sid):
        for s in self.manager.app.subjects:
            if s["id"]==sid: s["active"]=not s["active"]
        self.render()

    def students_view(self,c):
        add_title(c,"Lista de Estudiantes","Rendimiento general del curso.")
        rows=[("Sofía Morales","Matemáticas","85%","6.5"),("Tomás Rojas","Lenguaje","78%","5.8"),
              ("Camila Pérez","Ciencias","65%","5.3"),("Diego Soto","Historia","91%","6.8")]
        for name,sub,prog,avg in rows:
            card=Card(size_hint_y=None,height=dp(76),orientation="horizontal",spacing=dp(8))
            card.add_widget(lbl(name,14,TEXT,True,size_hint_x=.38))
            card.add_widget(lbl(sub,13,MUTED,size_hint_x=.28))
            card.add_widget(lbl(prog,13,BLUE,size_hint_x=.16))
            card.add_widget(lbl(avg,14,TEXT,True,size_hint_x=.12))
            c.add_widget(card)

    def performance(self,c):
        add_title(c,"Rendimiento","Indicadores generales del curso.")
        for name,val in [("Promedio del curso","6.1"),("Asistencia","94%"),("Actividades completadas","82%"),("Estudiantes que requieren refuerzo","4")]:
            card=Card(size_hint_y=None,height=dp(82),orientation="vertical")
            card.add_widget(lbl(name,13,MUTED));card.add_widget(lbl(val,22,TEXT,True));c.add_widget(card)

    def notices(self,c):
        add_title(c,"Avisos al Apoderado","Mensajes que pueden acompañar el proceso de aprendizaje.")
        inp=TextInput(hint_text="Escribe un aviso...",multiline=True,size_hint_y=None,height=dp(110))
        c.add_widget(inp)
        b=make_button("Enviar aviso",BLUE,WHITE,46)
        b.bind(on_release=lambda *_: self.notice_sent(inp))
        c.add_widget(b)

    def notice_sent(self,inp):
        Popup(title="Aviso enviado",content=lbl("El aviso fue registrado para los apoderados.",14,TEXT),
              size_hint=(.8,None),height=dp(180)).open()
        inp.text=""


# ------------------------------------------------------------
# App / routing
# ------------------------------------------------------------

class TutorEducaApp(App):
    is_online = BooleanProperty(True)
    subjects = ListProperty([
        {"id":"math","name":"Matemáticas","emoji":"🔢","active":True},
        {"id":"language","name":"Lenguaje y Comunicación","emoji":"📚","active":True},
        {"id":"science","name":"Ciencias Naturales","emoji":"🔬","active":True},
        {"id":"history","name":"Historia, Geografía y CC.SS.","emoji":"🗺️","active":True},
        {"id":"english","name":"Inglés","emoji":"🌍","active":True},
        {"id":"technology","name":"Tecnología","emoji":"💻","active":False},
        {"id":"arts","name":"Artes Visuales","emoji":"🎨","active":False},
        {"id":"music","name":"Música","emoji":"🎵","active":False},
        {"id":"pe","name":"Educación Física y Salud","emoji":"⚽","active":False},
    ])

    def build(self):
        sm=ScreenManager()
        self.screens={}
        for name, cls in [("login",LoginScreen),("guardian",GuardianScreen),("student",StudentScreen),
                          ("topic",TopicScreen),("ai",AIChatScreen),("progress",ProgressScreen),("teacher",TeacherScreen)]:
            s=cls(name=name); sm.add_widget(s); self.screens[name]=s
        sm.app=self
        return sm

    def go(self, screen):
        self.root.current=screen
        self.root.get_screen(screen).on_pre_enter()

    def toggle_online(self):
        self.is_online=not self.is_online
        current=self.root.current
        self.root.get_screen(current).on_pre_enter()


if __name__ == "__main__":
    TutorEducaApp().run()
