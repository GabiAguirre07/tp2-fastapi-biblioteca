"""Operaciones de servicio compartidas por todas las entidades."""

from typing import TypeVar

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel

from services.excepciones import ConflictoDeNegocio, RecursoNoEncontrado

T = TypeVar("T", bound=SQLModel)


def obtener_o_404(sesion: Session, modelo: type[T], id: int) -> T:
    """Devuelve el registro con ese id o lanza RecursoNoEncontrado."""
    registro = sesion.get(modelo, id)
    if registro is None:
        raise RecursoNoEncontrado(f"{modelo.__name__} con id {id} no existe")
    return registro


def guardar(
    sesion: Session, registro: SQLModel, mensaje_conflicto: str | None = None
) -> None:
    """Persiste el registro y lo refresca con los valores de la base.

    Si la base rechaza el guardado por una restricción de unicidad y se
    indicó mensaje_conflicto, lanza ConflictoDeNegocio. Confiar en la
    restricción de la base (y no en consultar antes) evita la carrera en
    la que dos pedidos simultáneos pasan la consulta y duplican el dato.
    """
    try:
        sesion.add(registro)
        sesion.commit()
    except IntegrityError as error:
        sesion.rollback()
        if mensaje_conflicto is None:
            raise
        raise ConflictoDeNegocio(mensaje_conflicto) from error
    sesion.refresh(registro)


def eliminar(sesion: Session, registro: SQLModel) -> None:
    """Borra el registro y confirma el cambio."""
    sesion.delete(registro)
    sesion.commit()
