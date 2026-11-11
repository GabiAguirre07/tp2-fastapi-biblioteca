"""Punto de entrada de la API: crea la aplicación y prepara la base de datos."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

# Importar el paquete ejecuta models/__init__.py y registra todas las tablas
# en la metadata; sin esto create_all no sabría qué tablas crear.
import models  # noqa: F401
from database import crear_tablas


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Crea las tablas al iniciar la aplicación."""
    crear_tablas()
    yield


app = FastAPI(title="Sistema de Biblioteca", lifespan=ciclo_de_vida)
