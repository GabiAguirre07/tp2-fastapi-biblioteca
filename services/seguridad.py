"""Identificación de quien pide y reglas de autorización por rol.

Esta capa no conoce HTTP: recibe los valores ya extraídos de la petición y
lanza errores de negocio que el manejador central traduce a 401 o 403.

La identificación es simulada: se confía en lo que el cliente declara
(rol y, para un socio, su id) y solo se comprueba que el socio exista. No hay
contraseñas ni tokens. Si algún día se reemplazara por JWT u otro mecanismo,
solo cambiaría identificar_usuario; las reglas de autorización de abajo, y
todo el resto de la aplicación, quedarían iguales.
"""

from dataclasses import dataclass
from enum import Enum

from sqlmodel import Session

from models import Socio
from services.comunes import ID_MAXIMO
from services.excepciones import NoAutenticado, OperacionNoPermitida

# Cantidad de cifras de ID_MAXIMO: un texto más largo no puede ser un id válido.
_CIFRAS_MAXIMAS = len(str(ID_MAXIMO))


class Rol(str, Enum):
    """Roles del sistema. Es str para compararse y mostrarse como texto."""

    BIBLIOTECARIO = "bibliotecario"
    SOCIO = "socio"


@dataclass(frozen=True)
class Usuario:
    """Quien hace el pedido: su rol y, si es socio, el id de su registro."""

    rol: Rol
    socio_id: int | None = None


def _identificar_socio(sesion: Session, socio_id: str | None) -> int:
    """Valida el id de socio declarado y devuelve su valor numérico.

    Se exige un entero positivo escrito solo con dígitos ASCII (isdigit por
    sí solo aceptaría también dígitos como «²»). Un texto con más cifras que
    ID_MAXIMO se descarta antes de convertirlo a int, porque Python limita la
    conversión de textos numéricos muy largos y fallaría con un error interno.
    """
    texto = (socio_id or "").strip()
    if not texto:
        raise NoAutenticado("El rol socio requiere el encabezado X-Socio-Id")
    if not (texto.isascii() and texto.isdigit()):
        raise NoAutenticado("X-Socio-Id debe ser un número entero positivo")
    numero = int(texto) if len(texto) <= _CIFRAS_MAXIMAS else 0
    if not 1 <= numero <= ID_MAXIMO or sesion.get(Socio, numero) is None:
        raise NoAutenticado(f"El socio {texto} no existe")
    return numero


def identificar_usuario(
    sesion: Session, rol: str | None, socio_id: str | None
) -> Usuario:
    """Arma el Usuario a partir de los encabezados X-Rol y X-Socio-Id.

    El rol no distingue mayúsculas ni espacios en los bordes. Un
    bibliotecario ignora X-Socio-Id; un socio debe indicar el de un socio
    existente (esté activo o no: un socio inactivo no puede pedir préstamos,
    pero sí consultar los suyos). Lanza NoAutenticado (401) si algo falta o
    es inválido.
    """
    texto = (rol or "").strip().lower()
    if not texto:
        raise NoAutenticado("Falta el encabezado X-Rol (bibliotecario o socio)")
    try:
        rol_declarado = Rol(texto)
    except ValueError:
        raise NoAutenticado(
            f"El rol '{rol}' no es válido: usar bibliotecario o socio"
        ) from None
    if rol_declarado is Rol.BIBLIOTECARIO:
        return Usuario(Rol.BIBLIOTECARIO)
    return Usuario(Rol.SOCIO, _identificar_socio(sesion, socio_id))


def exigir_bibliotecario(usuario: Usuario) -> None:
    """Permite continuar solo al bibliotecario; a un socio le lanza 403."""
    if usuario.rol is not Rol.BIBLIOTECARIO:
        raise OperacionNoPermitida("Esta operación es solo para el bibliotecario")


def exigir_propietario(usuario: Usuario, socio_id: int) -> None:
    """Un socio solo puede ver lo suyo; el bibliotecario ve todo.

    Lanza OperacionNoPermitida (403) si un socio pide datos de otro socio.
    """
    if usuario.rol is Rol.SOCIO and usuario.socio_id != socio_id:
        raise OperacionNoPermitida("Un socio solo puede ver sus propios préstamos")
