"""Modelos y esquemas de la entidad Préstamo."""

from datetime import date
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.libros import Libro
    from models.socios import Socio


class Prestamo(SQLModel, table=True):
    """Tabla de préstamos: vincula un socio con un libro.

    Un préstamo está activo mientras fecha_devolucion sea nula. El
    vencimiento y la multa los calcula la capa de servicios.
    """

    id: int | None = Field(default=None, primary_key=True)
    socio_id: int = Field(foreign_key="socio.id")
    libro_id: int = Field(foreign_key="libro.id")
    fecha_prestamo: date
    fecha_vencimiento: date
    fecha_devolucion: date | None = None
    multa: int = 0

    socio: "Socio" = Relationship(back_populates="prestamos")
    libro: "Libro" = Relationship(back_populates="prestamos")


class PrestamoCrear(SQLModel):
    """Esquema de entrada para pedir un préstamo.

    El cliente solo indica quién y qué libro: las fechas y la multa las
    decide el servidor, no se aceptan del cliente.
    """

    socio_id: int
    libro_id: int


class PrestamoLeer(SQLModel):
    """Esquema de salida: el préstamo más dos datos calculados al responder."""

    id: int
    socio_id: int
    libro_id: int
    fecha_prestamo: date
    fecha_vencimiento: date
    fecha_devolucion: date | None
    multa: int
    vencido: bool = Field(
        description="true si sigue sin devolverse y ya pasó su vencimiento"
    )
    dias_atraso: int = Field(
        description="Días de atraso: hasta hoy si está activo, o hasta la "
        "devolución si ya se devolvió"
    )
