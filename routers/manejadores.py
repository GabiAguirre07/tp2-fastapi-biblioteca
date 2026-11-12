"""Traducción de los errores de negocio a respuestas HTTP."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from services.excepciones import (
    ConflictoDeNegocio,
    ErrorDeNegocio,
    NoAutenticado,
    OperacionNoPermitida,
    RecursoNoEncontrado,
)

# Código HTTP de cada error de negocio. Para sumar un error nuevo alcanza
# con agregar una línea acá.
CODIGOS_HTTP: dict[type[ErrorDeNegocio], int] = {
    RecursoNoEncontrado: status.HTTP_404_NOT_FOUND,
    ConflictoDeNegocio: status.HTTP_409_CONFLICT,
    OperacionNoPermitida: status.HTTP_403_FORBIDDEN,
    NoAutenticado: status.HTTP_401_UNAUTHORIZED,
}


async def _responder_error(_: Request, error: Exception) -> JSONResponse:
    """Convierte un error de negocio en una respuesta JSON con su código."""
    if not isinstance(error, ErrorDeNegocio):
        raise error
    codigo = CODIGOS_HTTP[type(error)]
    return JSONResponse(status_code=codigo, content={"detail": error.mensaje})


def registrar_manejadores(app: FastAPI) -> None:
    """Registra en la aplicación el manejador de cada error de negocio."""
    for clase in CODIGOS_HTTP:
        app.add_exception_handler(clase, _responder_error)
