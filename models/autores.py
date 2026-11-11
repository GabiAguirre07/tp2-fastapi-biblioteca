"""Modelos y esquemas de la entidad Autor."""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from models.comunes import ActualizacionParcial, NacionalidadTexto, NombreTexto
from models.libro_autor import LibroAutor

if TYPE_CHECKING:
    from models.libros import Libro


class AutorBase(SQLModel):
    """Campos de un autor, compartidos por la tabla y los esquemas."""

    nombre: NombreTexto = Field(index=True)
    nacionalidad: NacionalidadTexto


class Autor(AutorBase, table=True):
    """Tabla de autores. Un autor puede tener muchos libros (relación N-N)."""

    id: int | None = Field(default=None, primary_key=True)
    libros: list["Libro"] = Relationship(
        back_populates="autores", link_model=LibroAutor
    )


class AutorCrear(AutorBase):
    """Esquema de entrada para el alta: el cliente no envía el id."""


class AutorActualizar(ActualizacionParcial):
    """Esquema de entrada para la modificación parcial de un autor."""

    nombre: NombreTexto | None = None
    nacionalidad: NacionalidadTexto | None = None


class AutorLeer(AutorBase):
    """Esquema de salida: los campos del autor más su id."""

    id: int
