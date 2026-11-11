"""Configuración de la base de datos: engine, creación de tablas y sesión.

Centraliza el acceso a SQLite para que el resto de la aplicación reciba
la sesión por inyección de dependencias y nunca cree conexiones propias.
"""

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy import event
from sqlalchemy.engine import URL, Engine
from sqlmodel import Session, SQLModel, create_engine

# La base se guarda junto al código, sin importar desde qué carpeta se lance
# la app: así se comporta igual en Windows, Linux y macOS.
RUTA_BASE_DE_DATOS = Path(__file__).resolve().parent / "biblioteca.db"
URL_BASE_DE_DATOS = URL.create("sqlite", database=str(RUTA_BASE_DE_DATOS))

# check_same_thread=False: FastAPI atiende los pedidos en distintos hilos y
# SQLite, por defecto, solo permite usar una conexión en el hilo que la creó.
engine = create_engine(URL_BASE_DE_DATOS, connect_args={"check_same_thread": False})


@event.listens_for(Engine, "connect")
def activar_claves_foraneas(
    dbapi_connection: object, connection_record: object
) -> None:
    """Activa la validación de claves foráneas en cada conexión nueva.

    SQLite no las valida por defecto: sin esto aceptaría, por ejemplo, un
    préstamo que referencia a un socio inexistente. Se registra sobre la
    clase Engine para que también alcance a los engines de los tests.
    """
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def crear_tablas() -> None:
    """Crea las tablas de todos los modelos importados, si no existen."""
    SQLModel.metadata.create_all(engine)


def obtener_sesion() -> Iterator[Session]:
    """Entrega una sesión por petición y la cierra al terminar."""
    with Session(engine) as sesion:
        yield sesion


# Alias para declarar la dependencia en los endpoints: sesion: SesionDep
SesionDep = Annotated[Session, Depends(obtener_sesion)]
