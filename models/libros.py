"""Modelos de la entidad Libro."""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint
from sqlmodel import Field, Relationship, SQLModel

from models.libro_autor import LibroAutor

if TYPE_CHECKING:
    from models.autores import Autor
    from models.prestamos import Prestamo

# Año de la imprenta de tipos móviles: ningún libro puede ser anterior.
ANIO_MINIMO = 1450
# Año actual, calculado al iniciar la app, como límite superior del año.
ANIO_ACTUAL = date.today().year


class LibroBase(SQLModel):
    """Campos de negocio de un libro, con sus reglas de validación.

    El ISBN es único, el stock no puede ser negativo y el año debe estar
    entre ANIO_MINIMO y el año actual.
    """

    titulo: str = Field(index=True)
    isbn: str = Field(unique=True, index=True)
    stock: int = Field(ge=0)
    anio: int = Field(ge=ANIO_MINIMO, le=ANIO_ACTUAL)


class Libro(LibroBase, table=True):
    """Tabla de libros. Se relaciona N-N con autores y 1-N con préstamos.

    Las validaciones de LibroBase no se ejecutan en las clases tabla, por eso
    el stock no negativo y el año mínimo se refuerzan con restricciones CHECK
    en la base. El año máximo no se refuerza ahí porque cambia con el tiempo.
    """

    __table_args__ = (
        CheckConstraint("stock >= 0", name="ck_libro_stock_no_negativo"),
        CheckConstraint(f"anio >= {ANIO_MINIMO}", name="ck_libro_anio_minimo"),
    )

    id: int | None = Field(default=None, primary_key=True)
    autores: list["Autor"] = Relationship(
        back_populates="libros", link_model=LibroAutor
    )
    prestamos: list["Prestamo"] = Relationship(back_populates="libro")
