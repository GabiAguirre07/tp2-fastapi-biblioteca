"""Endpoints de autores: alta, consulta, listado, modificación y baja."""

from collections.abc import Sequence

from fastapi import APIRouter, status

from database import SesionDep
from models import Autor, AutorActualizar, AutorCrear, AutorLeer
from routers.comunes import PaginacionDep, RESPUESTA_404, RESPUESTA_409
from services import autores as servicio

router = APIRouter(prefix="/autores", tags=["Autores"])


@router.post(
    "",
    response_model=AutorLeer,
    status_code=status.HTTP_201_CREATED,
    summary="Alta de autor",
    responses={**RESPUESTA_409},
)
def crear_autor(datos: AutorCrear, sesion: SesionDep) -> Autor:
    """Crea un autor y devuelve el registro con su id."""
    return servicio.crear_autor(sesion, datos)


@router.get("", response_model=list[AutorLeer], summary="Listado de autores")
def listar_autores(sesion: SesionDep, pagina: PaginacionDep) -> Sequence[Autor]:
    """Devuelve los autores ordenados por id, con paginación."""
    return servicio.listar_autores(sesion, pagina.skip, pagina.limit)


@router.get(
    "/{autor_id}",
    response_model=AutorLeer,
    summary="Consulta de autor por id",
    responses={**RESPUESTA_404},
)
def obtener_autor(autor_id: int, sesion: SesionDep) -> Autor:
    """Devuelve el autor con ese id."""
    return servicio.obtener_autor(sesion, autor_id)


@router.patch(
    "/{autor_id}",
    response_model=AutorLeer,
    summary="Modificación parcial de autor",
    responses={**RESPUESTA_404, **RESPUESTA_409},
)
def actualizar_autor(
    autor_id: int, cambios: AutorActualizar, sesion: SesionDep
) -> Autor:
    """Modifica solo los campos enviados y devuelve el registro actualizado."""
    return servicio.actualizar_autor(sesion, autor_id, cambios)


@router.delete(
    "/{autor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Baja de autor",
    responses={**RESPUESTA_404, **RESPUESTA_409},
)
def eliminar_autor(autor_id: int, sesion: SesionDep) -> None:
    """Elimina el autor con ese id."""
    servicio.eliminar_autor(sesion, autor_id)
