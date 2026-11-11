"""Tipos de campo y clase base reutilizables por los modelos.

Concentra las reglas de validación de texto, ISBN y email para que cada
entidad las declare en una línea y no se repitan (principio DRY).
"""

import re
from typing import Annotated

from pydantic import (
    AfterValidator,
    BeforeValidator,
    EmailStr,
    StringConstraints,
    model_validator,
)
from sqlmodel import SQLModel

# Largos de los textos. Se validan en los esquemas de entrada (error 422).
NombreTexto = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)
]
TituloTexto = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
NacionalidadTexto = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=2, max_length=60)
]

# ISBN-10 (el último carácter puede ser X) o ISBN-13. Se usa [0-9] y no \d
# porque \d también acepta dígitos de otros alfabetos.
_PATRON_ISBN = re.compile(r"[0-9]{9}[0-9X]|[0-9]{13}")


def _normalizar_isbn(valor: object) -> object:
    """Quita guiones y espacios y pasa a mayúsculas antes de validar."""
    if isinstance(valor, str):
        return re.sub(r"[\s-]", "", valor).upper()
    return valor


def _validar_isbn(valor: str) -> str:
    """Comprueba que el ISBN normalizado tenga 10 o 13 caracteres válidos."""
    if not _PATRON_ISBN.fullmatch(valor):
        raise ValueError(
            "El ISBN debe tener 10 dígitos (el último puede ser X) o 13 dígitos"
        )
    return valor


def _recortar(valor: object) -> object:
    """Quita los espacios al inicio y al final de un texto."""
    if isinstance(valor, str):
        return valor.strip()
    return valor


def _a_minusculas(valor: str) -> str:
    """Pasa el email a minúsculas para que la unicidad no dependa de ellas."""
    return valor.lower()


IsbnTexto = Annotated[
    str, BeforeValidator(_normalizar_isbn), AfterValidator(_validar_isbn)
]
EmailNormalizado = Annotated[
    EmailStr, BeforeValidator(_recortar), AfterValidator(_a_minusculas)
]


class ActualizacionParcial(SQLModel):
    """Base de los esquemas de modificación parcial (PATCH).

    Todos los campos son opcionales: solo se modifican los que el cliente
    envía. Pero enviar un campo explícitamente en null se rechaza, porque
    ningún campo de las tablas admite nulos.
    """

    @model_validator(mode="after")
    def _rechazar_nulos(self) -> "ActualizacionParcial":
        """Rechaza los campos enviados con valor null."""
        for campo in self.model_fields_set:
            if getattr(self, campo) is None:
                raise ValueError(f"El campo '{campo}' no puede ser null")
        return self
