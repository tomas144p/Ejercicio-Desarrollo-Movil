"""Pruebas de la calculadora de notas (tarea 19): Python puro, sin Kivy ni base de datos."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models.modelos import EscalaNotas, redondear  # noqa: E402
from services import calculadora_notas as c  # noqa: E402


class PruebasLectura(unittest.TestCase):
    def test_numeros_con_coma_o_punto(self):
        self.assertEqual(c.parsear_numero("5,5"), 5.5)
        self.assertEqual(c.parsear_numero(" 5.5 "), 5.5)
        self.assertEqual(c.parsear_numero("12"), 12.0)
        self.assertEqual(c.parsear_numero(7), 7.0)

    def test_lo_que_no_es_numero_da_un_mensaje_claro(self):
        for malo in ("", "   ", None, "abc", "5,5,5", "nan", "inf", "1e999"):
            with self.assertRaises(c.ErrorCalculo, msg=repr(malo)):
                c.parsear_numero(malo, "El puntaje")
        with self.assertRaises(c.ErrorCalculo) as cm:
            c.parsear_numero("hola", "El puntaje")
        self.assertIn("El puntaje", str(cm.exception))

    def test_notas_entre_1_y_7(self):
        self.assertEqual(c.parsear_nota("1,0"), 1.0)
        self.assertEqual(c.parsear_nota("7"), 7.0)
        for malo in ("0,9", "7,1", "-3", "8"):
            with self.assertRaises(c.ErrorCalculo, msg=malo):
                c.parsear_nota(malo)

    def test_lista_de_notas(self):
        self.assertEqual(c.parsear_notas("5,5  6,0 4,2"), [5.5, 6.0, 4.2])
        self.assertEqual(c.parsear_notas("5,5;6,0\n4,2"), [5.5, 6.0, 4.2])
        self.assertEqual(c.parsear_notas(""), [])
        with self.assertRaises(c.ErrorCalculo) as cm:
            c.parsear_notas("5,5 9,9")
        self.assertIn("9,9", str(cm.exception))


class PruebasPuntajeANota(unittest.TestCase):
    def test_casos_conocidos_con_60_por_ciento(self):
        # 42 puntos: 4 + 3·6/24 = 4,75 → 4,8 (redondeo escolar)
        for puntaje, nota in ((0, 1.0), (36, 4.0), (35, 3.9), (48, 5.5), (60, 7.0), (18, 2.5), (42, 4.8)):
            self.assertEqual(c.nota_por_puntaje(60, puntaje), nota, puntaje)

    def test_la_exigencia_cambia_la_nota(self):
        self.assertEqual(c.nota_por_puntaje(60, 30, 50), 4.0)         # con 50 %, la mitad aprueba
        self.assertEqual(c.nota_por_puntaje(60, 48, 50), 5.8)
        self.assertEqual(c.nota_por_puntaje(60, 36, 70), 3.6)         # con 70 %, 36 puntos ya no alcanzan el 4,0
        self.assertGreater(c.nota_por_puntaje(60, 40, 50), c.nota_por_puntaje(60, 40, 70))

    def test_limites_en_1_y_7(self):
        for e in (0, 30, 60, 90, 100):
            self.assertEqual(c.nota_por_puntaje(60, 60, e), 7.0, e)
            self.assertGreaterEqual(c.nota_por_puntaje(60, 0, e), 1.0)
        self.assertEqual(c.nota_por_puntaje(60, 0), 1.0)
        self.assertEqual(c.nota_por_puntaje(60, -5), 1.0)             # puntaje negativo: se acota
        self.assertEqual(c.nota_por_puntaje(60, 75), 7.0)             # más que el máximo: se acota

    def test_exigencia_0_por_ciento(self):
        self.assertEqual(c.nota_por_puntaje(60, 0, 0), 4.0)           # sin exigencia, hasta un cero parte en 4,0
        self.assertEqual(c.nota_por_puntaje(60, 30, 0), 5.5)
        self.assertEqual(c.nota_por_puntaje(60, 60, 0), 7.0)

    def test_exigencia_100_por_ciento(self):
        self.assertEqual(c.nota_por_puntaje(60, 60, 100), 7.0)        # el máximo siempre es un 7,0
        self.assertEqual(c.nota_por_puntaje(60, 59, 100), 4.0)        # un punto menos: queda justo en la nota de aprobación
        self.assertEqual(c.nota_por_puntaje(60, 30, 100), 2.5)
        self.assertEqual(c.nota_por_puntaje(60, 0, 100), 1.0)

    def test_mismo_resultado_que_la_escala_de_la_app(self):
        for total in range(1, 61):
            for correctas in range(total + 1):
                self.assertEqual(c.nota_por_puntaje(total, correctas, 60), EscalaNotas.nota(correctas, total),
                                 (correctas, total))

    def test_nunca_baja_al_subir_el_puntaje(self):
        for maximo in (10, 37, 60, 100):
            for exigencia in (0, 40, 50, 60, 75, 100):
                notas = [n for _p, n in c.tabla_puntajes(maximo, exigencia)]
                self.assertEqual(notas, sorted(notas), (maximo, exigencia))
                self.assertTrue(all(1.0 <= n <= 7.0 for n in notas))

    def test_redondeo_escolar_en_la_mitad(self):
        # 20 puntos de 40 con exigencia 50 % → 4,0 justo; 21 de 40 → 4 + 3·1/20 = 4,15 → 4,2 (no 4,1)
        self.assertEqual(c.nota_por_puntaje(40, 21, 50), 4.2)
        self.assertEqual(c.nota_por_puntaje(40, 27, 50), 5.1)          # 4 + 3·7/20 = 5,05 → 5,1

    def test_datos_invalidos(self):
        for maximo, exigencia in ((0, 60), (-10, 60), (5000, 60), (60, -1), (60, 101)):
            with self.assertRaises(c.ErrorCalculo, msg=(maximo, exigencia)):
                c.nota_por_puntaje(maximo, 10, exigencia)

    def test_puntajes_con_decimales(self):
        self.assertEqual(c.nota_por_puntaje(12.5, 12.5), 7.0)
        self.assertEqual(c.nota_por_puntaje(12.5, 7.5), 4.0)


class PruebasPuntosNecesarios(unittest.TestCase):
    def test_casos_conocidos(self):
        self.assertEqual(c.puntaje_para_nota(60, 4.0), 36)
        self.assertEqual(c.puntaje_para_nota(60, 7.0), 60)
        self.assertEqual(c.puntaje_para_nota(60, 1.0), 0)
        self.assertEqual(c.puntaje_para_nota(60, 5.5), 48)
        self.assertEqual(c.puntaje_para_nota(60, 4.0, 50), 30)
        self.assertEqual(c.puntaje_para_nota(60, 4.0, 70), 42)

    def test_de_a_medio_punto(self):
        self.assertEqual(c.puntaje_para_nota(60, 4.0, paso=0.5), 35.5)       # 35,5 → 3,96 → se ve 4,0
        self.assertEqual(c.puntaje_para_nota(10, 4.0, paso=0.5), 6.0)

    def test_es_el_puntaje_mas_bajo_que_alcanza(self):
        azar = random.Random(7)
        for _ in range(400):
            maximo = azar.choice([10, 20, 25, 30, 40, 45, 50, 60, 100])
            exigencia = azar.choice([0, 40, 50, 55, 60, 65, 70, 80, 100])
            nota = round(azar.uniform(1, 7), 1)
            puntaje = c.puntaje_para_nota(maximo, nota, exigencia)
            self.assertIsNotNone(puntaje)
            self.assertGreaterEqual(c.nota_por_puntaje(maximo, puntaje, exigencia), nota, (maximo, exigencia, nota))
            if puntaje >= 1:
                self.assertLess(c.nota_por_puntaje(maximo, puntaje - 1, exigencia), nota, (maximo, exigencia, nota))

    def test_errores(self):
        with self.assertRaises(c.ErrorCalculo):
            c.puntaje_para_nota(60, 7.5)
        with self.assertRaises(c.ErrorCalculo):
            c.puntaje_para_nota(60, 0.5)
        with self.assertRaises(c.ErrorCalculo):
            c.puntaje_para_nota(60, 4.0, paso=0)


class PruebasTabla(unittest.TestCase):
    def test_tabla_completa(self):
        tabla = c.tabla_puntajes(60)
        self.assertEqual(len(tabla), 61)
        self.assertEqual(tabla[0], (0, 1.0))
        self.assertEqual(tabla[36], (36, 4.0))
        self.assertEqual(tabla[-1], (60, 7.0))

    def test_tabla_de_a_medio_punto_y_maximo_decimal(self):
        self.assertEqual(len(c.tabla_puntajes(10, paso=0.5)), 21)
        tabla = c.tabla_puntajes(12.5)
        self.assertEqual(tabla[-1], (12.5, 7.0))                    # el máximo siempre aparece
        self.assertEqual(tabla[-2][0], 12)

    def test_texto_para_compartir(self):
        texto = c.texto_tabla(60, 60)
        lineas = texto.splitlines()
        self.assertEqual(lineas[0], "Tabla de notas · 60 puntos · exigencia 60 %")
        self.assertIn("36 puntos → 4,0", lineas)
        self.assertIn("1 punto → 1,1", lineas)                       # singular
        self.assertEqual(lineas[-1], "60 puntos → 7,0")
        self.assertEqual(len(lineas), 62)
        self.assertIn("12,5 puntos", c.texto_tabla(12.5, 50))        # coma decimal, como se escribe en Chile


class PruebasNotaNecesaria(unittest.TestCase):
    def test_el_caso_que_falla_con_decimales_de_computador(self):
        # 5,5 + 6,0 + 4,2 + 4,1 = 19,8 → promedio 4,95 → 5,0. Con decimales de computador daría 4,9499999.
        r = c.nota_necesaria([(5.5, 1), (6.0, 1), (4.2, 1)], 1, 5.0)
        self.assertEqual((r.estado, r.nota, r.promedio_actual, r.mejor_promedio), ("alcanzable", 4.1, 5.2, 5.7))

    def test_con_porcentajes(self):
        r = c.nota_necesaria([(6.5, 50)], 50, 6.0)
        self.assertEqual((r.estado, r.nota), ("alcanzable", 5.4))     # (6,5 + 5,4)/2 = 5,95 → 6,0

    def test_ya_cumple(self):
        r = c.nota_necesaria([(7.0, 1)], 1, 4.0)
        self.assertEqual((r.estado, r.nota), ("ya_cumple", None))
        self.assertEqual(c.nota_necesaria([(7.0, 80)], 20, 5.0).estado, "ya_cumple")

    def test_imposible(self):
        r = c.nota_necesaria([(3.0, 1), (3.0, 1)], 1, 6.0)
        self.assertEqual((r.estado, r.nota, r.mejor_promedio), ("imposible", None, 4.3))

    def test_sin_notas_todavia(self):
        r = c.nota_necesaria([], 3, 5.0)
        self.assertEqual((r.estado, r.nota, r.promedio_actual), ("alcanzable", 5.0, None))

    def test_exactamente_7(self):
        r = c.nota_necesaria([(6.0, 1), (6.0, 1)], 1, 6.3)           # (12 + x)/3 ≥ 6,25 → x = 6,75 → 6,8
        self.assertEqual((r.estado, r.nota), ("alcanzable", 6.8))
        self.assertEqual(c.nota_necesaria([(7.0, 1)], 1, 7.0).estado, "alcanzable")
        self.assertEqual(c.nota_necesaria([(6.9, 1)], 1, 7.0).nota, 7.0)   # (6,9 + 7)/2 = 6,95 → 7,0

    def test_la_nota_necesaria_cumple_y_un_decimo_menos_no(self):
        azar = random.Random(11)
        for _ in range(500):
            actuales = [(round(azar.uniform(1, 7), 1), azar.choice([1, 1, 20, 25, 30])) for _ in range(azar.randint(0, 5))]
            falta = azar.choice([1, 2, 20, 30])
            objetivo = round(azar.uniform(1, 7), 1)
            r = c.nota_necesaria(actuales, falta, objetivo)
            pesos = sum(p for _n, p in actuales)
            suma = sum(n * p for n, p in actuales)

            def promedio(x):
                from fractions import Fraction
                return redondear(float((Fraction(str(suma)) + Fraction(str(x)) * falta) / (Fraction(str(pesos)) + falta)))

            if r.estado == "alcanzable":
                self.assertGreaterEqual(promedio(r.nota), objetivo, (actuales, falta, objetivo, r))
                if r.nota > 1.0:
                    self.assertLess(promedio(redondear(r.nota - 0.1)), objetivo, (actuales, falta, objetivo, r))
            elif r.estado == "imposible":
                self.assertLess(promedio(7.0), objetivo)
            else:
                self.assertGreaterEqual(promedio(1.0), objetivo)

    def test_datos_invalidos(self):
        for actuales, falta, objetivo in (([(5.0, 1)], 0, 5.0), ([(5.0, 1)], -1, 5.0), ([(8.0, 1)], 1, 5.0),
                                          ([(5.0, 0)], 1, 5.0), ([(5.0, 1)], 1, 7.5), ([(5.0, 1)], 1, 0.5)):
            with self.assertRaises(c.ErrorCalculo, msg=(actuales, falta, objetivo)):
                c.nota_necesaria(actuales, falta, objetivo)


if __name__ == "__main__":
    unittest.main()
