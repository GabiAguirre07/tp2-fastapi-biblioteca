"""Tests directos de la capa de servicios, sin pasar por HTTP.

Verifican las piezas que la API usa por debajo: los cálculos puros de la
multa y el atraso, la transacción «todo o nada» y los helpers comunes.
"""

from collections.abc import Callable
from datetime import date
from typing import Any

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from models import Autor, Libro, Prestamo, PrestamoCrear, Socio
from services import prestamos as servicio
from services.comunes import ID_MAXIMO, guardar, obtener_o_404, transaccion
from services.excepciones import ConflictoDeNegocio, RecursoNoEncontrado
from tests.ayudas import HOY_INICIAL

# ------------------------------------------------ cálculos puros (sin base)


@pytest.mark.parametrize(
    ("vencimiento", "referencia", "esperado"),
    [
        (date(2026, 3, 24), date(2026, 3, 10), 0),  # devuelto antes
        (date(2026, 3, 24), date(2026, 3, 24), 0),  # justo el día del vencimiento
        (date(2026, 3, 24), date(2026, 3, 25), 1),  # un día tarde
        (date(2026, 3, 24), date(2026, 4, 24), 31),  # cruza de mes
        (date(2026, 12, 25), date(2027, 1, 5), 11),  # cruza de año
        (date(2028, 2, 28), date(2028, 3, 1), 2),  # año bisiesto: existe el 29/02
    ],
)
def test_dias_de_atraso_cuenta_solo_los_dias_posteriores_al_vencimiento(
    vencimiento: date, referencia: date, esperado: int
) -> None:
    assert servicio.dias_de_atraso(vencimiento, referencia) == esperado


@pytest.mark.parametrize(
    ("dias", "multa"), [(0, 0), (1, 100), (7, 700), (30, 3000), (366, 36600)]
)
def test_calcular_multa_es_100_por_dia_de_atraso(dias: int, multa: int) -> None:
    vencimiento = date(2026, 3, 24)
    devolucion = date.fromordinal(vencimiento.toordinal() + dias)

    assert servicio.calcular_multa(vencimiento, devolucion) == multa


def test_las_constantes_de_las_reglas_coinciden_con_la_consigna() -> None:
    assert servicio.PLAZO_DIAS == 14
    assert servicio.MULTA_POR_DIA == 100
    assert servicio.MAXIMO_ACTIVOS == 3


# ------------------------------------------------------------ obtener_o_404


@pytest.mark.parametrize("id_inexistente", [1, 0, -1, ID_MAXIMO, ID_MAXIMO + 1, 10**30])
def test_obtener_o_404_lanza_recurso_no_encontrado(
    tablas: None, motor: Engine, id_inexistente: int
) -> None:
    with Session(motor) as sesion:
        with pytest.raises(RecursoNoEncontrado) as error:
            obtener_o_404(sesion, Socio, id_inexistente)

    assert "Socio" in error.value.mensaje


def test_obtener_o_404_devuelve_el_registro_existente(
    tablas: None, motor: Engine
) -> None:
    with Session(motor) as sesion:
        sesion.add(Autor(nombre="Ana", nacionalidad="Chile"))
        sesion.commit()

        autor = obtener_o_404(sesion, Autor, 1)

        assert autor.nombre == "Ana"


# ------------------------------------------------------------------ guardar


def crear_libro_directo(isbn: str) -> Libro:
    """Arma un libro (sin guardarlo) para probar la restricción de ISBN único."""
    return Libro(titulo="Libro", isbn=isbn, stock=1, anio=2000)


def test_guardar_un_duplicado_con_mensaje_lanza_conflicto(
    tablas: None, motor: Engine
) -> None:
    with Session(motor) as sesion:
        guardar(sesion, crear_libro_directo("9780306406157"))

        with pytest.raises(ConflictoDeNegocio) as error:
            guardar(sesion, crear_libro_directo("9780306406157"), "ISBN repetido")

        assert error.value.mensaje == "ISBN repetido"


def test_guardar_un_duplicado_sin_mensaje_relanza_el_error_de_la_base(
    tablas: None, motor: Engine
) -> None:
    with Session(motor) as sesion:
        guardar(sesion, crear_libro_directo("9780306406157"))

        with pytest.raises(IntegrityError):
            guardar(sesion, crear_libro_directo("9780306406157"))


def test_guardar_deja_la_sesion_usable_despues_de_un_conflicto(
    tablas: None, motor: Engine
) -> None:
    with Session(motor) as sesion:
        guardar(sesion, crear_libro_directo("9780306406157"))
        with pytest.raises(ConflictoDeNegocio):
            guardar(sesion, crear_libro_directo("9780306406157"), "repetido")

        guardar(sesion, crear_libro_directo("9780131103627"))

        assert len(sesion.exec(select(Libro)).all()) == 2


# -------------------------------------------------------------- transaccion


class FallaSimulada(Exception):
    """Error inventado para forzar un fallo en medio de una transacción."""


def test_transaccion_confirma_todos_los_cambios_al_salir_bien(
    tablas: None, motor: Engine
) -> None:
    with Session(motor) as sesion:
        with transaccion(sesion):
            sesion.add(Autor(nombre="Ana", nacionalidad="Chile"))
            sesion.add(Autor(nombre="Beto", nacionalidad="Perú"))

    with Session(motor) as otra_sesion:
        assert len(otra_sesion.exec(select(Autor)).all()) == 2


def test_transaccion_descarta_todo_y_relanza_ante_cualquier_excepcion(
    tablas: None, motor: Engine
) -> None:
    with Session(motor) as sesion:
        with pytest.raises(FallaSimulada):
            with transaccion(sesion):
                sesion.add(Autor(nombre="Ana", nacionalidad="Chile"))
                sesion.flush()  # el cambio llega a la base, pero sin confirmar
                raise FallaSimulada()

        # Se consulta con la MISMA sesión, todavía abierta: sin el rollback de
        # transaccion() el autor seguiría ahí. Cerrar la sesión también
        # descartaría el cambio y ocultaría la falta del rollback.
        assert sesion.exec(select(Autor)).all() == []


def test_si_falla_el_alta_del_prestamo_se_revierte_el_descuento_de_stock(
    tablas: None, motor: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    with Session(motor) as sesion:
        socio = Socio(nombre="Ana", email="ana@example.com")
        libro = crear_libro_directo("9780306406157")
        libro.stock = 3
        sesion.add(socio)
        sesion.add(libro)
        sesion.commit()
        socio_id, libro_id = socio.id, libro.id
    assert socio_id is not None and libro_id is not None

    agregar_original: Callable[..., Any] = Session.add

    def agregar_que_falla_con_prestamos(
        self: Session, instance: object, *args: Any, **kwargs: Any
    ) -> None:
        if isinstance(instance, Prestamo):
            raise FallaSimulada()
        agregar_original(self, instance, *args, **kwargs)

    datos = PrestamoCrear(socio_id=socio_id, libro_id=libro_id)
    with monkeypatch.context() as parche:
        parche.setattr(Session, "add", agregar_que_falla_con_prestamos)
        with Session(motor) as sesion:
            with pytest.raises(FallaSimulada):
                servicio.crear_prestamo(sesion, datos, HOY_INICIAL)

    with Session(motor) as sesion:
        libro_en_base = sesion.get(Libro, libro_id)
        assert libro_en_base is not None
        assert libro_en_base.stock == 3  # el descuento se deshizo
        assert sesion.exec(select(Prestamo)).all() == []
