"""Reglas de negocio de los autores."""

from collections.abc import Sequence

from sqlmodel import Session, col, select

from models import Autor, AutorActualizar, AutorCrear, Libro, LibroAutor
from services.comunes import eliminar, guardar, obtener_o_404
from services.excepciones import ConflictoDeNegocio


def crear_autor(sesion: Session, datos: AutorCrear) -> Autor:
    """Da de alta un autor."""
    autor = Autor.model_validate(datos)
    guardar(sesion, autor)
    return autor


def listar_autores(sesion: Session, skip: int, limit: int) -> Sequence[Autor]:
    """Devuelve una página de autores ordenados por id."""
    consulta = select(Autor).order_by(col(Autor.id)).offset(skip).limit(limit)
    return sesion.exec(consulta).all()


def obtener_autor(sesion: Session, autor_id: int) -> Autor:
    """Devuelve un autor o lanza RecursoNoEncontrado."""
    return obtener_o_404(sesion, Autor, autor_id)


def actualizar_autor(sesion: Session, autor_id: int, cambios: AutorActualizar) -> Autor:
    """Modifica solo los campos enviados."""
    autor = obtener_o_404(sesion, Autor, autor_id)
    autor.sqlmodel_update(cambios.model_dump(exclude_unset=True))
    guardar(sesion, autor)
    return autor


def eliminar_autor(sesion: Session, autor_id: int) -> None:
    """Borra un autor, salvo que tenga libros asociados (409)."""
    autor = obtener_o_404(sesion, Autor, autor_id)
    if autor.libros:
        raise ConflictoDeNegocio(
            f"No se puede eliminar el autor {autor_id}: tiene libros "
            "asociados. Desasocie primero sus libros."
        )
    eliminar(sesion, autor)


def listar_libros_de_autor(
    sesion: Session, autor_id: int, skip: int, limit: int
) -> Sequence[Libro]:
    """Devuelve una página de los libros de un autor, ordenados por id.

    Lanza RecursoNoEncontrado si el autor no existe (404). Cada libro
    incluye todos sus autores, no solo el consultado.
    """
    obtener_o_404(sesion, Autor, autor_id)
    consulta = (
        select(Libro)
        .join(LibroAutor, col(LibroAutor.libro_id) == col(Libro.id))
        .where(col(LibroAutor.autor_id) == autor_id)
        .order_by(col(Libro.id))
        .offset(skip)
        .limit(limit)
    )
    return sesion.exec(consulta).all()
