"""Reglas de negocio de los préstamos: prestar, devolver y consultar."""

from collections.abc import Sequence
from datetime import date, timedelta

from sqlmodel import Session, col, func, select, update

from models import Libro, Prestamo, PrestamoCrear, PrestamoLeer, Socio
from services.comunes import obtener_o_404, transaccion
from services.excepciones import ConflictoDeNegocio, OperacionNoPermitida

# Reglas fijadas por la consigna.
PLAZO_DIAS = 14
MULTA_POR_DIA = 100
MAXIMO_ACTIVOS = 3


def dias_de_atraso(fecha_vencimiento: date, fecha_referencia: date) -> int:
    """Cuenta los días transcurridos después del vencimiento (0 si no hubo).

    Devolver el mismo día del vencimiento, o antes, no tiene atraso.
    """
    return max(0, (fecha_referencia - fecha_vencimiento).days)


def calcular_multa(fecha_vencimiento: date, fecha_devolucion: date) -> int:
    """Calcula la multa: MULTA_POR_DIA por cada día de atraso (0 si no hubo)."""
    return MULTA_POR_DIA * dias_de_atraso(fecha_vencimiento, fecha_devolucion)


def a_lectura(prestamo: Prestamo, hoy: date) -> PrestamoLeer:
    """Arma la respuesta de un préstamo con sus datos calculados.

    Si el préstamo sigue activo, el atraso se mide hasta hoy; si ya se
    devolvió, hasta la fecha de devolución. Solo un préstamo activo y
    pasado de fecha figura como vencido.
    """
    if prestamo.fecha_devolucion is None:
        atraso = dias_de_atraso(prestamo.fecha_vencimiento, hoy)
        vencido = atraso > 0
    else:
        atraso = dias_de_atraso(prestamo.fecha_vencimiento, prestamo.fecha_devolucion)
        vencido = False
    return PrestamoLeer.model_validate(
        prestamo, update={"vencido": vencido, "dias_atraso": atraso}
    )


def _contar_activos(sesion: Session, socio_id: int) -> int:
    """Cuenta los préstamos sin devolver de un socio."""
    consulta = (
        select(func.count())
        .select_from(Prestamo)
        .where(
            col(Prestamo.socio_id) == socio_id,
            col(Prestamo.fecha_devolucion).is_(None),
        )
    )
    return sesion.exec(consulta).one()


def crear_prestamo(sesion: Session, datos: PrestamoCrear, hoy: date) -> Prestamo:
    """Registra un préstamo aplicando las reglas de negocio.

    Se verifica en este orden: el socio existe (404), el libro existe
    (404), el socio está activo (403), el socio tiene menos de
    MAXIMO_ACTIVOS préstamos sin devolver (409) y el libro tiene stock
    (409). Al prestar se descuenta 1 del stock y el vencimiento es
    PLAZO_DIAS días después de hoy.

    El descuento de stock y el recuento de préstamos activos ocurren en
    la misma transacción que el alta, y el descuento es un solo UPDATE
    condicional: así, dos pedidos simultáneos no pueden llevarse el
    último ejemplar ni superar el máximo de préstamos del socio.
    """
    socio = obtener_o_404(sesion, Socio, datos.socio_id)
    obtener_o_404(sesion, Libro, datos.libro_id)
    if not socio.activo:
        raise OperacionNoPermitida(
            f"El socio {datos.socio_id} está inactivo y no puede pedir préstamos"
        )
    with transaccion(sesion):
        descuento = sesion.exec(
            update(Libro)
            .where(col(Libro.id) == datos.libro_id, col(Libro.stock) > 0)
            .values(stock=col(Libro.stock) - 1)
        )
        if _contar_activos(sesion, datos.socio_id) >= MAXIMO_ACTIVOS:
            raise ConflictoDeNegocio(
                f"El socio {datos.socio_id} ya tiene {MAXIMO_ACTIVOS} préstamos activos"
            )
        if descuento.rowcount == 0:
            raise ConflictoDeNegocio(
                f"El libro {datos.libro_id} no tiene ejemplares disponibles"
            )
        prestamo = Prestamo(
            socio_id=datos.socio_id,
            libro_id=datos.libro_id,
            fecha_prestamo=hoy,
            fecha_vencimiento=hoy + timedelta(days=PLAZO_DIAS),
        )
        sesion.add(prestamo)
    sesion.refresh(prestamo)
    return prestamo


def devolver_prestamo(sesion: Session, prestamo_id: int, hoy: date) -> Prestamo:
    """Registra la devolución: repone el stock y calcula la multa.

    Lanza RecursoNoEncontrado si el préstamo no existe (404) y
    ConflictoDeNegocio si ya estaba devuelto (409). Marcar la devolución
    es un UPDATE condicional (solo si sigue sin devolver), de modo que
    dos devoluciones simultáneas no pueden reponer el stock dos veces.
    """
    prestamo = obtener_o_404(sesion, Prestamo, prestamo_id)
    libro_id = prestamo.libro_id
    multa = calcular_multa(prestamo.fecha_vencimiento, hoy)
    with transaccion(sesion):
        marcado = sesion.exec(
            update(Prestamo)
            .where(
                col(Prestamo.id) == prestamo_id,
                col(Prestamo.fecha_devolucion).is_(None),
            )
            .values(fecha_devolucion=hoy, multa=multa)
        )
        if marcado.rowcount == 0:
            raise ConflictoDeNegocio(f"El préstamo {prestamo_id} ya fue devuelto")
        sesion.exec(
            update(Libro)
            .where(col(Libro.id) == libro_id)
            .values(stock=col(Libro.stock) + 1)
        )
    sesion.refresh(prestamo)
    return prestamo


def obtener_prestamo(sesion: Session, prestamo_id: int) -> Prestamo:
    """Devuelve un préstamo o lanza RecursoNoEncontrado."""
    return obtener_o_404(sesion, Prestamo, prestamo_id)


def listar_prestamos_de_socio(
    sesion: Session,
    socio_id: int,
    skip: int,
    limit: int,
    activos: bool | None = None,
) -> Sequence[Prestamo]:
    """Devuelve una página de los préstamos de un socio, ordenados por id.

    Con activos=True lista solo los que siguen sin devolver; con
    activos=False, solo los ya devueltos; con None, todos. El filtro se
    aplica en la consulta antes de saltar y limitar. Lanza
    RecursoNoEncontrado si el socio no existe (404).
    """
    obtener_o_404(sesion, Socio, socio_id)
    consulta = select(Prestamo).where(col(Prestamo.socio_id) == socio_id)
    if activos is True:
        consulta = consulta.where(col(Prestamo.fecha_devolucion).is_(None))
    elif activos is False:
        consulta = consulta.where(col(Prestamo.fecha_devolucion).is_not(None))
    consulta = consulta.order_by(col(Prestamo.id)).offset(skip).limit(limit)
    return sesion.exec(consulta).all()
