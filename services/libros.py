"""Reglas de negocio de los libros."""

from collections.abc import Sequence

from sqlmodel import Session, col, select

from models import Autor, Libro, LibroActualizar, LibroAutor, LibroCrear
from services.comunes import eliminar, guardar, obtener_o_404
from services.excepciones import ConflictoDeNegocio, RecursoNoEncontrado


def _mensaje_isbn_duplicado(isbn: str) -> str:
    """Arma el mensaje de conflicto por ISBN repetido."""
    return f"Ya existe un libro con el ISBN {isbn}"


def crear_libro(sesion: Session, datos: LibroCrear) -> Libro:
    """Da de alta un libro; el ISBN no puede repetirse (409)."""
    libro = Libro.model_validate(datos)
    guardar(sesion, libro, _mensaje_isbn_duplicado(datos.isbn))
    return libro


def listar_libros(
    sesion: Session, skip: int, limit: int, disponibles: bool | None = None
) -> Sequence[Libro]:
    """Devuelve una página de libros ordenados por id.

    Con disponibles=True lista solo los libros con stock; con
    disponibles=False, solo los agotados (stock 0); con None, todos. El
    filtro se aplica en la consulta antes de saltar y limitar, así que la
    paginación cuenta sobre los libros ya filtrados.
    """
    consulta = select(Libro)
    if disponibles is True:
        consulta = consulta.where(col(Libro.stock) > 0)
    elif disponibles is False:
        consulta = consulta.where(col(Libro.stock) == 0)
    consulta = consulta.order_by(col(Libro.id)).offset(skip).limit(limit)
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


def asociar_autor(sesion: Session, libro_id: int, autor_id: int) -> Libro:
    """Asocia un autor a un libro y devuelve el libro con sus autores.

    Lanza RecursoNoEncontrado si el libro o el autor no existen (404) y
    ConflictoDeNegocio si ya estaban asociados (409). El duplicado lo
    detecta la clave primaria compuesta de LibroAutor, no una consulta previa.
    """
    libro = obtener_o_404(sesion, Libro, libro_id)
    autor = obtener_o_404(sesion, Autor, autor_id)
    vinculo = LibroAutor(libro_id=libro.id, autor_id=autor.id)
    guardar(
        sesion,
        vinculo,
        f"El autor {autor_id} ya está asociado al libro {libro_id}",
    )
    sesion.refresh(libro)
    return libro


def desasociar_autor(sesion: Session, libro_id: int, autor_id: int) -> None:
    """Quita la asociación entre un libro y un autor.

    Lanza RecursoNoEncontrado si el libro o el autor no existen, o si
    existen pero no estaban asociados (404).
    """
    obtener_o_404(sesion, Libro, libro_id)
    obtener_o_404(sesion, Autor, autor_id)
    vinculo = sesion.get(LibroAutor, (libro_id, autor_id))
    if vinculo is None:
        raise RecursoNoEncontrado(
            f"El autor {autor_id} no está asociado al libro {libro_id}"
        )
    eliminar(sesion, vinculo)
