"""Modelos de datos: importa las tablas para registrarlas en la metadata."""

from models.autores import Autor, AutorActualizar, AutorBase, AutorCrear, AutorLeer
from models.libro_autor import LibroAutor
from models.libros import (
    Libro,
    LibroActualizar,
    LibroBase,
    LibroCrear,
    LibroLeer,
)
from models.prestamos import Prestamo
from models.socios import (
    Socio,
    SocioActualizar,
    SocioBase,
    SocioCrear,
    SocioLeer,
)

__all__ = [
    "Autor",
    "AutorActualizar",
    "AutorBase",
    "AutorCrear",
    "AutorLeer",
    "Libro",
    "LibroActualizar",
    "LibroAutor",
    "LibroBase",
    "LibroCrear",
    "LibroLeer",
    "Prestamo",
    "Socio",
    "SocioActualizar",
    "SocioBase",
    "SocioCrear",
    "SocioLeer",
]
