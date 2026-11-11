"""Modelos y esquemas de la entidad Socio."""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from models.comunes import ActualizacionParcial, EmailNormalizado, NombreTexto

if TYPE_CHECKING:
    from models.prestamos import Prestamo


class SocioBase(SQLModel):
    """Campos de negocio de un socio. El email es único."""

    nombre: NombreTexto = Field(index=True)
    email: EmailNormalizado = Field(unique=True, index=True)
    activo: bool = True


class Socio(SocioBase, table=True):
    """Tabla de socios. Un socio inactivo no puede pedir préstamos."""

    id: int | None = Field(default=None, primary_key=True)
    prestamos: list["Prestamo"] = Relationship(back_populates="socio")


class SocioCrear(SocioBase):
    """Esquema de entrada para el alta: el cliente no envía el id."""


class SocioActualizar(ActualizacionParcial):
    """Esquema de entrada para la modificación parcial de un socio."""

    nombre: NombreTexto | None = None
    email: EmailNormalizado | None = None
    activo: bool | None = None


class SocioLeer(SocioBase):
    """Esquema de salida: los campos del socio más su id."""

    id: int
