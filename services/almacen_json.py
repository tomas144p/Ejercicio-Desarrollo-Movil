"""
Persistencia de los intentos (pruebas rendidas) en un archivo JSON.

Los datos se guardan en el dispositivo y se recuperan al volver a abrir la app.
Todo acceso al disco usa ``with open(..., encoding="utf-8")``, de modo que el
archivo se cierra solo aunque ocurra un error. Python puro: no importa Kivy.
"""

import json
from pathlib import Path

from models.modelos import Intento


class AlmacenIntentos:
    """Lee y escribe la lista de intentos en ``intentos.json``."""

    def __init__(self, ruta: Path):
        self.ruta = Path(ruta)

    def cargar(self) -> list:
        """Devuelve los intentos guardados. Si el archivo no existe o está dañado, devuelve una lista vacía."""
        try:
            with open(self.ruta, "r", encoding="utf-8") as archivo:
                filas = json.load(archivo)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
        intentos = []
        for fila in filas:
            try:
                intentos.append(Intento.desde_dict(fila))
            except (KeyError, TypeError, ValueError):
                continue  # un registro dañado no impide leer los demás
        return intentos

    def guardar(self, intentos: list) -> None:
        """Escribe toda la lista en el archivo (cada objeto se serializa con ``to_dict()``)."""
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ruta, "w", encoding="utf-8") as archivo:
            json.dump([intento.to_dict() for intento in intentos], archivo, indent=2, ensure_ascii=False)

    def agregar(self, intento: Intento) -> None:
        """Agrega un intento nuevo: lee el archivo, suma el registro y lo vuelve a guardar."""
        self.agregar_varios([intento])

    def agregar_varios(self, nuevos: list) -> int:
        """Agrega varios intentos de una vez (sin repetir los que ya están, se comparan por ``codigo``)."""
        intentos = self.cargar()
        existentes = {i.codigo for i in intentos}
        faltantes = [i for i in nuevos if i.codigo not in existentes]
        if faltantes:
            self.guardar(intentos + faltantes)
        return len(faltantes)

    def de_estudiante(self, estudiante_id: int) -> list:
        """Intentos de un estudiante, del más reciente al más antiguo."""
        propios = [i for i in self.cargar() if i.estudiante_id == estudiante_id]
        return sorted(propios, key=lambda i: i.realizado_en, reverse=True)
