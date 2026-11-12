"""Errores de negocio que lanzan los servicios.

Los servicios no conocen HTTP: lanzan estas excepciones y la capa web
(routers/manejadores.py) las traduce al código de estado correspondiente.
"""


class ErrorDeNegocio(Exception):
    """Base de todos los errores de negocio; guarda un mensaje legible."""

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class RecursoNoEncontrado(ErrorDeNegocio):
    """El recurso pedido no existe (se traduce a 404)."""


class ConflictoDeNegocio(ErrorDeNegocio):
    """La operación choca con el estado de los datos (se traduce a 409)."""


class OperacionNoPermitida(ErrorDeNegocio):
    """Quien pide la operación no está habilitado para hacerla (403)."""
