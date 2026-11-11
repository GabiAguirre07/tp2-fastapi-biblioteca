"""Piezas compartidas por los routers: paginación y respuestas de error."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query
from pydantic import BaseModel


class MensajeError(BaseModel):
    """Cuerpo de las respuestas de error (404, 409)."""

    detail: str


# Se pasan en `responses=` para que Swagger documente cada código posible.
RESPUESTA_404 = {404: {"model": MensajeError, "description": "No existe"}}
RESPUESTA_409 = {409: {"model": MensajeError, "description": "Conflicto"}}


@dataclass
class Paginacion:
    """Parámetros de paginación del listado: ?skip=0&limit=100."""

    skip: Annotated[int, Query(ge=0, description="Registros a saltar")] = 0
    limit: Annotated[
        int, Query(ge=1, le=100, description="Máximo de registros a devolver")
    ] = 100


# Alias para declarar la dependencia en los endpoints: pagina: PaginacionDep
PaginacionDep = Annotated[Paginacion, Depends()]
