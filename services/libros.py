"""Reglas de negocio de los libros."""

from collections.abc import Sequence

from sqlmodel import Session, col, select

from models import Libro, LibroActualizar, LibroCrear
from services.comunes import eliminar, guardar, obtener_o_404
from services.excepciones import ConflictoDeNegocio


def _mensaje_isbn_duplicado(isbn: str) -> str:
    """Arma el mensaje de conflicto por ISBN repetido."""
    return f"Ya existe un libro con el ISBN {isbn}"


def crear_libro(sesion: Session, datos: LibroCrear) -> Libro:
    """Da de alta un libro; el ISBN no puede repetirse (409)."""
    libro = Libro.model_validate(datos)
    guardar(sesion, libro, _mensaje_isbn_duplicado(datos.isbn))
    return libro


def listar_libros(sesion: Session, skip: int, limit: int) -> Sequence[Libro]:
    """Devuelve una página de libros ordenados por id."""
    consulta = select(Libro).order_by(col(Libro.id)).offset(skip).limit(limit)
    return sesion.exec(consulta).all()


def obtener_libro(sesion: Session, libro_id: int) -> Libro:
    """Devuelve un libro o lanza RecursoNoEncontrado."""
    return obtener_o_404(sesion, Libro, libro_id)


def actualizar_libro(sesion: Session, libro_id: int, cambios: LibroActualizar) -> Libro:
    """Modifica solo los campos enviados; el ISBN sigue siendo único (409)."""
    libro = obtener_o_404(sesion, Libro, libro_id)
    isbn = cambios.isbn if cambios.isbn is not None else libro.isbn
    libro.sqlmodel_update(cambios.model_dump(exclude_unset=True))
    guardar(sesion, libro, _mensaje_isbn_duplicado(isbn))
    return libro


def eliminar_libro(sesion: Session, libro_id: int) -> None:
    """Borra un libro, salvo que tenga préstamos (409).

    Sus vínculos con autores se eliminan junto con el libro.
    """
    libro = obtener_o_404(sesion, Libro, libro_id)
    if libro.prestamos:
        raise ConflictoDeNegocio(
            f"No se puede eliminar el libro {libro_id}: tiene préstamos registrados"
        )
    eliminar(sesion, libro)
