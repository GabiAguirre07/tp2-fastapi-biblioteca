"""Tests de concurrencia: pedidos simultáneos sobre una base en archivo.

Una base en memoria con StaticPool tiene una única conexión compartida, así
que no puede mostrar carreras reales. Acá cada hilo abre su propia conexión
a un archivo temporal de SQLite, como pasaría con varios clientes a la vez.
El resultado es el mismo sin importar en qué orden se ejecuten los hilos.
"""

import threading
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine, select

from models import Libro, Prestamo, PrestamoCrear, Socio
from services import prestamos as servicio
from services.excepciones import ErrorDeNegocio
from tests.ayudas import HOY_INICIAL

HILOS = 12


@pytest.fixture
def base_en_archivo(tmp_path: Path) -> Iterator[Engine]:
    """Base SQLite en un archivo temporal, con una conexión por hilo."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'concurrencia.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()  # en Windows el archivo no se puede borrar con conexiones abiertas


def correr_a_la_vez(tarea: Callable[[int], None]) -> list[str]:
    """Lanza HILOS hilos que arrancan juntos y resume cómo terminó cada uno.

    Cada resultado es «OK», el nombre de la excepción de negocio que lanzó o
    «ERROR ...» si ocurrió algo inesperado (que haría fallar el test).
    """
    largada = threading.Barrier(HILOS)

    def envuelta(numero: int) -> str:
        largada.wait()
        try:
            tarea(numero)
        except ErrorDeNegocio as error:
            return type(error).__name__
        except Exception as error:
            return f"ERROR {type(error).__name__}: {error}"
        return "OK"

    with ThreadPoolExecutor(max_workers=HILOS) as pool:
        return list(pool.map(envuelta, range(HILOS)))


def cargar_socios_y_libro(
    base: Engine, socios: int, stock: int
) -> tuple[list[int], int]:
    """Inserta socios y un libro con ese stock; devuelve sus ids."""
    with Session(base) as sesion:
        libro = Libro(titulo="Libro", isbn="9780306406157", stock=stock, anio=2000)
        lista = [
            Socio(nombre=f"Socio {n}", email=f"s{n}@example.com") for n in range(socios)
        ]
        sesion.add(libro)
        sesion.add_all(lista)
        sesion.commit()
        ids = [s.id for s in lista if s.id is not None]
        assert libro.id is not None
        return ids, libro.id


def test_doce_pedidos_por_el_ultimo_ejemplar_dan_un_solo_prestamo(
    base_en_archivo: Engine,
) -> None:
    ids_socios, libro_id = cargar_socios_y_libro(base_en_archivo, HILOS, stock=1)

    def pedir(numero: int) -> None:
        with Session(base_en_archivo) as sesion:
            datos = PrestamoCrear(socio_id=ids_socios[numero], libro_id=libro_id)
            servicio.crear_prestamo(sesion, datos, HOY_INICIAL)

    resultados = correr_a_la_vez(pedir)

    assert resultados.count("OK") == 1, resultados
    assert resultados.count("ConflictoDeNegocio") == HILOS - 1, resultados
    with Session(base_en_archivo) as sesion:
        libro = sesion.get(Libro, libro_id)
        assert libro is not None and libro.stock == 0
        assert len(sesion.exec(select(Prestamo)).all()) == 1


def test_doce_pedidos_de_un_mismo_socio_no_superan_el_maximo_de_3(
    base_en_archivo: Engine,
) -> None:
    ids_socios, libro_id = cargar_socios_y_libro(base_en_archivo, 1, stock=50)

    def pedir(_: int) -> None:
        with Session(base_en_archivo) as sesion:
            datos = PrestamoCrear(socio_id=ids_socios[0], libro_id=libro_id)
            servicio.crear_prestamo(sesion, datos, HOY_INICIAL)

    resultados = correr_a_la_vez(pedir)

    assert resultados.count("OK") == servicio.MAXIMO_ACTIVOS, resultados
    assert resultados.count("ConflictoDeNegocio") == HILOS - 3, resultados
    with Session(base_en_archivo) as sesion:
        libro = sesion.get(Libro, libro_id)
        assert libro is not None and libro.stock == 47


def test_doce_devoluciones_simultaneas_reponen_el_stock_una_sola_vez(
    base_en_archivo: Engine,
) -> None:
    ids_socios, libro_id = cargar_socios_y_libro(base_en_archivo, 1, stock=5)
    with Session(base_en_archivo) as sesion:
        datos = PrestamoCrear(socio_id=ids_socios[0], libro_id=libro_id)
        prestamo = servicio.crear_prestamo(sesion, datos, HOY_INICIAL)
        prestamo_id = prestamo.id
    assert prestamo_id is not None

    def devolver(_: int) -> None:
        with Session(base_en_archivo) as sesion:
            servicio.devolver_prestamo(sesion, prestamo_id, HOY_INICIAL)

    resultados = correr_a_la_vez(devolver)

    assert resultados.count("OK") == 1, resultados
    assert resultados.count("ConflictoDeNegocio") == HILOS - 1, resultados
    with Session(base_en_archivo) as sesion:
        libro = sesion.get(Libro, libro_id)
        assert libro is not None and libro.stock == 5  # 5 - 1 + 1, no 5 - 1 + 12
