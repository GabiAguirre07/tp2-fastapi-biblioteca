"""Endpoints de libros: alta, consulta, listado, modificación y baja."""

from collections.abc import Sequence

from fastapi import APIRouter, status

from database import SesionDep
from models import Libro, LibroActualizar, LibroCrear, LibroLeer
from routers.comunes import PaginacionDep, RESPUESTA_404, RESPUESTA_409
from services import libros as servicio

router = APIRouter(prefix="/libros", tags=["Libros"])


@router.post(
    "",
    response_model=LibroLeer,
    status_code=status.HTTP_201_CREATED,
    summary="Alta de libro",
    responses={**RESPUESTA_409},
)
def crear_libro(datos: LibroCrear, sesion: SesionDep) -> Libro:
    """Crea un libro y devuelve el registro con su id."""
    return servicio.crear_libro(sesion, datos)


@router.get("", response_model=list[LibroLeer], summary="Listado de libros")
def listar_libros(sesion: SesionDep, pagina: PaginacionDep) -> Sequence[Libro]:
    """Devuelve los libros ordenados por id, con paginación."""
    return servicio.listar_libros(sesion, pagina.skip, pagina.limit)


@router.get(
    "/{libro_id}",
    response_model=LibroLeer,
    summary="Consulta de libro por id",
    responses={**RESPUESTA_404},
)
def obtener_libro(libro_id: int, sesion: SesionDep) -> Libro:
    """Devuelve el libro con ese id."""
    return servicio.obtener_libro(sesion, libro_id)


@router.patch(
    "/{libro_id}",
    response_model=LibroLeer,
    summary="Modificación parcial de libro",
    responses={**RESPUESTA_404, **RESPUESTA_409},
)
def actualizar_libro(
    libro_id: int, cambios: LibroActualizar, sesion: SesionDep
) -> Libro:
    """Modifica solo los campos enviados y devuelve el registro actualizado."""
    return servicio.actualizar_libro(sesion, libro_id, cambios)


@router.delete(
    "/{libro_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Baja de libro",
    responses={**RESPUESTA_404, **RESPUESTA_409},
)
def eliminar_libro(libro_id: int, sesion: SesionDep) -> None:
    """Elimina el libro con ese id."""
    servicio.eliminar_libro(sesion, libro_id)
