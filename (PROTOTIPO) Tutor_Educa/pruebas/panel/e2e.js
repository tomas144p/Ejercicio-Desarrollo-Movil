/*
 * Prueba de punta a punta del panel: abre /panel en jsdom contra el servidor real y recorre los flujos.
 * Uso:  node e2e.js <url> <correo admin> <clave> <correo superadmin>
 */
"use strict";
const { JSDOM } = require("jsdom");
const [base, correoAdmin, clave, correoSuper] = process.argv.slice(2);
const CLAVE_NUEVA = "Clave-larga-2026";

const pausa = (ms) => new Promise((r) => setTimeout(r, ms));
async function esperar(fn, mensaje, ms = 8000) {
  const inicio = Date.now();
  while (Date.now() - inicio < ms) {
    try { const r = fn(); if (r) return r; } catch (e) { /* aún no */ }
    await pausa(25);
  }
  throw new Error(`Tiempo agotado esperando: ${mensaje}`);
}
function verificar(condicion, mensaje) { if (!condicion) throw new Error(`Falló: ${mensaje}`); }

async function abrir() {
  const dom = await JSDOM.fromURL(`${base}/panel`, {
    runScripts: "dangerously", resources: "usable", pretendToBeVisual: true,
    beforeParse(w) {
      w.fetch = (u, o) => fetch(new URL(u, w.location.href), o);
      Object.defineProperty(w.navigator, "clipboard", { value: { writeText: async (t) => { w.__copiado = t; } } });
    },
  });
  const w = dom.window;
  const d = w.document;
  const api = {
    w, d,
    q: (s, raiz) => (raiz || d).querySelector(s),
    qa: (s, raiz) => [...(raiz || d).querySelectorAll(s)],
    texto: (s, raiz) => { const e = (raiz || d).querySelector(s); return e ? e.textContent : ""; },
    escribir(sel, valor) { const e = typeof sel === "string" ? d.querySelector(sel) : sel;
      e.value = valor; e.dispatchEvent(new w.Event("input", { bubbles: true })); e.dispatchEvent(new w.Event("change", { bubbles: true })); },
    clic(el) { el.dispatchEvent(new w.MouseEvent("click", { bubbles: true, cancelable: true })); },
    boton(texto, raiz) { return [...(raiz || d).querySelectorAll("button")].find((b) => b.textContent.trim() === texto); },
    fila(texto) { return [...d.querySelectorAll("tbody tr")].find((f) => f.textContent.includes(texto)); },
    modal: () => d.querySelector(".modal"),
    cerrar: () => dom.window.close(),
  };
  await esperar(() => api.q("form"), "pantalla de ingreso");
  return api;
}

async function ingresar(p, correo, claveUsada) {
  p.escribir("#correo", correo); p.escribir("#clave", claveUsada);
  p.clic(p.boton("Ingresar", p.q("form")));
}

