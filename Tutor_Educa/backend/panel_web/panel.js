/*
 * Panel web de Tutor Educa para administradores (superadmin y admin de colegio).
 *
 * Reglas de este archivo:
 *  - Todo texto que viene del servidor entra a la página como TEXTO (textContent), nunca como HTML.
 *  - La contraseña nunca se guarda; el token de acceso vive solo en memoria y el de renovación en sessionStorage
 *    (se borra al cerrar la pestaña). Tras 20 minutos sin actividad la sesión se cierra.
 *  - Las reglas de quién puede qué las hace cumplir el SERVIDOR; aquí solo se ocultan botones que no corresponden.
 */
"use strict";
(function () {
  const RAIZ = document.getElementById("app");
  const AVISOS = document.getElementById("aviso");
  const MODALES = document.getElementById("modales");
  const MINUTOS_INACTIVIDAD = 20;
  const LIMITE_PERSONAS = 1000;
  const CLAVE_SESION = "tutor_panel";
  const PERFILES = { estudiante: "Estudiante", docente: "Docente", apoderado: "Apoderado/a",
                     admin: "Administrador/a", superadmin: "Superadministrador/a" };

  const estado = { sesion: null, pagina: "personas", colegios: [], colegioId: null, cursos: [], personas: [],
                   docentes: [], filtros: { rol: "", buscar: "", curso: "" }, cargando: false, error: "",
                   errores: null, erroresDias: 30, erroresColegio: "" };

  // ======================================================================================================
  // Utilidades
  // ======================================================================================================
  function h(etiqueta, atributos, ...hijos) {
    const nodo = document.createElement(etiqueta);
    for (const [clave, valor] of Object.entries(atributos || {})) {
      if (valor === null || valor === undefined || valor === false) continue;
      if (clave === "clase") nodo.className = valor;
      else if (clave.startsWith("al")) nodo.addEventListener(clave.slice(2).toLowerCase(), valor);
      else if (valor === true) nodo.setAttribute(clave, "");
      else nodo.setAttribute(clave, String(valor));
    }
    for (const hijo of hijos.flat(Infinity)) {
      if (hijo === null || hijo === undefined || hijo === false) continue;
      nodo.append(hijo instanceof Node ? hijo : document.createTextNode(String(hijo)));
    }
    return nodo;
  }

  const normalizar = (texto) => String(texto || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

  function fechaCorta(texto) {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(texto || "");
    return m ? `${m[3]}-${m[2]}-${m[1]}` : (texto || "");
  }

  function avisar(texto, tipo) {
    const caja = h("div", { clase: tipo || "" }, texto);
    AVISOS.append(caja);
    setTimeout(() => caja.remove(), tipo === "error" ? 9000 : 5000);
  }

  class ErrorPanel extends Error {
    constructor(mensaje, codigo) { super(mensaje); this.codigo = codigo || 0; }
  }

  function mensajeDeError(datos, codigo) {
    const detalle = datos && datos.detail;
    if (typeof detalle === "string") return detalle;
    if (Array.isArray(detalle) && detalle.length) {
      const campo = (detalle[0].loc || []).slice(-1)[0];
      return `Revisa los datos${campo ? ` (campo «${campo}»)` : ""}: ${detalle[0].msg || "no son válidos"}.`;
    }
    if (codigo >= 500) return "El servidor tuvo un problema. Inténtalo de nuevo en un momento.";
    return "No se pudo completar la acción.";
  }

  // ======================================================================================================
  // Conexión con la API y sesión
  // ======================================================================================================
  async function pedir(metodo, ruta, cuerpo, opciones) {
    const { sinSesion = false, reintentar = true } = opciones || {};
    const cabeceras = { "Content-Type": "application/json" };
    if (!sinSesion && estado.sesion && estado.sesion.acceso) cabeceras.Authorization = `Bearer ${estado.sesion.acceso}`;
    let respuesta;
    try {
      respuesta = await fetch(ruta, { method: metodo, headers: cabeceras, cache: "no-store",
                                      body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo) });
    } catch (e) {
      throw new ErrorPanel("No hay conexión con el servidor. Revisa tu internet e inténtalo de nuevo.", 0);
    }
    if (respuesta.status === 401 && !sinSesion && reintentar && estado.sesion && estado.sesion.renovacion) {
      if (await renovar()) return pedir(metodo, ruta, cuerpo, { sinSesion, reintentar: false });
      cerrarSesion("Tu sesión venció. Ingresa de nuevo.");
      throw new ErrorPanel("Tu sesión venció. Ingresa de nuevo.", 401);
    }
    let datos = null;
    try { datos = await respuesta.json(); } catch (e) { datos = null; }
    if (!respuesta.ok) throw new ErrorPanel(mensajeDeError(datos, respuesta.status), respuesta.status);
    return datos;
  }

  async function renovar() {
    try {
      const datos = await pedir("POST", "/renovar", { token_renovacion: estado.sesion.renovacion },
                                { sinSesion: true });
      estado.sesion.acceso = datos.token_acceso;
      return true;
    } catch (e) { return false; }
  }

  function guardarSesion() {
    try {
      sessionStorage.setItem(CLAVE_SESION, JSON.stringify({ renovacion: estado.sesion.renovacion,
                                                            usuario: estado.sesion.usuario }));
    } catch (e) { /* sin almacenamiento: la sesión dura hasta recargar */ }
  }

  function aceptarSesion(datos, activando) {
    const rol = datos.usuario.rol;
    if (rol !== "admin" && rol !== "superadmin") {
      throw new ErrorPanel((activando ? "Tu cuenta quedó activada. " : "")
                           + "Este panel es solo para administradores: ingresa desde la app Tutor Educa.", 403);
    }
    estado.sesion = { acceso: datos.token_acceso, renovacion: datos.token_renovacion, usuario: datos.usuario };
    guardarSesion();
    reiniciarInactividad();
  }

  let temporizador = null;
  function reiniciarInactividad() {
    clearTimeout(temporizador);
    if (!estado.sesion) return;
    temporizador = setTimeout(() => cerrarSesion("Cerramos tu sesión por inactividad."),
                              MINUTOS_INACTIVIDAD * 60 * 1000);
  }

  function cerrarSesion(mensaje) {
    clearTimeout(temporizador);
    estado.sesion = null;
    estado.personas = []; estado.cursos = []; estado.docentes = []; estado.colegios = []; estado.colegioId = null;
    estado.errores = null; estado.erroresColegio = "";
    estado.filtros = { rol: "", buscar: "", curso: "" };
    try { sessionStorage.removeItem(CLAVE_SESION); } catch (e) { /* nada que borrar */ }
    MODALES.replaceChildren();
    vistaIngreso();
    if (mensaje) avisar(mensaje);
  }

  // ======================================================================================================
  // Ventanas (modales)
  // ======================================================================================================
  function modal(titulo, cuerpo, botones) {
    const anterior = document.activeElement;
    const id = `modal-${Math.random().toString(36).slice(2, 8)}`;
    const caja = h("div", { clase: "modal", role: "dialog", "aria-modal": "true", "aria-labelledby": id },
                   h("h2", { id }, titulo), cuerpo,
                   botones && botones.length ? h("div", { clase: "modal-botones" }, botones) : null);
    const fondo = h("div", { clase: "fondo-modal" }, caja);
    const cerrar = () => {
      document.removeEventListener("keydown", alTeclear);
      fondo.remove();
      if (anterior && anterior.focus) anterior.focus();
    };
    const alTeclear = (e) => { if (e.key === "Escape") cerrar(); };
    document.addEventListener("keydown", alTeclear);
    MODALES.append(fondo);
    const primero = caja.querySelector("input, select, textarea") || caja.querySelector("button");
    if (primero) primero.focus();
    return { cerrar, caja };
  }

  function botonCerrar(ventana, texto) {
    return h("button", { clase: "boton contorno", type: "button", alClick: () => ventana.cerrar() }, texto || "Cerrar");
  }

  /** Ventana con un formulario. ``alEnviar`` recibe (cerrar) y puede lanzar ErrorPanel para mostrar el motivo. */
  function ventanaFormulario(titulo, campos, textoEnviar, alEnviar) {
    const error = h("div", { clase: "error-formulario", role: "alert", hidden: true });
    const enviar = h("button", { clase: "boton", type: "submit" }, textoEnviar);
    const formulario = h("form", { clase: "formulario", novalidate: true }, campos, error, h("div", { clase: "modal-botones" }));
    const ventana = modal(titulo, formulario, []);
    const botones = formulario.querySelector(".modal-botones");
    botones.append(botonCerrar(ventana, "Cancelar"), enviar);
    formulario.addEventListener("submit", async (e) => {
      e.preventDefault();
      error.hidden = true;
      enviar.disabled = true;
      try {
        await alEnviar(ventana.cerrar);
      } catch (fallo) {
        error.textContent = fallo.message || "No se pudo completar la acción.";
        error.hidden = false;
      } finally {
        enviar.disabled = false;
      }
    });
    return ventana;
  }

  function confirmar(titulo, texto, textoBoton, alConfirmar, peligro) {
    const error = h("div", { clase: "error-formulario", role: "alert", hidden: true });
    const aceptar = h("button", { clase: peligro ? "boton peligro" : "boton", type: "button" }, textoBoton);
    const ventana = modal(titulo, h("div", { clase: "formulario" }, h("p", {}, texto), error), []);
    ventana.caja.querySelector(".formulario").append(h("div", { clase: "modal-botones" },
                                                       botonCerrar(ventana, "Cancelar"), aceptar));
    aceptar.addEventListener("click", async () => {
      aceptar.disabled = true; error.hidden = true;
      try { await alConfirmar(ventana.cerrar); }
      catch (fallo) { error.textContent = fallo.message; error.hidden = false; }
      finally { aceptar.disabled = false; }
    });
    return ventana;
  }

  // ======================================================================================================
  // Códigos de invitación
  // ======================================================================================================
  function nombreColegioActual() {
    const u = estado.sesion.usuario;
    if (u.rol === "admin") return u.colegio || "";
    const c = estado.colegios.find((x) => x.id === estado.colegioId);
    return c ? c.nombre : "";
  }

  function mensajeInvitacion(persona, codigo, vence, colegio) {
    const primero = String(persona.nombre || "").split(/\s+/)[0];
    const donde = persona.rol === "admin"
      ? `Entra a ${location.origin}/panel y toca «Tengo un código».`
      : "Abre la app y toca «Tengo un código».";
    return [`Hola ${primero}, te invitan a Tutor Educa${colegio ? ` (${colegio})` : ""}.`,
            `1) ${donde}`,
            `2) Escribe tu correo: ${persona.correo}`,
            `3) Escribe este código: ${codigo} (sirve una sola vez y vence el ${fechaCorta(vence)}).`,
            "4) Elige tu propia contraseña. Nadie más la conoce."].join("\n");
  }

  async function copiar(texto, areaTexto) {
    try {
      await navigator.clipboard.writeText(texto);
    } catch (e) {
      areaTexto.focus(); areaTexto.select();
      if (!document.execCommand || !document.execCommand("copy")) {
        avisar("No se pudo copiar solo: selecciona el texto y cópialo.", "error");
        return;
      }
    }
    avisar("Mensaje copiado. Pégalo en WhatsApp o en un correo.", "exito");
  }

  /** ``cuentas``: [{persona, codigo, vence_en}]. El código se muestra UNA vez; el servidor solo guarda su huella. */
  function mostrarCodigos(titulo, cuentas) {
    const colegio = nombreColegioActual();
    const bloques = cuentas.map(({ persona, codigo, vence_en: vence }) => {
      const mensaje = mensajeInvitacion(persona, codigo, vence, colegio);
      const area = h("textarea", { readonly: true, "aria-label": `Mensaje para ${persona.nombre}` }, mensaje);
      return h("div", { clase: "codigo-caja" },
               h("strong", {}, persona.nombre), h("span", { clase: "nota" }, persona.correo),
               h("div", { clase: "codigo" }, codigo),
               h("span", { clase: "nota" }, `Sirve una sola vez y vence el ${fechaCorta(vence)}.`),
               area,
               h("button", { clase: "boton chico", type: "button", alClick: () => copiar(mensaje, area) },
                 "Copiar mensaje"));
    });
    const ventana = modal(titulo, h("div", { clase: "formulario" },
      h("p", { clase: "advertencia" }, "Guarda o envía el código ahora: por seguridad no se vuelve a mostrar. "
        + "Si se pierde, genera uno nuevo."), bloques), []);
    ventana.caja.append(h("div", { clase: "modal-botones" }, botonCerrar(ventana, "Listo")));
    return ventana;
  }

  // ======================================================================================================
  // Ingreso
  // ======================================================================================================
  function campo(etiqueta, atributos, ayuda) {
    const entrada = h(atributos.tipo === "select" ? "select" : "input", { ...atributos, tipo: undefined,
                      type: atributos.tipo === "select" ? undefined : (atributos.tipo || "text") });
    return { nodo: h("label", {}, etiqueta, entrada, ayuda ? h("span", { clase: "ayuda" }, ayuda) : null), entrada };
  }

  function vistaIngreso() {
    let modo = "ingresar";
    const caja = h("div", { clase: "ingreso-tarjeta" });
    const dibujar = () => {
      const error = h("div", { clase: "error-formulario", role: "alert", hidden: true });
      const mostrarError = (texto) => { error.textContent = texto; error.hidden = false; };
      let formulario;
      if (modo === "ingresar") {
        const correo = campo("Correo", { id: "correo", type: "email", autocomplete: "username", required: true });
        const clave = campo("Contraseña", { id: "clave", type: "password", autocomplete: "current-password", required: true });
        const boton = h("button", { clase: "boton", type: "submit" }, "Ingresar");
        formulario = h("form", { clase: "formulario", novalidate: true }, correo.nodo, clave.nodo, error, boton);
        formulario.addEventListener("submit", async (e) => {
          e.preventDefault(); error.hidden = true; boton.disabled = true;
          try {
            if (!correo.entrada.value.trim() || !clave.entrada.value) throw new ErrorPanel("Escribe tu correo y tu contraseña.");
            const datos = await pedir("POST", "/login", { correo: correo.entrada.value.trim(), clave: clave.entrada.value },
                                      { sinSesion: true });
            aceptarSesion(datos);
            await arrancar();
          } catch (fallo) { mostrarError(fallo.message); } finally { boton.disabled = false; }
        });
      } else {
        const correo = campo("Correo", { id: "correo", type: "email", autocomplete: "username", required: true });
        const codigo = campo("Código de invitación", { id: "codigo", type: "text", autocomplete: "one-time-code",
                             autocapitalize: "characters", required: true }, "Ejemplo: ABCDE-FGHJK");
        const clave = campo("Elige tu contraseña", { id: "clave-nueva", type: "password", autocomplete: "new-password",
                            required: true }, "Al menos 10 caracteres, mezclando letras y números.");
        const repetir = campo("Repite la contraseña", { id: "clave-repetida", type: "password",
                              autocomplete: "new-password", required: true });
        const boton = h("button", { clase: "boton", type: "submit" }, "Activar mi cuenta");
        formulario = h("form", { clase: "formulario", novalidate: true }, correo.nodo, codigo.nodo, clave.nodo, repetir.nodo,
                       error, boton);
        formulario.addEventListener("submit", async (e) => {
          e.preventDefault(); error.hidden = true; boton.disabled = true;
          try {
            if (clave.entrada.value !== repetir.entrada.value) throw new ErrorPanel("Las dos contraseñas no coinciden.");
            const datos = await pedir("POST", "/activar", { correo: correo.entrada.value.trim(),
                                      codigo: codigo.entrada.value.trim(), clave: clave.entrada.value }, { sinSesion: true });
            aceptarSesion(datos, true);
            await arrancar();
          } catch (fallo) { mostrarError(fallo.message); } finally { boton.disabled = false; }
        });
      }
      const pestanas = h("div", { clase: "pestanas" },
        h("button", { clase: modo === "ingresar" ? "boton" : "boton contorno", type: "button",
                      alClick: () => { modo = "ingresar"; dibujar(); } }, "Ingresar"),
        h("button", { clase: modo === "codigo" ? "boton" : "boton contorno", type: "button",
                      alClick: () => { modo = "codigo"; dibujar(); } }, "Tengo un código"));
      caja.replaceChildren(
        h("div", { clase: "marca" }, h("div", { clase: "marca-icono", "aria-hidden": "true" }, "T"),
          h("div", {}, h("h1", {}, "Tutor Educa"), h("small", {}, "Panel de administración"))),
        pestanas, formulario);
      const primero = formulario.querySelector("input");
      if (primero) primero.focus();
    };
    dibujar();
    RAIZ.replaceChildren(h("div", { clase: "ingreso" }, caja));
  }

  // ======================================================================================================
  // Carga de datos y navegación
  // ======================================================================================================
  const esSuper = () => estado.sesion.usuario.rol === "superadmin";

  function consulta(parametros) {
    const p = new URLSearchParams();
    if (esSuper() && estado.colegioId !== null) p.set("colegio_id", estado.colegioId);
    for (const [clave, valor] of Object.entries(parametros || {})) p.set(clave, valor);
    const texto = p.toString();
    return texto ? `?${texto}` : "";
  }

  async function cargarColegios() {
    estado.colegios = await pedir("GET", "/admin/colegios");
    if (esSuper()) {
      const activos = estado.colegios.filter((c) => c.activo);
      if (!activos.some((c) => c.id === estado.colegioId)) estado.colegioId = activos.length ? activos[0].id : null;
    }
  }

  async function cargarPagina() {
    estado.error = "";
    if (estado.pagina === "colegios") { await cargarColegios(); return; }
    if (estado.pagina === "errores") {
      const parametros = { dias: estado.erroresDias };
      if (esSuper() && estado.erroresColegio) parametros.colegio_id = estado.erroresColegio;
      const p = new URLSearchParams(parametros).toString();
      estado.errores = await pedir("GET", `/admin/errores?${p}`);
      return;
    }
    if (esSuper() && estado.colegioId === null) return;       // todavía no hay colegio donde trabajar
    if (estado.pagina === "personas") {
      [estado.cursos, estado.personas] = await Promise.all([
        pedir("GET", `/admin/cursos${consulta()}`),
        pedir("GET", `/admin/usuarios${consulta({ limite: LIMITE_PERSONAS })}`)]);
    } else if (estado.pagina === "cursos") {
      [estado.cursos, estado.docentes] = await Promise.all([
        pedir("GET", `/admin/cursos${consulta()}`),
        pedir("GET", `/admin/usuarios${consulta({ rol: "docente", limite: LIMITE_PERSONAS })}`)]);
    }
  }

  // Cada carga lleva un número: si la persona cambia de sección mientras otra todavía carga, la respuesta atrasada
  // se descarta y no pisa a la más nueva.
  let secuencia = 0;

  async function ir(pagina) {
    const mia = ++secuencia;
    estado.pagina = pagina;
    estado.cargando = true;
    estado.error = "";
    dibujar();
    let fallo = null;
    try { await cargarPagina(); } catch (e) { fallo = e; }
    if (mia !== secuencia || !estado.sesion) return;
    if (fallo) estado.error = fallo.message;
    estado.cargando = false;
    dibujar();
  }

  async function arrancar() {
    const mia = ++secuencia;
    estado.cargando = true;
    dibujar();
    let fallo = null;
    try {
      await cargarColegios();
      if (mia === secuencia) {
        estado.pagina = esSuper() && estado.colegioId === null ? "colegios" : "personas";
        await cargarPagina();
      }
    } catch (e) { fallo = e; }
    if (mia !== secuencia || !estado.sesion) return;
    if (fallo) estado.error = fallo.message;
    estado.cargando = false;
    dibujar();
  }

  // ======================================================================================================
  // Estructura de la página
  // ======================================================================================================
  function dibujar() {
    if (!estado.sesion) return;
    const u = estado.sesion.usuario;
    const paginas = [["personas", "Personas"], ["cursos", "Cursos"], ["errores", "Errores"]];
    if (esSuper()) paginas.push(["colegios", "Colegios"]);

    let selectorColegio = null;
    if (esSuper() && estado.pagina !== "colegios" && estado.pagina !== "errores") {
      const activos = estado.colegios.filter((c) => c.activo);
      selectorColegio = h("label", {}, "Colegio",
        h("select", { id: "colegio-activo", alChange: (e) => { estado.colegioId = Number(e.target.value); ir(estado.pagina); } },
          activos.map((c) => h("option", { value: c.id, selected: c.id === estado.colegioId }, c.nombre))));
    }

    const cabecera = h("header", { clase: "cabecera" },
      h("div", { clase: "marca" }, h("div", { clase: "marca-icono", "aria-hidden": "true" }, "T"),
        h("div", {}, h("strong", {}, "Tutor Educa"), h("small", {}, u.rol === "admin" ? (u.colegio || "Colegio") : "Plataforma"))),
      h("div", { clase: "quien" }, selectorColegio, h("span", {}, `${u.nombre} · ${PERFILES[u.rol]}`),
        h("button", { clase: "boton contorno chico", type: "button", id: "salir", alClick: () => cerrarSesion("Cerraste la sesión.") },
          "Salir")));
    const menu = h("nav", { clase: "menu", "aria-label": "Secciones" },
      paginas.map(([clave, texto]) => h("button", { type: "button", "data-pagina": clave,
                                          "aria-current": estado.pagina === clave ? "page" : null,
                                          alClick: () => ir(clave) }, texto)));
    let contenido;
    if (estado.cargando) contenido = h("p", { clase: "vacio" }, "Cargando…");
    else if (estado.error) contenido = h("div", { clase: "tarjeta" }, h("p", { clase: "error-formulario", role: "alert" }, estado.error));
    else if (estado.pagina === "colegios") contenido = vistaColegios();
    else if (estado.pagina === "errores") contenido = vistaErrores();
    else if (esSuper() && estado.colegioId === null && estado.pagina !== "errores")
      contenido = h("p", { clase: "vacio" }, "Aún no hay colegios activos. Crea uno en la sección Colegios.");
    else contenido = estado.pagina === "cursos" ? vistaCursos() : vistaPersonas();
    RAIZ.replaceChildren(cabecera, menu, h("main", {}, contenido));
  }

  // ======================================================================================================
  // Personas
  // ======================================================================================================
  const estadoDe = (p) => !p.activo ? ["baja", "Desactivada"] : p.pendiente ? ["falta", "Falta activar"] : ["ok", "Activa"];

  function detalleDe(p) {
    const cursoPorId = new Map(estado.cursos.map((c) => [c.id, c]));
    const personaPorId = new Map(estado.personas.map((x) => [x.id, x]));
    if (p.rol === "estudiante") {
      const curso = cursoPorId.get(p.curso_id);
      const apoderado = personaPorId.get(p.apoderado_id);
      return [curso ? curso.nombre : "Sin curso", h("small", {}, apoderado ? `Apoderado/a: ${apoderado.nombre}` : "Sin apoderado/a")];
    }
    if (p.rol === "docente") {
      const suyos = estado.cursos.filter((c) => c.docente_id === p.id).map((c) => c.nombre);
      return suyos.length ? suyos.join(", ") : "Sin cursos";
    }
    if (p.rol === "apoderado") {
      const hijos = estado.personas.filter((x) => x.rol === "estudiante" && x.apoderado_id === p.id).map((x) => x.nombre);
      return hijos.length ? hijos.join(", ") : "Sin estudiantes vinculados";
    }
    return "Administra el colegio";
  }

  function vistaPersonas() {
    const f = estado.filtros;
    const zona = h("div", {});
    const pintar = () => {
      const texto = normalizar(f.buscar);
      const lista = estado.personas.filter((p) =>
        (!f.rol || p.rol === f.rol) && (!f.curso || String(p.curso_id) === f.curso)
        && (!texto || normalizar(p.nombre).includes(texto) || normalizar(p.correo).includes(texto)));
      if (!lista.length) {
        zona.replaceChildren(h("p", { clase: "vacio" }, estado.personas.length
          ? "Ninguna persona coincide con los filtros." : "Todavía no hay personas en este colegio. Crea la primera con «Nueva persona»."));
        return;
      }
      zona.replaceChildren(
        h("table", { clase: "tabla" },
          h("thead", {}, h("tr", {}, ["Nombre", "Perfil", "Detalle", "Estado", "Acciones"].map((t) => h("th", { scope: "col" }, t)))),
          h("tbody", {}, lista.map(filaPersona))),
        estado.personas.length >= LIMITE_PERSONAS
          ? h("p", { clase: "nota" }, `Se muestran las primeras ${LIMITE_PERSONAS} personas: usa los filtros para acotar.`) : null);
    };
    const filtroRol = h("select", { id: "filtro-rol", alChange: (e) => { f.rol = e.target.value; pintar(); } },
      h("option", { value: "" }, "Todos los perfiles"),
      ["docente", "estudiante", "apoderado", "admin"].map((r) => h("option", { value: r, selected: f.rol === r }, PERFILES[r])));
    const filtroCurso = h("select", { id: "filtro-curso", alChange: (e) => { f.curso = e.target.value; pintar(); } },
      h("option", { value: "" }, "Todos los cursos"),
      estado.cursos.map((c) => h("option", { value: c.id, selected: f.curso === String(c.id) }, c.nombre)));
    const buscar = h("input", { id: "filtro-buscar", type: "search", placeholder: "Nombre o correo", value: f.buscar,
                                alInput: (e) => { f.buscar = e.target.value; pintar(); } });
    buscar.value = f.buscar;
    pintar();
    return h("div", { clase: "formulario" },
      h("div", { clase: "barra" }, h("h2", {}, "Personas"),
        h("button", { clase: "boton", type: "button", id: "nueva-persona", alClick: () => formularioPersona() }, "Nueva persona")),
      h("div", { clase: "filtros" }, h("label", {}, "Perfil", filtroRol), h("label", {}, "Curso", filtroCurso),
        h("label", {}, "Buscar", buscar)),
      zona);
  }

  function filaPersona(p) {
    const [clase, texto] = estadoDe(p);
    const yo = p.id === estado.sesion.usuario.id;
    const gestionable = esSuper() || p.rol !== "admin";
    const botones = [];
    if (gestionable) {
      botones.push(h("button", { clase: "boton contorno chico", type: "button", "data-accion": "editar",
                                 alClick: () => formularioEditarPersona(p) }, "Editar"));
      if (p.activo && !yo) botones.push(h("button", { clase: "boton contorno chico", type: "button", "data-accion": "codigo",
                                                      alClick: () => pedirCodigoNuevo(p) }, "Código nuevo"));
      if (!yo) botones.push(p.activo
        ? h("button", { clase: "boton peligro chico", type: "button", "data-accion": "desactivar", alClick: () => desactivar(p) }, "Desactivar")
        : h("button", { clase: "boton contorno chico", type: "button", "data-accion": "reactivar", alClick: () => reactivar(p) }, "Reactivar"));
    }
    return h("tr", { "data-persona": p.id },
      h("td", { "data-etiqueta": "Nombre" }, h("strong", {}, p.nombre), h("small", {}, p.correo)),
      h("td", { "data-etiqueta": "Perfil" }, PERFILES[p.rol] || p.rol),
      h("td", { "data-etiqueta": "Detalle" }, detalleDe(p)),
      h("td", { "data-etiqueta": "Estado" }, h("span", { clase: `insignia ${clase}` }, texto)),
      h("td", { "data-etiqueta": "Acciones" }, h("div", { clase: "acciones" }, botones.length ? botones : "—")));
  }

  function pedirCodigoNuevo(p) {
    confirmar(`Código nuevo para ${p.nombre}`,
      "La contraseña actual de esta persona (si la tiene) dejará de servir y los códigos anteriores se anulan. "
      + "Se genera un código nuevo que tendrás que entregarle.", "Generar código", async (cerrar) => {
        const r = await pedir("POST", `/admin/usuarios/${p.id}/invitacion`);
        cerrar();
        mostrarCodigos("Código nuevo", [{ persona: r.usuario, codigo: r.codigo, vence_en: r.vence_en }]);
        await ir("personas");
      });
  }

  function desactivar(p) {
    confirmar(`Desactivar a ${p.nombre}`, "No podrá ingresar, pero no se borra nada: puedes reactivarla cuando quieras.",
      "Desactivar", async (cerrar) => {
        const r = await pedir("PATCH", `/admin/usuarios/${p.id}`, { activo: false });
        cerrar();
        if (r.advertencias && r.advertencias.length) {
          const v = modal("Revisa esto", h("div", { clase: "formulario" }, r.advertencias.map((t) => h("p", { clase: "advertencia" }, t))), []);
          v.caja.append(h("div", { clase: "modal-botones" }, botonCerrar(v, "Entendido")));
        } else avisar(`${p.nombre} quedó desactivada.`, "exito");
        await ir("personas");
      }, true);
  }

  async function reactivar(p) {
    try {
      await pedir("PATCH", `/admin/usuarios/${p.id}`, { activo: true });
      avisar(`${p.nombre} quedó activa de nuevo.`, "exito");
      await ir("personas");
    } catch (fallo) { avisar(fallo.message, "error"); }
  }

  /** Alta de una persona. ``fijo``: {rol, colegio} para abrirlo ya preparado (por ejemplo, desde Colegios). */
  function formularioPersona(fijo) {
    const roles = esSuper() ? ["docente", "estudiante", "apoderado", "admin"] : ["docente", "estudiante", "apoderado"];
    const rol = campo("Perfil", { id: "p-rol", tipo: "select", required: true });
    for (const r of roles) rol.entrada.append(h("option", { value: r, selected: (fijo && fijo.rol === r) }, PERFILES[r]));
    const nombre = campo("Nombre completo", { id: "p-nombre", required: true, autocomplete: "off" });
    const correo = campo("Correo", { id: "p-correo", type: "email", required: true, autocomplete: "off" });
    const cursoNombre = campo("Nombre del curso", { id: "p-curso-nombre", autocomplete: "off" }, "Ejemplo: 7° Básico B");
    const cursoNivel = campo("Nivel", { id: "p-curso-nivel", autocomplete: "off" }, "Ejemplo: 7° básico");
    const bloqueDocente = h("fieldset", { clase: "grupo" }, h("legend", {}, "Primer curso (opcional)"),
      h("div", { clase: "fila" }, cursoNombre.nodo, cursoNivel.nodo));
    const curso = campo("Curso", { id: "p-curso", tipo: "select" });
    curso.entrada.append(h("option", { value: "" }, "Elige un curso"));
    for (const c of estado.cursos) curso.entrada.append(h("option", { value: c.id }, c.nombre));
    const apCorreo = campo("Correo del apoderado/a", { id: "p-ap-correo", type: "email", autocomplete: "off" },
                           "Si ya tiene cuenta se vincula; si no, se crea.");
    const apNombre = campo("Nombre del apoderado/a", { id: "p-ap-nombre", autocomplete: "off" }, "Solo si aún no tiene cuenta.");
    const bloqueEstudiante = h("fieldset", { clase: "grupo" }, h("legend", {}, "Curso y apoderado/a"), curso.nodo,
      h("div", { clase: "fila" }, apCorreo.nodo, apNombre.nodo));
    const colegioNombre = fijo && fijo.colegio ? fijo.colegio.nombre : nombreColegioActual();
    const mostrar = () => {
      bloqueDocente.hidden = rol.entrada.value !== "docente";
      bloqueEstudiante.hidden = rol.entrada.value !== "estudiante";
    };
    rol.entrada.addEventListener("change", mostrar);
    if (fijo && fijo.rol) { rol.entrada.value = fijo.rol; if (fijo.bloquearRol) rol.entrada.disabled = true; }
    mostrar();
    ventanaFormulario("Nueva persona", [h("p", { clase: "nota" }, `Colegio: ${colegioNombre}`), rol.nodo,
      h("div", { clase: "fila" }, nombre.nodo, correo.nodo), bloqueDocente, bloqueEstudiante],
      "Crear y obtener código", async (cerrar) => {
        const cuerpo = { correo: correo.entrada.value.trim(), nombre: nombre.entrada.value.trim(), rol: rol.entrada.value };
        if (esSuper()) cuerpo.colegio_id = fijo && fijo.colegio ? fijo.colegio.id : estado.colegioId;
        if (cuerpo.rol === "docente" && (cursoNombre.entrada.value.trim() || cursoNivel.entrada.value.trim())) {
          if (!cursoNombre.entrada.value.trim() || !cursoNivel.entrada.value.trim())
            throw new ErrorPanel("Para crear el primer curso escribe su nombre y su nivel.");
          cuerpo.curso_nuevo = { nombre: cursoNombre.entrada.value.trim(), nivel: cursoNivel.entrada.value.trim() };
        }
        if (cuerpo.rol === "estudiante") {
          if (!curso.entrada.value) throw new ErrorPanel("Elige el curso del estudiante. Si no hay ninguno, crea primero un curso.");
          cuerpo.curso_id = Number(curso.entrada.value);
          if (apCorreo.entrada.value.trim()) {
            cuerpo.apoderado_correo = apCorreo.entrada.value.trim();
            if (apNombre.entrada.value.trim()) cuerpo.apoderado_nombre = apNombre.entrada.value.trim();
          }
        }
        const r = await pedir("POST", "/admin/usuarios", cuerpo);
        cerrar();
        const cuentas = [{ persona: r.usuario, codigo: r.codigo, vence_en: r.vence_en }];
        if (r.apoderado && r.apoderado.codigo)
          cuentas.push({ persona: r.apoderado.usuario, codigo: r.apoderado.codigo, vence_en: r.apoderado.vence_en });
        else if (r.apoderado && r.apoderado.existente)
          avisar(`Se vinculó a ${r.apoderado.usuario.nombre}, que ya tenía cuenta.`, "exito");
        mostrarCodigos("Cuenta creada", cuentas);
        if (estado.pagina !== "colegios") await ir(estado.pagina);
      });
  }

  function formularioEditarPersona(p) {
    const nombre = campo("Nombre completo", { id: "e-nombre", required: true, value: p.nombre, autocomplete: "off" });
    nombre.entrada.value = p.nombre;
    const partes = [nombre.nodo];
    let curso, apCorreo, apNombre, quitar;
    if (p.rol === "estudiante") {
      curso = campo("Curso", { id: "e-curso", tipo: "select" });
      for (const c of estado.cursos) curso.entrada.append(h("option", { value: c.id, selected: c.id === p.curso_id }, c.nombre));
      const actual = estado.personas.find((x) => x.id === p.apoderado_id);
      apCorreo = campo("Cambiar apoderado/a: correo", { id: "e-ap-correo", type: "email", autocomplete: "off" },
                       actual ? `Hoy: ${actual.nombre} (${actual.correo})` : "Hoy no tiene apoderado/a.");
      apNombre = campo("Nombre del nuevo apoderado/a", { id: "e-ap-nombre", autocomplete: "off" }, "Solo si aún no tiene cuenta.");
      quitar = h("input", { id: "e-quitar", type: "checkbox" });
      partes.push(curso.nodo, h("fieldset", { clase: "grupo" }, h("legend", {}, "Apoderado/a"),
        h("div", { clase: "fila" }, apCorreo.nodo, apNombre.nodo),
        actual ? h("label", { clase: "casilla" }, quitar, "Quitar al apoderado/a actual") : null));
    }
    ventanaFormulario(`Editar a ${p.nombre}`, partes, "Guardar cambios", async (cerrar) => {
      const nuevoNombre = nombre.entrada.value.trim();
      let r;
      if (p.rol === "estudiante") {
        const cuerpo = {};
        if (nuevoNombre !== p.nombre) cuerpo.nombre = nuevoNombre;
        if (Number(curso.entrada.value) !== p.curso_id) cuerpo.curso_id = Number(curso.entrada.value);
        if (apCorreo.entrada.value.trim()) {
          cuerpo.apoderado_correo = apCorreo.entrada.value.trim();
          if (apNombre.entrada.value.trim()) cuerpo.apoderado_nombre = apNombre.entrada.value.trim();
        } else if (quitar.checked) cuerpo.quitar_apoderado = true;
        if (!Object.keys(cuerpo).length) throw new ErrorPanel("No cambiaste nada.");
        r = await pedir("PATCH", `/admin/estudiantes/${p.id}`, cuerpo);
      } else {
        if (nuevoNombre === p.nombre) throw new ErrorPanel("No cambiaste nada.");
        r = await pedir("PATCH", `/admin/usuarios/${p.id}`, { nombre: nuevoNombre });
      }
      cerrar();
      avisar("Cambios guardados.", "exito");
      if (r.apoderado && r.apoderado.codigo)
        mostrarCodigos("Cuenta del apoderado/a", [{ persona: r.apoderado.usuario, codigo: r.apoderado.codigo, vence_en: r.apoderado.vence_en }]);
      await ir("personas");
    });
  }

  // ======================================================================================================
  // Cursos
  // ======================================================================================================
  function vistaCursos() {
    const activas = estado.docentes.filter((d) => d.activo);
    const cuerpo = estado.cursos.length
      ? h("table", { clase: "tabla" },
          h("thead", {}, h("tr", {}, ["Curso", "Nivel", "Año", "Docente", "Estudiantes", "Acciones"].map((t) => h("th", { scope: "col" }, t)))),
          h("tbody", {}, estado.cursos.map((c) => h("tr", { "data-curso": c.id },
            h("td", { "data-etiqueta": "Curso" }, h("strong", {}, c.nombre)),
            h("td", { "data-etiqueta": "Nivel" }, c.nivel), h("td", { "data-etiqueta": "Año" }, c.anio),
            h("td", { "data-etiqueta": "Docente" }, c.docente),
            h("td", { "data-etiqueta": "Estudiantes" }, c.estudiantes),
            h("td", { "data-etiqueta": "Acciones" }, h("button", { clase: "boton contorno chico", type: "button",
              "data-accion": "editar-curso", alClick: () => formularioCurso(c, activas) }, "Editar"))))))
      : h("p", { clase: "vacio" }, "Todavía no hay cursos en este colegio.");
    return h("div", { clase: "formulario" },
      h("div", { clase: "barra" }, h("h2", {}, "Cursos"),
        h("button", { clase: "boton", type: "button", id: "nuevo-curso", alClick: () => formularioCurso(null, activas) }, "Nuevo curso")),
      cuerpo);
  }

  function formularioCurso(curso, docentes) {
    if (!docentes.length) {
      const v = modal("Primero una docente", h("p", {}, "Un curso necesita una docente a cargo. Crea la cuenta de la docente "
        + "en la sección Personas y vuelve aquí."), []);
      v.caja.append(h("div", { clase: "modal-botones" }, botonCerrar(v, "Entendido")));
      return;
    }
    const nombre = campo("Nombre del curso", { id: "c-nombre", required: true, autocomplete: "off" }, "Ejemplo: 7° Básico B");
    const nivel = campo("Nivel", { id: "c-nivel", required: true, autocomplete: "off" }, "Ejemplo: 7° básico");
    const docente = campo("Docente a cargo", { id: "c-docente", tipo: "select", required: true });
    for (const d of docentes) docente.entrada.append(h("option", { value: d.id, selected: curso && d.id === curso.docente_id }, d.nombre));
    if (curso) { nombre.entrada.value = curso.nombre; nivel.entrada.value = curso.nivel; }
    ventanaFormulario(curso ? `Editar ${curso.nombre}` : "Nuevo curso",
      [h("div", { clase: "fila" }, nombre.nodo, nivel.nodo), docente.nodo], curso ? "Guardar cambios" : "Crear curso",
      async (cerrar) => {
        const n = nombre.entrada.value.trim(), v = nivel.entrada.value.trim(), d = Number(docente.entrada.value);
        if (!n || !v) throw new ErrorPanel("Escribe el nombre y el nivel del curso.");
        if (curso) {
          const cuerpo = {};
          if (n !== curso.nombre) cuerpo.nombre = n;
          if (v !== curso.nivel) cuerpo.nivel = v;
          if (d !== curso.docente_id) cuerpo.docente_id = d;
          if (!Object.keys(cuerpo).length) throw new ErrorPanel("No cambiaste nada.");
          await pedir("PATCH", `/admin/cursos/${curso.id}`, cuerpo);
        } else {
          const cuerpo = { nombre: n, nivel: v, docente_id: d };
          if (esSuper()) cuerpo.colegio_id = estado.colegioId;
          await pedir("POST", "/admin/cursos", cuerpo);
        }
        cerrar();
        avisar(curso ? "Curso actualizado." : "Curso creado.", "exito");
        await ir("cursos");
      });
  }

  // ======================================================================================================
  // Errores de la app
  // ======================================================================================================
  function vistaErrores() {
    const datos = estado.errores || { total: 0, grupos: [], dias: estado.erroresDias };
    const dias = h("select", { id: "errores-dias", alChange: (e) => { estado.erroresDias = Number(e.target.value); ir("errores"); } },
      [7, 30, 90].map((d) => h("option", { value: d, selected: d === estado.erroresDias }, `Últimos ${d} días`)));
    let colegio = null;
    if (esSuper()) {
      colegio = h("label", {}, "Colegio",
        h("select", { id: "errores-colegio", alChange: (e) => { estado.erroresColegio = e.target.value; ir("errores"); } },
          h("option", { value: "" }, "Todos los colegios"),
          estado.colegios.map((c) => h("option", { value: c.id, selected: String(c.id) === estado.erroresColegio }, c.nombre))));
    }
    const cuerpo = datos.grupos.length
      ? h("table", { clase: "tabla" },
          h("thead", {}, h("tr", {}, ["Error", "Dónde", "Veces", "Última vez", "Versión", "Detalle"].map((t) => h("th", { scope: "col" }, t)))),
          h("tbody", {}, datos.grupos.map((g) => h("tr", { "data-error": g.huella },
            h("td", { "data-etiqueta": "Error" }, h("strong", {}, g.tipo), h("small", {}, g.mensaje || "—")),
            h("td", { "data-etiqueta": "Dónde" }, g.pantalla || "—"),
            h("td", { "data-etiqueta": "Veces" }, h("span", { clase: g.veces > 5 ? "insignia falta" : "insignia ok" }, g.veces)),
            h("td", { "data-etiqueta": "Última vez" }, g.ultima_vez),
            h("td", { "data-etiqueta": "Versión" }, `${g.version || "—"} · ${g.plataforma || "—"}`),
            h("td", { "data-etiqueta": "Detalle" }, h("button", { clase: "boton contorno chico", type: "button",
              "data-accion": "ver-error", alClick: () => detalleError(g) }, "Ver"))))))
      : h("p", { clase: "vacio" }, "No hay errores registrados en este período. ¡Buenas noticias!");
    return h("div", { clase: "formulario" },
      h("div", { clase: "barra" }, h("h2", {}, "Errores de la app"),
        h("div", { clase: "filtros" }, colegio, h("label", {}, "Período", dias))),
      h("p", { clase: "nota" }, `${datos.total} ${datos.total === 1 ? "error" : "errores"} en ${datos.grupos.length} `
        + `${datos.grupos.length === 1 ? "causa distinta" : "causas distintas"}. Se agrupan por causa (mismo error en el mismo lugar). `
        + "No incluyen nombres, correos ni contraseñas, y se borran a los 90 días."),
      cuerpo);
  }

  function detalleError(g) {
    const ventana = modal(`${g.tipo}`, h("div", { clase: "formulario" },
      h("p", {}, g.mensaje || "Sin mensaje."),
      h("p", { clase: "nota" }, `Pantalla: ${g.pantalla || "—"} · Versión: ${g.version || "—"} · Plataforma: ${g.plataforma || "—"}`),
      h("p", { clase: "nota" }, `Primera vez: ${g.primera_vez} · Última vez: ${g.ultima_vez} · Veces: ${g.veces}`),
      g.traza ? h("pre", { clase: "traza", tabindex: "0", "aria-label": "Traza del error" }, g.traza)
              : h("p", { clase: "nota" }, "Este registro no tiene traza: la app se cerró sin avisar (cierre inesperado).")), []);
    ventana.caja.append(h("div", { clase: "modal-botones" }, botonCerrar(ventana, "Cerrar")));
  }

  // ======================================================================================================
  // Colegios (solo superadmin)
  // ======================================================================================================
  function vistaColegios() {
    const cuerpo = estado.colegios.length
      ? h("table", { clase: "tabla" },
          h("thead", {}, h("tr", {}, ["Colegio", "Estado", "Acciones"].map((t) => h("th", { scope: "col" }, t)))),
          h("tbody", {}, estado.colegios.map((c) => h("tr", { "data-colegio": c.id },
            h("td", { "data-etiqueta": "Colegio" }, h("strong", {}, c.nombre)),
            h("td", { "data-etiqueta": "Estado" }, h("span", { clase: `insignia ${c.activo ? "ok" : "baja"}` }, c.activo ? "Activo" : "Suspendido")),
            h("td", { "data-etiqueta": "Acciones" }, h("div", { clase: "acciones" },
              h("button", { clase: "boton contorno chico", type: "button", "data-accion": "renombrar", alClick: () => formularioColegio(c) }, "Renombrar"),
              c.activo ? h("button", { clase: "boton contorno chico", type: "button", "data-accion": "crear-admin",
                alClick: () => formularioPersona({ rol: "admin", bloquearRol: true, colegio: c }) }, "Crear administrador/a") : null,
              h("button", { clase: c.activo ? "boton peligro chico" : "boton contorno chico", type: "button",
                "data-accion": c.activo ? "suspender" : "reactivar-colegio", alClick: () => cambiarEstadoColegio(c) },
                c.activo ? "Suspender" : "Reactivar")))))))
      : h("p", { clase: "vacio" }, "Todavía no hay colegios. Crea el primero.");
    return h("div", { clase: "formulario" },
      h("div", { clase: "barra" }, h("h2", {}, "Colegios"),
        h("button", { clase: "boton", type: "button", id: "nuevo-colegio", alClick: () => formularioColegio(null) }, "Nuevo colegio")),
      cuerpo);
  }

  function formularioColegio(colegio) {
    const nombre = campo("Nombre del colegio", { id: "col-nombre", required: true, autocomplete: "off" });
    if (colegio) nombre.entrada.value = colegio.nombre;
    ventanaFormulario(colegio ? "Renombrar colegio" : "Nuevo colegio", [nombre.nodo], colegio ? "Guardar" : "Crear colegio",
      async (cerrar) => {
        const texto = nombre.entrada.value.trim();
        if (colegio) await pedir("PATCH", `/admin/colegios/${colegio.id}`, { nombre: texto });
        else await pedir("POST", "/admin/colegios", { nombre: texto });
        cerrar();
        avisar(colegio ? "Nombre actualizado." : "Colegio creado. Ahora crea su administrador/a.", "exito");
        await ir("colegios");
      });
  }

  function cambiarEstadoColegio(c) {
    const suspender = c.activo;
    confirmar(suspender ? `Suspender ${c.nombre}` : `Reactivar ${c.nombre}`,
      suspender ? "Nadie de este colegio podrá ingresar a la app ni al panel hasta que lo reactives. No se borra nada."
                : "Las personas de este colegio podrán ingresar de nuevo.",
      suspender ? "Suspender" : "Reactivar", async (cerrar) => {
        await pedir("PATCH", `/admin/colegios/${c.id}`, { activo: !suspender });
        cerrar();
        avisar(suspender ? "Colegio suspendido." : "Colegio reactivado.", "exito");
        await ir("colegios");
      }, suspender);
  }

  // ======================================================================================================
  // Inicio
  // ======================================================================================================
  async function iniciar() {
    for (const evento of ["click", "keydown", "touchstart"]) document.addEventListener(evento, reiniciarInactividad, { passive: true });
    let guardado = null;
    try { guardado = JSON.parse(sessionStorage.getItem(CLAVE_SESION) || "null"); } catch (e) { guardado = null; }
    if (guardado && guardado.renovacion && guardado.usuario
        && (guardado.usuario.rol === "admin" || guardado.usuario.rol === "superadmin")) {
      estado.sesion = { acceso: null, renovacion: guardado.renovacion, usuario: guardado.usuario };
      if (await renovar()) { reiniciarInactividad(); await arrancar(); return; }
      estado.sesion = null;
      try { sessionStorage.removeItem(CLAVE_SESION); } catch (e) { /* nada */ }
    }
    vistaIngreso();
  }

  iniciar();
})();
