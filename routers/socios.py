"""Endpoints de socios: alta, consulta, listado, modificación y baja."""

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Query, status

from database import SesionDep
from models import PrestamoLeer, Socio, SocioActualizar, SocioCrear, SocioLeer
from routers.comunes import (
    FechaHoyDep,
    PaginacionDep,
    RESPUESTA_404,
    RESPUESTA_409,
)
from services import prestamos as servicio_prestamos
from services import socios as servicio

router = APIRouter(prefix="/socios", tags=["Socios"])


@router.post(
    "",
    response_model=SocioLeer,
    status_code=status.HTTP_201_CREATED,
    summary="Alta de socio",
    responses={**RESPUESTA_409},
)
def crear_socio(datos: SocioCrear, sesion: SesionDep) -> Socio:
    """Crea un socio y devuelve el registro con su id."""
    return servicio.crear_socio(sesion, datos)


@router.get("", response_model=list[SocioLeer], summary="Listado de socios")
def listar_socios(sesion: SesionDep, pagina: PaginacionDep) -> Sequence[Socio]:
    """Devuelve los socios ordenados por id, con paginación."""
    return servicio.listar_socios(sesion, pagina.skip, pagina.limit)


@router.get(
    "/{socio_id}",
    response_model=SocioLeer,
    summary="Consulta de socio por id",
    responses={**RESPUESTA_404},
)
def obtener_socio(socio_id: int, sesion: SesionDep) -> Socio:
    """Devuelve el socio con ese id."""
    return servicio.obtener_socio(sesion, socio_id)


@router.patch(
    "/{socio_id}",
    response_model=SocioLeer,
    summary="Modificación parcial de socio",
    responses={**RESPUESTA_404, **RESPUESTA_409},
)
def actualizar_socio(
    socio_id: int, cambios: SocioActualizar, sesion: SesionDep
) -> Socio:
    """Modifica solo los campos enviados y devuelve el registro actualizado."""
    return servicio.actualizar_socio(sesion, socio_id, cambios)


@router.delete(
    "/{socio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Baja de socio",
    responses={**RESPUESTA_404, **RESPUESTA_409},
)
def eliminar_socio(socio_id: int, sesion: SesionDep) -> None:
    """Elimina el socio con ese id."""
    servicio.eliminar_socio(sesion, socio_id)


@router.get(
    "/{socio_id}/prestamos",
    response_model=list[PrestamoLeer],
    summary="Préstamos de un socio",
    responses={**RESPUESTA_404},
)
def listar_prestamos_de_socio(
    socio_id: int,
    sesion: SesionDep,
    pagina: PaginacionDep,
    hoy: FechaHoyDep,
    activos: Annotated[
        bool | None,
        Query(
            description=(
                "true: solo préstamos sin devolver; false: solo devueltos; "
                "sin indicar: todos"
            )
        ),
    ] = None,
) -> list[PrestamoLeer]:
    """Devuelve los préstamos del socio ordenados por id, con paginación."""
    prestamos = servicio_prestamos.listar_prestamos_de_socio(
        sesion, socio_id, pagina.skip, pagina.limit, activos
    )
    return [servicio_prestamos.a_lectura(prestamo, hoy) for prestamo in prestamos]
