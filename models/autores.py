"""Modelos de la entidad Autor."""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from models.libro_autor import LibroAutor

if TYPE_CHECKING:
    from models.libros import Libro


class AutorBase(SQLModel):
    """Campos de negocio de un autor, compartidos por la tabla y los esquemas."""

    nombre: str = Field(index=True)
    nacionalidad: str


class Autor(AutorBase, table=True):
    """Tabla de autores. Un autor puede tener muchos libros (relación N-N)."""

    id: int | None = Field(default=None, primary_key=True)
    libros: list["Libro"] = Relationship(
        back_populates="autores", link_model=LibroAutor
    )
