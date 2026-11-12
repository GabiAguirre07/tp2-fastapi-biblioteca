"""Endpoints de préstamos: registrar, devolver y consultar uno.

Registrar y devolver son solo del bibliotecario. Consultar un préstamo lo
puede hacer el bibliotecario o el socio al que pertenece.
"""

from fastapi import APIRouter, status

from database import SesionDep
from models import PrestamoCrear, PrestamoLeer
from routers.comunes import (
    FechaHoyDep,
    RESPUESTA_401,
    RESPUESTA_403,
    RESPUESTA_404,
    RESPUESTA_409,
)
from routers.seguridad import SOLO_BIBLIOTECARIO, UsuarioDep
from services import prestamos as servicio
from services import seguridad as servicio_seguridad

router = APIRouter(prefix="/prestamos", tags=["Préstamos"])


@router.post(
    "",
    response_model=PrestamoLeer,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un préstamo",
    dependencies=[SOLO_BIBLIOTECARIO],
    responses={**RESPUESTA_401, **RESPUESTA_403, **RESPUESTA_404, **RESPUESTA_409},
)
def crear_prestamo(
    datos: PrestamoCrear, sesion: SesionDep, hoy: FechaHoyDep
) -> PrestamoLeer:
    """Presta un libro a un socio: descuenta 1 del stock y fija el vencimiento."""
    prestamo = servicio.crear_prestamo(sesion, datos, hoy)
    return servicio.a_lectura(prestamo, hoy)


@router.post(
    "/{prestamo_id}/devolucion",
    response_model=PrestamoLeer,
    summary="Registrar la devolución de un préstamo",
    dependencies=[SOLO_BIBLIOTECARIO],
    responses={**RESPUESTA_401, **RESPUESTA_403, **RESPUESTA_404, **RESPUESTA_409},
)
def devolver_prestamo(
    prestamo_id: int, sesion: SesionDep, hoy: FechaHoyDep
) -> PrestamoLeer:
    """Devuelve el libro: repone 1 al stock y calcula la multa por atraso."""
    prestamo = servicio.devolver_prestamo(sesion, prestamo_id, hoy)
    return servicio.a_lectura(prestamo, hoy)


@router.get(
    "/{prestamo_id}",
    response_model=PrestamoLeer,
    summary="Consulta de préstamo por id",
    responses={**RESPUESTA_401, **RESPUESTA_403, **RESPUESTA_404},
)
def obtener_prestamo(
    prestamo_id: int, sesion: SesionDep, hoy: FechaHoyDep, usuario: UsuarioDep
) -> PrestamoLeer:
    """Devuelve el préstamo con ese id, solo a su socio o al bibliotecario."""
    prestamo = servicio.obtener_prestamo(sesion, prestamo_id)
    servicio_seguridad.exigir_propietario(usuario, prestamo.socio_id)
    return servicio.a_lectura(prestamo, hoy)
