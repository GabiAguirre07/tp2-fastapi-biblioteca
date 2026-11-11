"""Reglas de negocio de los socios."""

from collections.abc import Sequence

from sqlmodel import Session, col, select

from models import Socio, SocioActualizar, SocioCrear
from services.comunes import eliminar, guardar, obtener_o_404
from services.excepciones import ConflictoDeNegocio


def _mensaje_email_duplicado(email: str) -> str:
    """Arma el mensaje de conflicto por email repetido."""
    return f"Ya existe un socio con el email {email}"


def crear_socio(sesion: Session, datos: SocioCrear) -> Socio:
    """Da de alta un socio; el email no puede repetirse (409)."""
    socio = Socio.model_validate(datos)
    guardar(sesion, socio, _mensaje_email_duplicado(datos.email))
    return socio


def listar_socios(sesion: Session, skip: int, limit: int) -> Sequence[Socio]:
    """Devuelve una página de socios ordenados por id."""
    consulta = select(Socio).order_by(col(Socio.id)).offset(skip).limit(limit)
    return sesion.exec(consulta).all()


def obtener_socio(sesion: Session, socio_id: int) -> Socio:
    """Devuelve un socio o lanza RecursoNoEncontrado."""
    return obtener_o_404(sesion, Socio, socio_id)


def actualizar_socio(sesion: Session, socio_id: int, cambios: SocioActualizar) -> Socio:
    """Modifica solo los campos enviados; el email sigue siendo único (409)."""
    socio = obtener_o_404(sesion, Socio, socio_id)
    email = cambios.email if cambios.email is not None else socio.email
    socio.sqlmodel_update(cambios.model_dump(exclude_unset=True))
    guardar(sesion, socio, _mensaje_email_duplicado(email))
    return socio


def eliminar_socio(sesion: Session, socio_id: int) -> None:
    """Borra un socio, salvo que tenga préstamos (409)."""
    socio = obtener_o_404(sesion, Socio, socio_id)
    if socio.prestamos:
        raise ConflictoDeNegocio(
            f"No se puede eliminar el socio {socio_id}: tiene préstamos "
            "registrados. Para impedir que pida más, desactívelo (activo=false)"
        )
    eliminar(sesion, socio)
