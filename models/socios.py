"""Modelos de la entidad Socio."""

from typing import TYPE_CHECKING

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.prestamos import Prestamo


class SocioBase(SQLModel):
    """Campos de negocio de un socio. El email es único."""

    nombre: str = Field(index=True)
    email: EmailStr = Field(unique=True, index=True)
    activo: bool = True


class Socio(SocioBase, table=True):
    """Tabla de socios. Un socio inactivo no puede pedir préstamos."""

    id: int | None = Field(default=None, primary_key=True)
    prestamos: list["Prestamo"] = Relationship(back_populates="socio")