async function guion() {
  // ---------------------------------------------------------------- Administrador del colegio
  let p = await abrir();
  console.log("· ingreso con contraseña incorrecta");
  await ingresar(p, correoAdmin, "otra-clave-equivocada");
  await esperar(() => p.q(".error-formulario:not([hidden])"), "mensaje de error");
  verificar(/incorrectos/.test(p.texto(".error-formulario")), "mensaje de credenciales");
  verificar(!p.q("header.cabecera"), "no debe entrar con clave incorrecta");

  console.log("· ingreso correcto y lista de personas");
  await ingresar(p, correoAdmin, clave);
  await esperar(() => p.q("tr[data-persona]"), "lista de personas");
  verificar(p.q("header.cabecera"), "cabecera del panel");
  verificar(!p.boton("Colegios"), "el admin no ve la sección Colegios");
  verificar(!p.q("#colegio-activo"), "el admin no elige colegio");
  const total = p.qa("tr[data-persona]").length;
  verificar(total >= 5, `hay personas del colegio (${total})`);
  verificar(!p.qa("tr[data-persona]").some((f) => /Superadministrador/.test(f.textContent)), "no ve a la superadmin");

  console.log("· filtros por perfil y búsqueda");
  p.escribir("#filtro-rol", "docente");
  verificar(p.qa("tr[data-persona]").length >= 1 && p.qa("tr[data-persona]").every((f) => f.children[1].textContent === "Docente"), "solo docentes");
  p.escribir("#filtro-rol", "");
  p.escribir("#filtro-buscar", "sofía");
  verificar(p.qa("tr[data-persona]").length >= 1 && p.qa("tr[data-persona]").every((f) => /sof[ií]a/i.test(f.textContent)), "búsqueda sin tildes");
  p.escribir("#filtro-buscar", "");

  console.log("· crear docente con su primer curso y obtener el código");
  p.clic(p.q("#nueva-persona"));
  p.escribir("#p-nombre", "Paula Rojas Díaz"); p.escribir("#p-correo", "paula.rojas@colegio.test");
  p.escribir("#p-curso-nombre", "8° Básico A"); p.escribir("#p-curso-nivel", "8° básico");
  p.clic(p.boton("Crear y obtener código", p.modal()));
  await esperar(() => p.q(".codigo"), "código de invitación");
  const codigoPaula = p.texto(".codigo");
  verificar(/^[A-Z0-9]{5}-[A-Z0-9]{5}$/.test(codigoPaula), `formato del código (${codigoPaula})`);
  const mensaje = p.q(".codigo-caja textarea").value;
  verificar(mensaje.includes("paula.rojas@colegio.test") && mensaje.includes(codigoPaula) && mensaje.includes("Abre la app"), "mensaje listo para copiar");
  p.clic(p.boton("Copiar mensaje"));
  await esperar(() => p.w.__copiado, "copiado al portapapeles");
  verificar(p.w.__copiado.includes(codigoPaula), "el portapapeles trae el código");
  p.clic(p.boton("Listo"));
  await esperar(() => p.fila("Paula Rojas"), "la docente aparece en la lista");
  verificar(/Falta activar/.test(p.fila("Paula Rojas").textContent), "queda pendiente de activar");
  verificar(/8° Básico A/.test(p.fila("Paula Rojas").textContent), "muestra su curso");

  console.log("· un texto con HTML se muestra como texto y no se ejecuta");
  p.clic(p.q("#nueva-persona"));
  p.escribir("#p-rol", "apoderado");
  p.escribir("#p-nombre", '<img src=x onerror="window.__xss=1"> Mala');
  p.escribir("#p-correo", "xss@colegio.test");
  p.clic(p.boton("Crear y obtener código", p.modal()));
  await esperar(() => p.q(".codigo"), "código del apoderado");
  p.clic(p.boton("Listo"));
  const filaXss = await esperar(() => p.fila("Mala"), "fila con el nombre raro");
  verificar(p.w.__xss === undefined, "no se ejecutó código del nombre");
  verificar(!p.q("img"), "no se creó ningún elemento <img>");
  verificar(filaXss.textContent.includes("<img"), "el texto aparece tal cual");

  console.log("· cursos: crear y editar");
  p.clic(p.boton("Cursos", p.q("nav.menu")));
  await esperar(() => p.q("#nuevo-curso"), "sección Cursos");
  p.clic(p.q("#nuevo-curso"));
  p.escribir("#c-nombre", "Taller"); p.escribir("#c-nivel", "7° básico");
  const opcionPaula = [...p.qa("#c-docente option")].find((o) => /Paula/.test(o.textContent));
  verificar(opcionPaula, "Paula aparece como docente posible");
  p.escribir("#c-docente", opcionPaula.value);
  p.clic(p.boton("Crear curso", p.modal()));
  await esperar(() => p.fila("Taller"), "el curso nuevo");
  p.clic(p.q("[data-accion=editar-curso]", p.fila("Taller")));
  p.escribir("#c-nombre", "Taller B");
  p.clic(p.boton("Guardar cambios", p.modal()));
  await esperar(() => p.fila("Taller B"), "curso renombrado");
  p.clic(p.q("[data-accion=editar-curso]", p.fila("Taller B")));
  p.clic(p.boton("Guardar cambios", p.modal()));
  await esperar(() => /No cambiaste nada/.test(p.texto(".error-formulario")), "aviso de que no hay cambios");
  p.clic(p.boton("Cancelar", p.modal()));

  console.log("· cursos: activar las clases de sábado");
  p.clic(p.q("[data-accion=editar-curso]", p.fila("Taller B")));
  verificar(!p.q("#c-sabado").checked, "el sábado parte apagado");
  p.clic(p.q("#c-sabado"));
  p.clic(p.boton("Guardar cambios", p.modal()));
  await esperar(() => /Con clases/.test((p.fila("Taller B") || { textContent: "" }).textContent), "el curso queda con clases de sábado");

  console.log("· calendario: feriados de Chile, evento propio y quitar");
  p.clic(p.boton("Calendario", p.q("nav.menu")));
  await esperar(() => p.q("#cargar-feriados"), "sección Calendario");
  verificar(/Reloj en orden/.test(p.texto("#reloj-servidor")) && /hora de Chile/.test(p.texto("#reloj-servidor")), "muestra la hora del servidor y que el reloj está en orden");
  p.escribir("#eventos-anio", "2026");
  await esperar(() => p.q("#cargar-feriados") && /2026/.test(p.q("#cargar-feriados").textContent), "año 2026");
  await esperar(() => p.qa("tr[data-evento]").length >= 16, "la demostración ya trae los feriados de 2026");
  const antes = p.qa("tr[data-evento]").length;
  verificar(p.fila("Navidad") && /No hay clases/.test(p.fila("Navidad").textContent), "un feriado no tiene clases");
  p.clic(p.q("#cargar-feriados"));
  await esperar(() => /ya estaban cargados/.test(p.texto("#aviso")), "cargar de nuevo no duplica");
  verificar(p.qa("tr[data-evento]").length === antes, "no se duplicaron");
  console.log("  · año 2027 parte vacío y se cargan 17 feriados");
  p.escribir("#eventos-anio", "2027");
  await esperar(() => /2027/.test(p.q("#cargar-feriados").textContent), "año 2027");
  await esperar(() => /Todavía no hay eventos en 2027/.test(p.texto("main")), "2027 sin eventos");
  p.clic(p.q("#cargar-feriados"));
  await esperar(() => p.qa("tr[data-evento]").length === 17, "17 feriados de 2027");
  p.clic(p.q("#nuevo-evento"));
  p.escribir("#e-titulo", "Día del alumno"); p.escribir("#e-tipo", "celebracion");
  verificar(!p.q("#e-sin-clases").checked, "una celebración sí tiene clases");
  p.escribir("#e-desde", "2027-12-02");
  p.clic(p.boton("Guardar evento", p.modal()));
  await esperar(() => p.fila("Día del alumno"), "el evento nuevo");
  verificar(/Hay clases/.test(p.fila("Día del alumno").textContent) && /Todo el colegio/.test(p.fila("Día del alumno").textContent), "evento de todo el colegio");
  p.clic(p.q("#nuevo-evento"));
  p.escribir("#e-titulo", "Mal"); p.escribir("#e-desde", "2027-12-10"); p.escribir("#e-hasta", "2027-12-01");
  p.clic(p.boton("Guardar evento", p.modal()));
  await esperar(() => /no puede ser anterior/.test(p.texto(".error-formulario")), "rechaza un rango al revés");
  p.clic(p.boton("Cancelar", p.modal()));
  p.clic(p.q("[data-accion=quitar-evento]", p.fila("Día del alumno")));
  p.clic(p.boton("Quitar", p.modal()));
  await esperar(() => !p.fila("Día del alumno"), "el evento se quitó");
  p.escribir("#eventos-anio", "2028");
  await esperar(() => /2028/.test(p.q("#cargar-feriados").textContent), "año 2028");
  p.clic(p.q("#cargar-feriados"));
  await esperar(() => /Aún no tenemos los feriados de 2028/.test(p.texto("#aviso")), "año sin feriados precargados");

  console.log("· editar estudiante: pasarlo al curso nuevo");
  p.clic(p.boton("Personas", p.q("nav.menu")));
  await esperar(() => p.q("tr[data-persona]"), "lista de personas");
  const filaEstudiante = p.qa("tr[data-persona]").find((f) => f.children[1].textContent === "Estudiante");
  const nombreEst = filaEstudiante.querySelector("strong").textContent;
  p.clic(p.q("[data-accion=editar]", filaEstudiante));
  const opcion = [...p.qa("#e-curso option")].find((o) => /Taller B/.test(o.textContent));
  p.escribir("#e-curso", opcion.value);
  p.clic(p.boton("Guardar cambios", p.modal()));
  await esperar(() => /Taller B/.test((p.fila(nombreEst) || { textContent: "" }).textContent), "estudiante en el curso nuevo");

  console.log("· errores de la app: lista agrupada, detalle y texto seguro");
  p.clic(p.boton("Errores", p.q("nav.menu")));
  await esperar(() => p.q("tr[data-error]"), "lista de errores");
  const filasError = p.qa("tr[data-error]");
  verificar(filasError.length === 2, `dos causas distintas (${filasError.length})`);
  verificar(filasError[0].children[2].textContent.trim() === "3", "la causa más frecuente va primero, con 3 veces");
  verificar(/4 errores en 2 causas/.test(p.texto("main")), "resumen del período");
  verificar(p.texto("main").includes("<b>negrita</b>") && !p.q("main b"), "un mensaje con HTML se ve como texto");
  verificar(!p.q("#errores-colegio"), "el admin no elige colegio en errores");
  p.clic(p.q("[data-accion=ver-error]", filasError[0]));
  await esperar(() => p.q(".traza"), "detalle del error");
  verificar(/views\/leccion_screen\.py:10 en abrir/.test(p.texto(".traza")), "la traza se muestra");
  verificar(/Pantalla: leccion/.test(p.texto(".modal")), "datos del error");
  p.clic(p.boton("Cerrar", p.modal()));
  p.escribir("#errores-dias", "7");
  await esperar(() => p.q("tr[data-error]") && p.q("#errores-dias").value === "7", "cambio de período");
  p.clic(p.boton("Personas", p.q("nav.menu")));
  await esperar(() => p.q("tr[data-persona]"), "vuelve a Personas");

  console.log("· desactivar a una docente con cursos avisa; reactivar");
  p.clic(p.q("[data-accion=desactivar]", p.fila("Paula Rojas")));
  p.clic(p.boton("Desactivar", p.modal()));
  await esperar(() => /cursos a cargo/.test(p.texto(".modal")), "advertencia de cursos a cargo");
  p.clic(p.boton("Entendido"));
  await esperar(() => /Desactivada/.test((p.fila("Paula Rojas") || { textContent: "" }).textContent), "quedó desactivada");
  verificar(!p.q("[data-accion=codigo]", p.fila("Paula Rojas")), "una cuenta desactivada no recibe códigos");
  p.clic(p.q("[data-accion=reactivar]", p.fila("Paula Rojas")));
  await esperar(() => /Falta activar/.test((p.fila("Paula Rojas") || { textContent: "" }).textContent), "reactivada");

  console.log("· código nuevo anula el anterior");
  p.clic(p.q("[data-accion=codigo]", p.fila("Paula Rojas")));
  p.clic(p.boton("Generar código", p.modal()));
  await esperar(() => p.q(".codigo"), "código nuevo");
  const codigoNuevo = p.texto(".codigo");
  verificar(codigoNuevo !== codigoPaula, "el código cambió");
  p.clic(p.boton("Listo"));

  console.log("· una docente que activa su cuenta en el panel queda activada, pero no entra");
  p.clic(p.q("#salir"));
  await esperar(() => p.q("form") && !p.q("header.cabecera"), "vuelve al ingreso");
  p.clic(p.boton("Tengo un código"));
  p.escribir("#correo", "paula.rojas@colegio.test"); p.escribir("#codigo", codigoNuevo);
  p.escribir("#clave-nueva", CLAVE_NUEVA); p.escribir("#clave-repetida", CLAVE_NUEVA);
  p.clic(p.boton("Activar mi cuenta"));
  await esperar(() => /quedó activada/.test(p.texto(".error-formulario")), "mensaje para quien no es administrador");
  verificar(!p.q("header.cabecera"), "una docente no entra al panel");
  verificar(p.w.sessionStorage.getItem("tutor_panel") === null, "no se guardó ninguna sesión");
  p.cerrar();

  // ---------------------------------------------------------------- Superadministradora
  p = await abrir();
  console.log("· superadmin: colegios");
  await ingresar(p, correoSuper, clave);
  await esperar(() => p.q("#colegio-activo"), "selector de colegio");
  verificar(p.boton("Colegios", p.q("nav.menu")), "ve la sección Colegios");
  console.log("· superadmin: errores de todos los colegios");
  p.clic(p.boton("Errores", p.q("nav.menu")));
  await esperar(() => p.q("#errores-colegio"), "errores con selector de colegio");
  verificar(!p.q("#colegio-activo"), "en errores no se usa el selector general");
  await esperar(() => p.q("tr[data-error]"), "errores de todos los colegios");
  verificar(p.qa("tr[data-error]").length === 2, "ve las dos causas");
  p.clic(p.boton("Colegios", p.q("nav.menu")));
  await esperar(() => p.q("#nuevo-colegio"), "sección Colegios");
  p.clic(p.q("#nuevo-colegio"));
  p.escribir("#col-nombre", "Escuela Norte");
  p.clic(p.boton("Crear colegio", p.modal()));
  await esperar(() => p.fila("Escuela Norte"), "colegio nuevo");
  p.clic(p.q("[data-accion=crear-admin]", p.fila("Escuela Norte")));
  verificar(p.q("#p-rol").value === "admin" && p.q("#p-rol").disabled, "el perfil queda fijo en administrador/a");
  p.escribir("#p-nombre", "Marta Soto Vera"); p.escribir("#p-correo", "marta.soto@norte.test");
  p.clic(p.boton("Crear y obtener código", p.modal()));
  await esperar(() => p.q(".codigo"), "código del administrador");
  const codigoAdmin = p.texto(".codigo");
  verificar(p.q(".codigo-caja textarea").value.includes("/panel"), "el mensaje del admin apunta al panel web");
  p.clic(p.boton("Listo"));

  console.log("· suspender y reactivar un colegio");
  p.clic(p.q("[data-accion=suspender]", p.fila("Escuela Norte")));
  p.clic(p.boton("Suspender", p.modal()));
  await esperar(() => /Suspendido/.test((p.fila("Escuela Norte") || { textContent: "" }).textContent), "colegio suspendido");
  p.clic(p.q("[data-accion=reactivar-colegio]", p.fila("Escuela Norte")));
  p.clic(p.boton("Reactivar", p.modal()));
  await esperar(() => /Activo/.test((p.fila("Escuela Norte") || { textContent: "" }).textContent), "colegio reactivado");
  p.cerrar();

  // ---------------------------------------------------------------- El nuevo administrador activa su cuenta
  p = await abrir();
  console.log("· un administrador nuevo activa su cuenta con el código y entra");
  p.clic(p.boton("Tengo un código"));
  p.escribir("#correo", "marta.soto@norte.test"); p.escribir("#codigo", codigoAdmin);
  p.escribir("#clave-nueva", CLAVE_NUEVA); p.escribir("#clave-repetida", "otra-distinta-123");
  p.clic(p.boton("Activar mi cuenta"));
  await esperar(() => /no coinciden/.test(p.texto(".error-formulario")), "contraseñas distintas");
  p.escribir("#clave-repetida", CLAVE_NUEVA);
  p.clic(p.boton("Activar mi cuenta"));
  await esperar(() => p.q("header.cabecera"), "entra al panel");
  verificar(/Marta Soto Vera/.test(p.texto("header.cabecera")) && /Escuela Norte/.test(p.texto("header.cabecera")), "cabecera con su nombre y colegio");
  await esperar(() => /Todavía no hay personas|tr\[data-persona\]/.test(p.texto("main")) || p.q("tr[data-persona]"), "lista");
  p.clic(p.boton("Errores", p.q("nav.menu")));
  await esperar(() => /No hay errores registrados/.test(p.texto("main")), "un colegio nuevo no ve errores de otros");
  p.clic(p.boton("Personas", p.q("nav.menu")));
  await esperar(() => p.q("tr[data-persona]"), "vuelve a Personas");
  verificar(p.qa("tr[data-persona]").some((f) => /Marta Soto/.test(f.textContent)), "se ve a sí misma");
  verificar(!p.q("[data-accion=desactivar]", p.fila("Marta Soto")), "no puede desactivarse a sí misma");
  p.clic(p.q("#salir"));
  await esperar(() => !p.q("header.cabecera"), "cierre de sesión");
  p.cerrar();
  console.log("TODO BIEN");
}

guion().then(() => process.exit(0), (error) => { console.error(error.stack || error); process.exit(1); });
