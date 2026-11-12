"""Ayudas para escribir los tests: un reloj controlable y atajos de la API."""

from datetime import date, timedelta
from itertools import count
from typing import Any

from fastapi.testclient import TestClient
from httpx2 import Response

# Fecha de «hoy» con la que arranca cada test (el reloj puede avanzarla).
HOY_INICIAL = date(2026, 3, 10)


class Reloj:
    """Fecha de «hoy» que el test controla.

    Se instala como reemplazo de la dependencia obtener_fecha_hoy, de modo
    que la API «vive» en la fecha del reloj. Un test puede prestar un libro
    y después avanzar los días necesarios para probar vencimientos y multas.
    """

    def __init__(self, hoy: date = HOY_INICIAL) -> None:
        self.hoy = hoy

    def avanzar(self, dias: int) -> None:
        """Pasa el tiempo: suma (o resta, si es negativo) esa cantidad de días."""
        self.hoy += timedelta(days=dias)

    def __call__(self) -> date:
        """Entrega la fecha actual; así FastAPI puede usar el reloj como dependencia."""
        return self.hoy


class Api:
    """Atajos para crear datos de prueba a través de la API real.

    Cada método genera valores únicos (nombres, ISBN, emails) para que los
    tests no se pisen entre sí, y comprueba que la creación haya salido bien
    para que un error de preparación no se confunda con un fallo del test.
    """

    def __init__(self, cliente: TestClient) -> None:
        self.cliente = cliente
        self._numeros = count(1)

    def autor(
        self, nombre: str | None = None, nacionalidad: str = "Argentina"
    ) -> dict[str, Any]:
        """Da de alta un autor y devuelve su JSON."""
        numero = next(self._numeros)
        respuesta = self.cliente.post(
            "/autores",
            json={"nombre": nombre or f"Autor {numero}", "nacionalidad": nacionalidad},
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    def libro(
        self, stock: int = 1, titulo: str | None = None, anio: int = 2000
    ) -> dict[str, Any]:
        """Da de alta un libro con ISBN propio y devuelve su JSON."""
        numero = next(self._numeros)
        respuesta = self.cliente.post(
            "/libros",
            json={
                "titulo": titulo or f"Libro {numero}",
                "isbn": f"978{numero:010d}",
                "stock": stock,
                "anio": anio,
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    def socio(self, activo: bool = True, nombre: str | None = None) -> dict[str, Any]:
        """Da de alta un socio con email propio y devuelve su JSON."""
        numero = next(self._numeros)
        respuesta = self.cliente.post(
            "/socios",
            json={
                "nombre": nombre or f"Socio {numero}",
                "email": f"socio{numero}@example.com",
                "activo": activo,
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    def prestar(self, socio_id: int, libro_id: int) -> Response:
        """Pide un préstamo y devuelve la respuesta tal cual (sea éxito o error)."""
        return self.cliente.post(
            "/prestamos", json={"socio_id": socio_id, "libro_id": libro_id}
        )

    def prestar_ok(self, socio_id: int, libro_id: int) -> dict[str, Any]:
        """Pide un préstamo que tiene que salir bien y devuelve su JSON."""
        respuesta = self.prestar(socio_id, libro_id)
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    def devolver(self, prestamo_id: int) -> Response:
        """Registra una devolución y devuelve la respuesta tal cual."""
        return self.cliente.post(f"/prestamos/{prestamo_id}/devolucion")

    def stock(self, libro_id: int) -> int:
        """Consulta el stock actual de un libro."""
        respuesta = self.cliente.get(f"/libros/{libro_id}")
        assert respuesta.status_code == 200, respuesta.text
        return respuesta.json()["stock"]
