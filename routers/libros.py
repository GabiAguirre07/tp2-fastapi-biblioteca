"""Endpoints de libros: alta, consulta, listado, modificación y baja.

La consulta y el listado son públicos; el alta, la modificación, la baja y
la asociación con autores son solo del bibliotecario.
"""

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Query, status

from database import SesionDep
from models import Libro, LibroActualizar, LibroCrear, LibroLeer
from routers.comunes import (
    PaginacionDep,
    RESPUESTA_401,
    RESPUESTA_403,
    RESPUESTA_404,
    RESPUESTA_409,
)
from routers.seguridad import SOLO_BIBLIOTECARIO
from services import libros as servicio

router = APIRouter(prefix="/libros", tags=["Libros"])


@router.post(
    "",
    response_model=LibroLeer,
    status_code=status.HTTP_201_CREATED,
    summary="Alta de libro",
    dependencies=[SOLO_BIBLIOTECARIO],
    responses={**RESPUESTA_401, **RESPUESTA_403, **RESPUESTA_409},
)
def crear_libro(datos: LibroCrear, sesion: SesionDep) -> Libro:
    """Crea un libro y devuelve el registro con su id."""
    return servicio.crear_libro(sesion, datos)


@router.get("", response_model=list[LibroLeer], summary="Listado de libros")
def listar_libros(
    sesion: SesionDep,
    pagina: PaginacionDep,
    disponibles: Annotated[
        bool | None,
        Query(
            description=(
                "true: solo libros con stock; false: solo agotados (stock 0); "
                "sin indicar: todos"
            )
        ),
    ] = None,
) -> Sequence[Libro]:
    """Devuelve los libros ordenados por id, con filtro y paginación."""
    return servicio.listar_libros(sesion, pagina.skip, pagina.limit, disponibles)


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
    dependencies=[SOLO_BIBLIOTECARIO],
    responses={**RESPUESTA_401, **RESPUESTA_403, **RESPUESTA_404, **RESPUESTA_409},
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
    dependencies=[SOLO_BIBLIOTECARIO],
    responses={**RESPUESTA_401, **RESPUESTA_403, **RESPUESTA_404, **RESPUESTA_409},
)
def eliminar_libro(libro_id: int, sesion: SesionDep) -> None:
    """Elimina el libro con ese id."""
    servicio.eliminar_libro(sesion, libro_id)


@router.post(
    "/{libro_id}/autores/{autor_id}",
    response_model=LibroLeer,
    status_code=status.HTTP_201_CREATED,
    summary="Asociar un autor a un libro",
    dependencies=[SOLO_BIBLIOTECARIO],
    responses={**RESPUESTA_401, **RESPUESTA_403, **RESPUESTA_404, **RESPUESTA_409},
)
def asociar_autor(libro_id: int, autor_id: int, sesion: SesionDep) -> Libro:
    """Asocia el autor al libro y devuelve el libro con todos sus autores."""
    return servicio.asociar_autor(sesion, libro_id, autor_id)


@router.delete(
    "/{libro_id}/autores/{autor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desasociar un autor de un libro",
    dependencies=[SOLO_BIBLIOTECARIO],
    responses={**RESPUESTA_401, **RESPUESTA_403, **RESPUESTA_404},
)
def desasociar_autor(libro_id: int, autor_id: int, sesion: SesionDep) -> None:
    """Quita la asociación entre el libro y el autor."""
    servicio.desasociar_autor(sesion, libro_id, autor_id)
