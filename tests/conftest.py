"""Fixtures compartidas por todos los tests.

Cada test arranca con una base SQLite en memoria nueva y vacía, así que
ninguno depende del resultado de otro ni toca el archivo biblioteca.db.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

import database
from database import obtener_sesion
from main import app
from routers.comunes import obtener_fecha_hoy
from tests.ayudas import Api, Reloj


@pytest.fixture(autouse=True)
def motor(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    """Base en memoria, vacía y nueva para cada test.

    Es autouse: se aplica a todos los tests sin pedirla. Reemplaza el engine
    de database.py por el de memoria, de modo que nada de lo que ejecute el
    test (ni siquiera el lifespan de la app) pueda abrir el archivo real.

    StaticPool hace que todas las conexiones sean una sola: una base SQLite
    en memoria existe solo dentro de su conexión, y sin esto cada hilo de
    FastAPI vería una base distinta y vacía. check_same_thread=False permite
    usar esa conexión desde hilos distintos al que la creó.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    monkeypatch.setattr(database, "engine", engine)
    yield engine
    engine.dispose()


@pytest.fixture
def tablas(motor: Engine) -> None:
    """Crea las tablas en la base en memoria con la misma función de la app."""
    database.crear_tablas()


@pytest.fixture
def reloj() -> Reloj:
    """Reloj controlable que reemplaza a la fecha del servidor."""
    return Reloj()


@pytest.fixture
def cliente(tablas: None, motor: Engine, reloj: Reloj) -> Iterator[TestClient]:
    """Cliente HTTP de la API con base en memoria y fecha controlada.

    Se reemplazan dos dependencias de la app con dependency_overrides: la
    sesión de base de datos y la fecha de hoy. Al terminar se limpian para
    que no afecten al test siguiente.
    """

    def sesion_de_prueba() -> Iterator[Session]:
        with Session(motor) as sesion:
            yield sesion

    app.dependency_overrides[obtener_sesion] = sesion_de_prueba
    app.dependency_overrides[obtener_fecha_hoy] = reloj
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def api(cliente: TestClient) -> Api:
    """Atajos para crear autores, libros, socios y préstamos."""
    return Api(cliente)
