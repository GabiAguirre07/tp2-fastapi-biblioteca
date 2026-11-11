"""Modelos de datos. Importa todas las tablas para registrarlas en la metadata."""

from models.autores import Autor, AutorBase
from models.libro_autor import LibroAutor
from models.libros import Libro, LibroBase
from models.prestamos import Prestamo
from models.socios import Socio, SocioBase

__all__ = [
    "Autor",
    "AutorBase",
    "Libro",
    "LibroAutor",
    "LibroBase",
    "Prestamo",
    "Socio",
    "SocioBase",
]
