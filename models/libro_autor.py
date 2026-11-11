"""Tabla intermedia de la relación N-N entre Libro y Autor."""

from sqlmodel import Field, SQLModel


class LibroAutor(SQLModel, table=True):
    """Asociación entre un libro y un autor.

    La clave primaria compuesta impide asociar dos veces el mismo par.
    """

    libro_id: int | None = Field(default=None, foreign_key="libro.id", primary_key=True)
    autor_id: int | None = Field(default=None, foreign_key="autor.id", primary_key=True)
