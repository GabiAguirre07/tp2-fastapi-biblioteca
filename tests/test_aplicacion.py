"""Tests de la aplicación completa: arranque (lifespan) y contrato de rutas."""

from contextlib import contextmanager
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from database import RUTA_BASE_DE_DATOS, obtener_sesion
from main import app
from routers.comunes import obtener_fecha_hoy
from tests.ayudas import Api

TABLAS_ESPERADAS = {"autor", "libro", "libroautor", "socio", "prestamo"}

# Endpoints mínimos de la consigna (más los que se sumaron por decisión propia).
RUTAS_DE_LA_CONSIGNA = {
    ("POST", "/autores"),
    ("GET", "/autores"),
    ("GET", "/autores/{autor_id}"),
    ("PATCH", "/autores/{autor_id}"),
    ("DELETE", "/autores/{autor_id}"),
    ("POST", "/libros"),
    ("GET", "/libros"),
    ("GET", "/libros/{libro_id}"),
    ("PATCH", "/libros/{libro_id}"),
    ("DELETE", "/libros/{libro_id}"),
    ("POST", "/socios"),
    ("GET", "/socios"),
    ("GET", "/socios/{socio_id}"),
    ("PATCH", "/socios/{socio_id}"),
    ("DELETE", "/socios/{socio_id}"),
    ("POST", "/libros/{libro_id}/autores/{autor_id}"),
    ("POST", "/prestamos"),
    ("POST", "/prestamos/{prestamo_id}/devolucion"),
    ("GET", "/socios/{socio_id}/prestamos"),
}
RUTAS_EXTRA = {
    ("DELETE", "/libros/{libro_id}/autores/{autor_id}"),
    ("GET", "/autores/{autor_id}/libros"),
    ("GET", "/prestamos/{prestamo_id}"),
}


def test_al_arrancar_la_app_crea_las_cinco_tablas_en_la_base_de_los_tests(
    motor: Engine,
) -> None:
    existia = RUTA_BASE_DE_DATOS.exists()
    modificada_antes = RUTA_BASE_DE_DATOS.stat().st_mtime_ns if existia else None
    assert inspect(motor).get_table_names() == []

    with TestClient(app):  # entrar al «with» ejecuta el lifespan de la app
        assert set(inspect(motor).get_table_names()) == TABLAS_ESPERADAS

    # Los tests nunca tocan el archivo real biblioteca.db.
    assert RUTA_BASE_DE_DATOS.exists() == existia
    if existia:
        assert RUTA_BASE_DE_DATOS.stat().st_mtime_ns == modificada_antes


def test_la_api_expone_todos_los_endpoints_de_la_consigna(api: Api) -> None:
    rutas = api.cliente.get("/openapi.json").json()["paths"]

    publicadas = {
        (metodo.upper(), ruta) for ruta, metodos in rutas.items() for metodo in metodos
    }

    assert RUTAS_DE_LA_CONSIGNA <= publicadas
    assert RUTAS_EXTRA <= publicadas
    assert publicadas == RUTAS_DE_LA_CONSIGNA | RUTAS_EXTRA


def test_swagger_documenta_los_codigos_de_las_reglas_de_negocio(api: Api) -> None:
    rutas = api.cliente.get("/openapi.json").json()["paths"]

    codigos_prestar = set(rutas["/prestamos"]["post"]["responses"])
    codigos_devolver = set(
        rutas["/prestamos/{prestamo_id}/devolucion"]["post"]["responses"]
    )

    assert {"201", "403", "404", "409", "422"} <= codigos_prestar
    assert {"200", "404", "409"} <= codigos_devolver


def test_swagger_y_la_documentacion_estan_disponibles(api: Api) -> None:
    assert api.cliente.get("/docs").status_code == 200
    assert api.cliente.get("/openapi.json").json()["info"]["title"] == (
        "Sistema de Biblioteca"
    )


def test_la_dependencia_de_sesion_entrega_una_sesion_de_la_base_en_uso(
    motor: Engine,
) -> None:
    with contextmanager(obtener_sesion)() as sesion:
        assert sesion.get_bind() is motor  # los tests nunca usan el engine real


def test_la_dependencia_de_fecha_entrega_el_dia_de_hoy_del_servidor() -> None:
    assert obtener_fecha_hoy() == date.today()
