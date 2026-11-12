"""Tests del modelo de datos: columnas, restricciones y relaciones.

Se prueban directamente contra la base, sin pasar por la API, porque las
restricciones de la base son la última defensa cuando falla una validación.
"""

from datetime import date

import pytest
from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from models import Autor, Libro, LibroAutor, Prestamo, Socio

# Columnas que pide la consigna para cada entidad. El orden no se compara: en las
# tablas que heredan de una clase base, SQLModel deja el id al final.
COLUMNAS_ESPERADAS = {
    "autor": ["id", "nombre", "nacionalidad"],
    "libro": ["id", "titulo", "isbn", "stock", "anio"],
    "libroautor": ["libro_id", "autor_id"],
    "socio": ["id", "nombre", "email", "activo"],
    "prestamo": [
        "id",
        "socio_id",
        "libro_id",
        "fecha_prestamo",
        "fecha_vencimiento",
        "fecha_devolucion",
        "multa",
    ],
}


def un_libro(**cambios: object) -> Libro:
    """Libro válido para insertar directo en la base."""
    datos: dict[str, object] = {
        "titulo": "Libro",
        "isbn": "9780306406157",
        "stock": 1,
        "anio": 2000,
    }
    return Libro.model_validate({**datos, **cambios})


def un_socio(**cambios: object) -> Socio:
    """Socio válido para insertar directo en la base."""
    datos: dict[str, object] = {"nombre": "Ana", "email": "ana@example.com"}
    return Socio.model_validate({**datos, **cambios})


# ---------------------------------------------------------------- estructura


def test_las_tablas_tienen_las_columnas_de_la_consigna(
    tablas: None, motor: Engine
) -> None:
    inspector = inspect(motor)

    for tabla, columnas in COLUMNAS_ESPERADAS.items():
        nombres = [c["name"] for c in inspector.get_columns(tabla)]
        assert sorted(nombres) == sorted(columnas), tabla


def test_solo_la_fecha_de_devolucion_admite_nulo_en_prestamo(
    tablas: None, motor: Engine
) -> None:
    columnas = {c["name"]: c for c in inspect(motor).get_columns("prestamo")}

    admiten_nulo = {nombre for nombre, c in columnas.items() if c["nullable"]}

    assert "fecha_devolucion" in admiten_nulo
    assert not {"socio_id", "libro_id", "fecha_prestamo", "fecha_vencimiento"} & (
        admiten_nulo
    )


# ------------------------------------------------------------- restricciones


def test_las_claves_foraneas_estan_activadas(tablas: None, motor: Engine) -> None:
    huerfano = Prestamo(
        socio_id=999,
        libro_id=999,
        fecha_prestamo=date(2026, 3, 10),
        fecha_vencimiento=date(2026, 3, 24),
    )

    with Session(motor) as sesion:
        sesion.add(huerfano)
        with pytest.raises(IntegrityError):
            sesion.commit()


def test_la_base_rechaza_un_stock_negativo(tablas: None, motor: Engine) -> None:
    with Session(motor) as sesion:
        sesion.add(un_libro())
        sesion.commit()
        sesion.add(Libro(titulo="Malo", isbn="9780131103627", stock=-1, anio=2000))
        with pytest.raises(IntegrityError):
            sesion.commit()


def test_la_base_rechaza_un_anio_anterior_a_1450(tablas: None, motor: Engine) -> None:
    with Session(motor) as sesion:
        sesion.add(Libro(titulo="Malo", isbn="9780131103627", stock=1, anio=1449))
        with pytest.raises(IntegrityError):
            sesion.commit()


def test_la_base_rechaza_un_isbn_repetido(tablas: None, motor: Engine) -> None:
    with Session(motor) as sesion:
        sesion.add(un_libro())
        sesion.commit()
        sesion.add(un_libro(titulo="Otro libro, mismo ISBN"))
        with pytest.raises(IntegrityError):
            sesion.commit()


def test_la_base_rechaza_un_email_repetido(tablas: None, motor: Engine) -> None:
    with Session(motor) as sesion:
        sesion.add(un_socio())
        sesion.commit()
        sesion.add(un_socio(nombre="Otra Ana"))
        with pytest.raises(IntegrityError):
            sesion.commit()


def test_la_base_rechaza_asociar_dos_veces_el_mismo_autor_al_mismo_libro(
    tablas: None, motor: Engine
) -> None:
    with Session(motor) as sesion:
        libro = un_libro()
        autor = Autor(nombre="Ana", nacionalidad="Chile")
        sesion.add(libro)
        sesion.add(autor)
        sesion.commit()
        sesion.add(LibroAutor(libro_id=libro.id, autor_id=autor.id))
        sesion.commit()
        sesion.add(LibroAutor(libro_id=libro.id, autor_id=autor.id))
        with pytest.raises(IntegrityError):
            sesion.commit()


# ---------------------------------------------------------------- relaciones


def test_la_relacion_libro_autor_se_navega_en_los_dos_sentidos(
    tablas: None, motor: Engine
) -> None:
    with Session(motor) as sesion:
        libro = un_libro()
        autor = Autor(nombre="Ana", nacionalidad="Chile")
        libro.autores.append(autor)
        sesion.add(libro)
        sesion.commit()

        assert [a.nombre for a in libro.autores] == ["Ana"]
        assert [x.titulo for x in autor.libros] == ["Libro"]


def test_un_prestamo_conoce_a_su_socio_y_a_su_libro_y_viceversa(
    tablas: None, motor: Engine
) -> None:
    with Session(motor) as sesion:
        socio, libro = un_socio(), un_libro()
        sesion.add(socio)
        sesion.add(libro)
        sesion.commit()
        assert socio.id is not None and libro.id is not None
        prestamo = Prestamo(
            socio_id=socio.id,
            libro_id=libro.id,
            fecha_prestamo=date(2026, 3, 10),
            fecha_vencimiento=date(2026, 3, 24),
        )
        sesion.add(prestamo)
        sesion.commit()

        assert prestamo.socio.email == "ana@example.com"
        assert prestamo.libro.titulo == "Libro"
        assert socio.prestamos == [prestamo]
        assert libro.prestamos == [prestamo]
        assert prestamo.fecha_devolucion is None
        assert prestamo.multa == 0


def test_un_socio_nuevo_queda_activo_por_defecto(tablas: None, motor: Engine) -> None:
    with Session(motor) as sesion:
        socio = un_socio()
        sesion.add(socio)
        sesion.commit()

        assert socio.activo is True
