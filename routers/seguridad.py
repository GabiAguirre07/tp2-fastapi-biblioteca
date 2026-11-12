"""Dependencias de seguridad de los routers: quién pide y qué rol tiene.

Cada endpoint declara lo que exige con una dependencia y los servicios no se
enteran de cómo llegan las credenciales (encabezados HTTP). Los dos
encabezados figuran como esquemas de seguridad: en Swagger aparecen en el
botón «Authorize» y se envían solos en cada llamada.
"""

from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader

from database import SesionDep
from services import seguridad as servicio
from services.seguridad import Usuario

esquema_rol = APIKeyHeader(
    name="X-Rol",
    scheme_name="Rol",
    description="Rol de quien pide: bibliotecario o socio.",
    auto_error=False,
)
esquema_socio_id = APIKeyHeader(
    name="X-Socio-Id",
    scheme_name="SocioId",
    description="Id del socio. Obligatorio solo si el rol es socio.",
    auto_error=False,
)


def obtener_usuario(
    sesion: SesionDep,
    rol: Annotated[str | None, Security(esquema_rol)] = None,
    socio_id: Annotated[str | None, Security(esquema_socio_id)] = None,
) -> Usuario:
    """Identifica a quien hace el pedido a partir de sus encabezados (401)."""
    return servicio.identificar_usuario(sesion, rol, socio_id)


# Alias para declarar la dependencia en los endpoints: usuario: UsuarioDep
UsuarioDep = Annotated[Usuario, Depends(obtener_usuario)]


def exigir_bibliotecario(usuario: UsuarioDep) -> None:
    """Deja pasar solo al bibliotecario (401 sin credenciales, 403 a un socio)."""
    servicio.exigir_bibliotecario(usuario)


def exigir_propietario(socio_id: int, usuario: UsuarioDep) -> None:
    """Un socio solo puede consultar su propio {socio_id} (403 si es otro).

    Toma socio_id de la ruta: FastAPI lo completa con el parámetro del
    endpoint que usa esta dependencia.
    """
    servicio.exigir_propietario(usuario, socio_id)


# Para usar en el decorador: @router.post(..., dependencies=[SOLO_BIBLIOTECARIO])
SOLO_BIBLIOTECARIO = Depends(exigir_bibliotecario)
# Para el listado de préstamos de un socio: el bibliotecario o el propio socio.
EL_PROPIO_SOCIO_O_BIBLIOTECARIO = Depends(exigir_propietario)
