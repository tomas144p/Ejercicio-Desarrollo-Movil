"""Métricas de uso y desempeño del estudiante (Python puro): semestres, promedios, primer intento, textos y CSV."""

from __future__ import annotations

import csv
import io
import sys
import unittest
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))

from models.modelos import Calificacion, Intento  # noqa: E402
from services.metricas import (COLUMNAS_CSV, MIN_NOTAS, Metricas, a_csv, calcular_metricas, lectura,  # noqa: E402
                               nota_texto, resumen_curso, semestre_actual, semestre_de, variacion_texto)

S2 = semestre_de(date(2026, 9, 1))      # 2.º semestre 2026: 1 ago a 31 dic


def nota(id_, valor, fecha, asignatura="mat"):
    return Calificacion(id_, 1, asignatura, valor, "", fecha)


def intento(id_, tema, porcentaje, momento):
    return Intento(id_, f"cod-{id_:06d}", 1, tema, porcentaje // 10, 10, porcentaje, 4.0, momento)


class PruebasSemestres(unittest.TestCase):
    def test_limites_de_los_semestres(self):
        self.assertEqual(semestre_de(date(2026, 3, 1)).numero, 1)
        self.assertEqual(semestre_de(date(2026, 7, 31)).numero, 1)
        self.assertEqual(semestre_de(date(2026, 8, 1)).numero, 2)
        self.assertEqual(semestre_de(date(2026, 12, 31)).numero, 2)

    def test_enero_y_febrero_son_vacaciones(self):
        self.assertIsNone(semestre_de(date(2026, 2, 15)))
        actual = semestre_actual(date(2026, 1, 20))
        self.assertEqual((actual.anio, actual.numero), (2025, 2))      # el último que terminó

    def test_semestre_actual(self):
        self.assertEqual(semestre_actual(date(2026, 11, 17)).nombre, "2.º semestre 2026")


class PruebasMetricas(unittest.TestCase):
    def test_sin_notas_no_hay_conclusion(self):
        m = calcular_metricas(1, [], [], S2)
        self.assertEqual((m.notas, m.promedio_inicial, m.promedio_final, m.variacion), (0, None, None, None))
        self.assertEqual(m.direccion, "sin_datos")

    def test_con_pocas_notas_hay_numeros_pero_no_conclusion(self):
        m = calcular_metricas(1, [nota(1, 4.0, "2026-08-10"), nota(2, 6.0, "2026-09-10")], [], S2)
        self.assertEqual((m.notas, m.promedio_inicial, m.promedio_final), (2, 4.0, 5.0))
        self.assertEqual(m.direccion, "sin_datos")
        self.assertFalse(m.suficientes)
        self.assertIn(str(MIN_NOTAS - 2), lectura(m))

    def test_el_promedio_sube(self):
        m = calcular_metricas(1, [nota(1, 4.0, "2026-08-10"), nota(2, 5.0, "2026-09-10"), nota(3, 6.0, "2026-10-10")], [], S2)
        self.assertEqual((m.promedio_inicial, m.origen_inicial, m.promedio_final, m.variacion), (4.0, "primera_nota", 5.0, 1.0))
        self.assertEqual(m.direccion, "sube")

    def test_el_promedio_baja_y_el_estable(self):
        baja = calcular_metricas(1, [nota(1, 6.0, "2026-08-10"), nota(2, 4.0, "2026-09-10"), nota(3, 4.0, "2026-10-10")], [], S2)
        self.assertEqual((baja.variacion, baja.direccion), (-1.3, "baja"))
        estable = calcular_metricas(1, [nota(1, 5.0, "2026-08-10"), nota(2, 5.2, "2026-09-10"), nota(3, 5.0, "2026-10-10")], [], S2)
        self.assertEqual(estable.direccion, "estable")

    def test_promedio_inicial_registrado_tiene_prioridad(self):
        m = calcular_metricas(1, [nota(i, 5.0, f"2026-0{8 + i // 2}-1{i}") for i in range(1, 4)], [], S2,
                              promedio_inicial_registrado=5.5)
        self.assertEqual((m.promedio_inicial, m.origen_inicial, m.variacion, m.direccion), (5.5, "registrado", -0.5, "baja"))

    def test_solo_cuentan_las_notas_de_la_asignatura_y_del_semestre(self):
        notas = [nota(1, 7.0, "2026-05-10"),                      # otro semestre
                 nota(2, 2.0, "2026-09-10", "len"),               # otra asignatura
                 nota(3, 5.0, "2026-08-20"), nota(4, 5.0, "2026-09-20"), nota(5, 5.0, "2026-10-20")]
        m = calcular_metricas(1, notas, [], S2)
        self.assertEqual((m.notas, m.promedio_inicial, m.promedio_final), (3, 5.0, 5.0))

    def test_las_notas_se_ordenan_por_fecha_aunque_lleguen_desordenadas(self):
        m = calcular_metricas(1, [nota(3, 6.0, "2026-10-10"), nota(1, 4.0, "2026-08-10"), nota(2, 5.0, "2026-09-10")], [], S2)
        self.assertEqual(m.promedio_inicial, 4.0)

    def test_aciertos_del_primer_intento(self):
        intentos = [intento(3, "t1", 80, "2026-09-12 10:00:00"),       # llegan desordenados
                    intento(1, "t1", 40, "2026-09-10 10:00:00"),
                    intento(2, "t2", 60, "2026-09-10 11:00:00"),
                    intento(4, "t1", 100, "2026-09-12 12:00:00")]
        m = calcular_metricas(1, [], intentos, S2)
        self.assertEqual(m.pruebas, 4)
        self.assertEqual(m.temas_trabajados, 2)
        self.assertEqual(m.aciertos_primer_intento, 50.0)             # (40 + 60) / 2: solo el primer intento de cada tema
        self.assertEqual(m.mejora_practica, 60.0)                      # t1: de 40 a 100; t2 no tiene segundo intento
        self.assertEqual(m.dias_activos, 2)
        self.assertEqual(m.ultima_actividad, "2026-09-12")

    def test_sin_intentos_no_inventa_porcentajes(self):
        m = calcular_metricas(1, [], [], S2)
        self.assertEqual((m.pruebas, m.aciertos_primer_intento, m.mejora_practica, m.dias_activos), (0, None, None, 0))

    def test_los_intentos_de_otro_semestre_no_cuentan(self):
        m = calcular_metricas(1, [], [intento(1, "t1", 90, "2026-05-10 10:00:00")], S2)
        self.assertEqual(m.pruebas, 0)

    def test_formatos_de_numeros(self):
        self.assertEqual((nota_texto(5.0), nota_texto(None), variacion_texto(0.8), variacion_texto(-0.5), variacion_texto(0.0)),
                         ("5,0", "—", "+0,8", "-0,5", "0,0"))


class PruebasTextos(unittest.TestCase):
    def metricas(self, notas, intentos=()):
        return calcular_metricas(1, notas, list(intentos), S2)

    NOTAS_SUBE = [nota(1, 4.0, "2026-08-10"), nota(2, 5.0, "2026-09-10"), nota(3, 6.0, "2026-10-10")]
    NOTAS_BAJA = [nota(1, 6.0, "2026-08-10"), nota(2, 4.0, "2026-09-10"), nota(3, 4.0, "2026-10-10")]
    PRACTICA = [intento(i, f"t{i}", 70, f"2026-09-1{i} 10:00:00") for i in range(1, 4)]

    def test_la_docente_ve_la_variacion_junto_con_la_practica(self):
        con = lectura(self.metricas(self.NOTAS_SUBE, self.PRACTICA))
        self.assertIn("subió 1 punto", con)
        self.assertIn("practicó 3 pruebas", con)
        sin = lectura(self.metricas(self.NOTAS_SUBE))
        self.assertIn("todavía no practica", sin)
        self.assertIn("otras cosas", sin)                      # no se atribuye la mejora a Tutor Educa

    def test_si_baja_sin_practica_se_sugiere_un_refuerzo(self):
        self.assertIn("refuerzo", lectura(self.metricas(self.NOTAS_BAJA)))
        self.assertIn("conversar", lectura(self.metricas(self.NOTAS_BAJA, self.PRACTICA)))

    def test_el_tono_para_la_familia_es_amable(self):
        sube = lectura(self.metricas(self.NOTAS_SUBE), "apoderado", "Sofía")
        self.assertIn("Buenas noticias", sube)
        baja = lectura(self.metricas(self.NOTAS_BAJA), "apoderado", "Sofía")
        self.assertIn("bajó", baja)
        self.assertNotIn("Conviene conversar para ver qué le dificulta", baja)
        self.assertIn("Sofía", baja)

    def test_ningun_texto_afirma_una_causa(self):
        for notas in (self.NOTAS_SUBE, self.NOTAS_BAJA):
            for para in ("docente", "apoderado"):
                texto = lectura(self.metricas(notas, self.PRACTICA), para)
                self.assertNotIn("gracias a Tutor Educa", texto)
                self.assertNotIn("por culpa", texto)


class PruebasCurso(unittest.TestCase):
    def m(self, variacion, pruebas):
        base = Metricas(1, S2, notas=4, promedio_inicial=5.0, promedio_final=5.0 + variacion, variacion=variacion,
                        direccion="sube" if variacion >= 0.3 else "baja" if variacion <= -0.3 else "estable",
                        pruebas=pruebas, aciertos_primer_intento=60.0 if pruebas else None)
        return base

    def test_resumen_y_comparacion_entre_con_practica_y_sin_practica(self):
        con = [self.m(0.8, 5), self.m(0.6, 4), self.m(0.4, 3)]
        sin = [self.m(-0.2, 0), self.m(0.0, 1), self.m(-0.4, 2)]
        r = resumen_curso(con + sin)
        self.assertEqual((r.estudiantes, r.con_datos, r.subieron, r.bajaron, r.estables), (6, 6, 3, 1, 2))
        self.assertEqual((r.n_con_practica, r.n_sin_practica), (3, 3))
        self.assertEqual((r.variacion_con_practica, r.variacion_sin_practica), (0.6, -0.2))
        self.assertTrue(r.comparacion_confiable)
        self.assertEqual(r.sin_practica, 3)

    def test_no_compara_grupos_demasiado_chicos(self):
        r = resumen_curso([self.m(0.8, 5), self.m(-0.2, 0), self.m(-0.1, 0), self.m(0.0, 1)])
        self.assertFalse(r.comparacion_confiable)

    def test_curso_vacio(self):
        r = resumen_curso([])
        self.assertEqual((r.estudiantes, r.variacion_promedio, r.aciertos_primer_intento), (0, None, None))

    def test_estudiantes_con_pocas_notas_no_entran_en_la_variacion(self):
        pocos = Metricas(1, S2, notas=1, promedio_inicial=5.0, promedio_final=5.0, variacion=0.0, pruebas=2)
        r = resumen_curso([pocos, self.m(0.8, 5)])
        self.assertEqual((r.estudiantes, r.con_datos, r.variacion_promedio), (2, 1, 0.8))


class PruebasCSV(unittest.TestCase):
    def filas(self):
        m = Metricas(1, S2, notas=4, promedio_inicial=4.5, origen_inicial="primera_nota", promedio_final=5.3,
                     variacion=0.8, direccion="sube", pruebas=6, temas_trabajados=3, aciertos_primer_intento=58.3,
                     mejora_practica=21.5, dias_activos=4, ultima_actividad="2026-11-10")
        return [("Sofía Díaz", "7° Básico B", m), ("Benjamín Muñoz", "7° Básico B", m)]

    def leer(self, texto):
        return list(csv.reader(io.StringIO(texto.lstrip("\ufeff")), delimiter=";"))

    def test_formato_para_excel_en_espanol(self):
        texto = a_csv(self.filas())
        self.assertTrue(texto.startswith("\ufeff"))                       # BOM: Excel respeta las tildes
        filas = self.leer(texto)
        self.assertEqual(tuple(filas[0]), COLUMNAS_CSV)
        datos = dict(zip(COLUMNAS_CSV, filas[1]))
        self.assertEqual((datos["estudiante"], datos["promedio_inicial"], datos["variacion"], datos["aciertos_primer_intento_pct"]),
                         ("Sofía Díaz", "4,5", "0,8", "58,3"))               # decimales con coma
        self.assertEqual(datos["semestre"], "2.º semestre 2026")

    def test_la_version_anonima_no_trae_nombres(self):
        texto = a_csv(self.filas(), anonimo=True)
        self.assertNotIn("Sofía", texto)
        self.assertNotIn("Benjamín", texto)
        self.assertEqual([f[0] for f in self.leer(texto)[1:]], ["Estudiante 01", "Estudiante 02"])

    def test_valores_vacios_quedan_vacios(self):
        vacio = Metricas(1, S2)
        datos = dict(zip(COLUMNAS_CSV, self.leer(a_csv([("A", "C", vacio)]))[1]))
        self.assertEqual((datos["promedio_inicial"], datos["variacion"], datos["aciertos_primer_intento_pct"], datos["direccion"]),
                         ("", "", "", "sin_datos"))


if __name__ == "__main__":
    unittest.main()
