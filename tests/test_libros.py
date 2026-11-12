"""Tests de los libros: CRUD, validaciones, filtro de disponibles y autores."""

from datetime import date
from typing import Any

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from models import LibroAutor
from tests.ayudas import Api

IDS_IMPOSIBLES = [0, -1, 2**63, 10**30]


def cuerpo_libro(**cambios: object) -> dict[str, object]:
    """Cuerpo válido de alta de libro, con los cambios que pida el test."""
    base: dict[str, object] = {
        "titulo": "Rayuela",
        "isbn": "9780306406157",
        "stock": 3,
        "anio": 1963,
    }
    return {**base, **cambios}


# --------------------------------------------------------------------- alta


def test_crear_libro_devuelve_201_con_id_y_sin_autores(api: Api) -> None:
    respuesta = api.cliente.post("/libros", json=cuerpo_libro())

    assert respuesta.status_code == 201
    assert respuesta.json() == {
        "id": 1,
        "titulo": "Rayuela",
        "isbn": "9780306406157",
        "stock": 3,
        "anio": 1963,
        "autores": [],
    }


@pytest.mark.parametrize(
    ("isbn_enviado", "isbn_guardado"),
    [
        ("978-0-306-40615-7", "9780306406157"),  # guiones
        ("978 0306 40615 7", "9780306406157"),  # espacios
        ("0-8044-2957-X", "080442957X"),  # ISBN-10 con X
        ("080442957x", "080442957X"),  # X en minúscula
    ],
)
def test_crear_libro_normaliza_el_isbn(
    api: Api, isbn_enviado: str, isbn_guardado: str
) -> None:
    respuesta = api.cliente.post("/libros", json=cuerpo_libro(isbn=isbn_enviado))

    assert respuesta.status_code == 201
    assert respuesta.json()["isbn"] == isbn_guardado


def test_crear_libro_recorta_el_titulo(api: Api) -> None:
    respuesta = api.cliente.post("/libros", json=cuerpo_libro(titulo="  Rayuela  "))

    assert respuesta.json()["titulo"] == "Rayuela"


def test_crear_libro_acepta_los_limites_validos(api: Api) -> None:
    anio_actual = date.today().year

    primero = api.cliente.post("/libros", json=cuerpo_libro(anio=1450, stock=0))
    segundo = api.cliente.post(
        "/libros", json=cuerpo_libro(isbn="9780131103627", anio=anio_actual)
    )

    assert primero.status_code == 201
    assert segundo.status_code == 201


@pytest.mark.parametrize(
    "cambios",
    [
        {"titulo": ""},
        {"titulo": "   "},
        {"titulo": "T" * 201},
        {"isbn": "123"},  # muy corto
        {"isbn": "97803064061570"},  # 14 dígitos
        {"isbn": "97803064061X7"},  # X fuera de la última posición
        {"isbn": "ABCDEFGHIJ"},
        {"isbn": 9780306406157},  # número en lugar de texto
        {"stock": -1},
        {"stock": "muchos"},
        {"anio": 1449},
        {"anio": date.today().year + 1},
    ],
)
def test_crear_libro_con_datos_invalidos_da_422(
    api: Api, cambios: dict[str, object]
) -> None:
    respuesta = api.cliente.post("/libros", json=cuerpo_libro(**cambios))

    assert respuesta.status_code == 422


def test_crear_libro_con_campos_faltantes_da_422(api: Api) -> None:
    assert (
        api.cliente.post("/libros", json={"titulo": "Solo título"}).status_code == 422
    )


def test_crear_libro_ignora_los_autores_enviados_en_el_alta(api: Api) -> None:
    autor = api.autor()

    respuesta = api.cliente.post("/libros", json=cuerpo_libro(autores=[autor]))

    assert respuesta.status_code == 201
    assert respuesta.json()["autores"] == []


# ------------------------------------------------------------------ listado


def test_listar_libros_ordenados_por_id_y_paginados(api: Api) -> None:
    ids = [api.libro()["id"] for _ in range(5)]

    todos = api.cliente.get("/libros").json()
    pagina = api.cliente.get("/libros?skip=2&limit=2").json()

    assert [x["id"] for x in todos] == ids
    assert [x["id"] for x in pagina] == ids[2:4]


@pytest.mark.parametrize(
    "consulta", ["limit=0", "limit=101", "skip=-1", f"skip={10**30}"]
)
def test_listar_libros_con_paginacion_invalida_da_422(api: Api, consulta: str) -> None:
    assert api.cliente.get(f"/libros?{consulta}").status_code == 422


def preparar_libros_con_y_sin_stock(api: Api) -> tuple[list[int], list[int]]:
    """Crea 7 libros alternando stock y devuelve los ids con y sin stock."""
    libros = [api.libro(stock=stock) for stock in (5, 0, 3, 0, 1, 0, 2)]
    con_stock = [x["id"] for x in libros if x["stock"] > 0]
    sin_stock = [x["id"] for x in libros if x["stock"] == 0]
    return con_stock, sin_stock


def test_filtro_disponibles_true_lista_solo_los_que_tienen_stock(api: Api) -> None:
    con_stock, _ = preparar_libros_con_y_sin_stock(api)

    respuesta = api.cliente.get("/libros?disponibles=true")

    assert [x["id"] for x in respuesta.json()] == con_stock
    assert all(x["stock"] > 0 for x in respuesta.json())


def test_filtro_disponibles_false_lista_solo_los_agotados(api: Api) -> None:
    _, sin_stock = preparar_libros_con_y_sin_stock(api)

    respuesta = api.cliente.get("/libros?disponibles=false")

    assert [x["id"] for x in respuesta.json()] == sin_stock


def test_sin_filtro_disponibles_se_listan_todos(api: Api) -> None:
    con_stock, sin_stock = preparar_libros_con_y_sin_stock(api)

    respuesta = api.cliente.get("/libros")

    assert len(respuesta.json()) == len(con_stock) + len(sin_stock)


def test_la_paginacion_cuenta_sobre_los_libros_ya_filtrados(api: Api) -> None:
    con_stock, _ = preparar_libros_con_y_sin_stock(api)

    pagina_1 = api.cliente.get("/libros?disponibles=true&limit=2").json()
    pagina_2 = api.cliente.get("/libros?disponibles=true&limit=2&skip=2").json()

    assert [x["id"] for x in pagina_1] == con_stock[0:2]
    assert [x["id"] for x in pagina_2] == con_stock[2:4]


@pytest.mark.parametrize(
    ("valor", "codigo"),
    [("true", 200), ("false", 200), ("1", 200), ("0", 200), ("TRUE", 200)]
    + [("maybe", 422), ("", 422)],
)
def test_filtro_disponibles_valida_su_valor(api: Api, valor: str, codigo: int) -> None:
    assert api.cliente.get(f"/libros?disponibles={valor}").status_code == codigo


def test_un_libro_prestado_hasta_agotarse_sale_de_disponibles(api: Api) -> None:
    libro = api.libro(stock=1)
    api.prestar_ok(api.socio()["id"], libro["id"])

    disponibles = api.cliente.get("/libros?disponibles=true").json()
    agotados = api.cliente.get("/libros?disponibles=false").json()

    assert libro["id"] not in [x["id"] for x in disponibles]
    assert libro["id"] in [x["id"] for x in agotados]


def test_listar_libros_no_hace_una_consulta_por_libro(api: Api, motor: Engine) -> None:
    autor = api.autor()
    for _ in range(8):
        libro = api.libro()
        api.cliente.post(f"/libros/{libro['id']}/autores/{autor['id']}")
    consultas: list[str] = []

    def registrar(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        consultas.append(statement)

    event.listen(motor, "before_cursor_execute", registrar)
    try:
        respuesta = api.cliente.get("/libros")
    finally:
        event.remove(motor, "before_cursor_execute", registrar)

    assert len(respuesta.json()) == 8
    # Una consulta para los libros y otra para los autores de todos ellos.
    assert len(consultas) <= 3, consultas


# ----------------------------------------------------------------- consulta


def test_obtener_libro_existente_devuelve_200(api: Api) -> None:
    libro = api.libro()

    respuesta = api.cliente.get(f"/libros/{libro['id']}")

    assert respuesta.status_code == 200
    assert respuesta.json() == libro


def test_obtener_libro_inexistente_da_404(api: Api) -> None:
    respuesta = api.cliente.get("/libros/9999")

    assert respuesta.status_code == 404
    assert "Libro" in respuesta.json()["detail"]


@pytest.mark.parametrize("id_libro", IDS_IMPOSIBLES)
def test_ids_imposibles_dan_404_y_no_500(api: Api, id_libro: int) -> None:
    assert api.cliente.get(f"/libros/{id_libro}").status_code == 404
    assert (
        api.cliente.patch(f"/libros/{id_libro}", json={"stock": 1}).status_code == 404
    )
    assert api.cliente.delete(f"/libros/{id_libro}").status_code == 404
    assert api.cliente.post(f"/libros/{id_libro}/autores/1").status_code == 404
    assert api.cliente.delete(f"/libros/{id_libro}/autores/1").status_code == 404


# ------------------------------------------------------------- modificación


def test_modificar_libro_cambia_solo_los_campos_enviados(api: Api) -> None:
    libro = api.libro(stock=2, titulo="Viejo")

    respuesta = api.cliente.patch(f"/libros/{libro['id']}", json={"titulo": "Nuevo"})

    assert respuesta.status_code == 200
    assert respuesta.json() == {**libro, "titulo": "Nuevo"}


def test_modificar_el_stock_de_un_libro_es_posible(api: Api) -> None:
    libro = api.libro(stock=0)

    respuesta = api.cliente.patch(f"/libros/{libro['id']}", json={"stock": 7})

    assert respuesta.json()["stock"] == 7


def test_modificar_libro_mantiene_sus_autores(api: Api) -> None:
    libro, autor = api.libro(), api.autor()
    api.cliente.post(f"/libros/{libro['id']}/autores/{autor['id']}")

    respuesta = api.cliente.patch(f"/libros/{libro['id']}", json={"titulo": "Otro"})

    assert [a["id"] for a in respuesta.json()["autores"]] == [autor["id"]]


def test_modificar_libro_con_su_propio_isbn_no_es_conflicto(api: Api) -> None:
    libro = api.libro()

    respuesta = api.cliente.patch(
        f"/libros/{libro['id']}", json={"isbn": libro["isbn"]}
    )

    assert respuesta.status_code == 200


def test_modificar_libro_con_el_isbn_de_otro_da_409(api: Api) -> None:
    uno, otro = api.libro(), api.libro()

    respuesta = api.cliente.patch(f"/libros/{uno['id']}", json={"isbn": otro["isbn"]})

    assert respuesta.status_code == 409
    assert "ISBN" in respuesta.json()["detail"]
    # El 409 no dejó la sesión rota ni cambió el libro.
    assert api.cliente.get(f"/libros/{uno['id']}").json()["isbn"] == uno["isbn"]


@pytest.mark.parametrize(
    "cuerpo", [{"stock": -1}, {"stock": None}, {"titulo": None}, {"anio": 1000}]
)
def test_modificar_libro_con_datos_invalidos_da_422(
    api: Api, cuerpo: dict[str, int | None]
) -> None:
    libro = api.libro()

    assert api.cliente.patch(f"/libros/{libro['id']}", json=cuerpo).status_code == 422


def test_modificar_libro_inexistente_da_404(api: Api) -> None:
    assert api.cliente.patch("/libros/9999", json={"stock": 1}).status_code == 404


# --------------------------------------------------------------------- baja


def test_eliminar_libro_devuelve_204_y_luego_da_404(api: Api) -> None:
    libro = api.libro()

    respuesta = api.cliente.delete(f"/libros/{libro['id']}")

    assert respuesta.status_code == 204
    assert api.cliente.get(f"/libros/{libro['id']}").status_code == 404


def test_eliminar_libro_inexistente_da_404(api: Api) -> None:
    assert api.cliente.delete("/libros/9999").status_code == 404


def test_eliminar_libro_con_prestamo_activo_da_409(api: Api) -> None:
    libro = api.libro()
    api.prestar_ok(api.socio()["id"], libro["id"])

    respuesta = api.cliente.delete(f"/libros/{libro['id']}")

    assert respuesta.status_code == 409
    assert "préstamos registrados" in respuesta.json()["detail"]


def test_eliminar_libro_con_prestamo_devuelto_tambien_da_409(api: Api) -> None:
    libro = api.libro()
    prestamo = api.prestar_ok(api.socio()["id"], libro["id"])
    api.devolver(prestamo["id"])

    assert api.cliente.delete(f"/libros/{libro['id']}").status_code == 409


def test_eliminar_libro_borra_sus_vinculos_con_autores(api: Api, motor: Engine) -> None:
    libro, autor = api.libro(), api.autor()
    api.cliente.post(f"/libros/{libro['id']}/autores/{autor['id']}")

    api.cliente.delete(f"/libros/{libro['id']}")

    with Session(motor) as sesion:
        assert sesion.exec(select(LibroAutor)).all() == []
    assert api.cliente.delete(f"/autores/{autor['id']}").status_code == 204


# ------------------------------------------------- relación libro - autor


def test_asociar_autor_devuelve_201_con_el_libro_y_sus_autores(api: Api) -> None:
    libro, autor = api.libro(), api.autor()

    respuesta = api.cliente.post(f"/libros/{libro['id']}/autores/{autor['id']}")

    assert respuesta.status_code == 201
    assert respuesta.json()["id"] == libro["id"]
    assert respuesta.json()["autores"] == [autor]


def test_los_autores_de_un_libro_salen_ordenados_por_id(api: Api) -> None:
    libro = api.libro()
    primero, segundo = api.autor(), api.autor()
    api.cliente.post(f"/libros/{libro['id']}/autores/{segundo['id']}")  # al revés

    respuesta = api.cliente.post(f"/libros/{libro['id']}/autores/{primero['id']}")

    assert [a["id"] for a in respuesta.json()["autores"]] == [
        primero["id"],
        segundo["id"],
    ]


def test_los_autores_aparecen_en_el_detalle_y_en_el_listado(api: Api) -> None:
    libro, autor = api.libro(), api.autor()
    api.cliente.post(f"/libros/{libro['id']}/autores/{autor['id']}")

    detalle = api.cliente.get(f"/libros/{libro['id']}").json()
    listado = api.cliente.get("/libros").json()

    assert detalle["autores"] == [autor]
    assert listado[0]["autores"] == [autor]


def test_asociar_dos_veces_el_mismo_autor_da_409_y_no_duplica(api: Api) -> None:
    libro, autor = api.libro(), api.autor()
    api.cliente.post(f"/libros/{libro['id']}/autores/{autor['id']}")

    repetida = api.cliente.post(f"/libros/{libro['id']}/autores/{autor['id']}")

    assert repetida.status_code == 409
    assert "ya está asociado" in repetida.json()["detail"]
    assert len(api.cliente.get(f"/libros/{libro['id']}").json()["autores"]) == 1


def test_despues_de_un_409_de_asociacion_se_puede_seguir_asociando(api: Api) -> None:
    libro, uno, otro = api.libro(), api.autor(), api.autor()
    api.cliente.post(f"/libros/{libro['id']}/autores/{uno['id']}")
    api.cliente.post(f"/libros/{libro['id']}/autores/{uno['id']}")  # 409

    respuesta = api.cliente.post(f"/libros/{libro['id']}/autores/{otro['id']}")

    assert respuesta.status_code == 201
    assert len(respuesta.json()["autores"]) == 2


def test_asociar_con_libro_inexistente_da_404(api: Api) -> None:
    autor = api.autor()

    respuesta = api.cliente.post(f"/libros/9999/autores/{autor['id']}")

    assert respuesta.status_code == 404
    assert "Libro" in respuesta.json()["detail"]


def test_asociar_con_autor_inexistente_da_404(api: Api) -> None:
    libro = api.libro()

    respuesta = api.cliente.post(f"/libros/{libro['id']}/autores/9999")

    assert respuesta.status_code == 404
    assert "Autor" in respuesta.json()["detail"]


def test_asociar_con_ambos_inexistentes_informa_el_libro(api: Api) -> None:
    respuesta = api.cliente.post("/libros/9999/autores/9999")

    assert respuesta.status_code == 404
    assert "Libro" in respuesta.json()["detail"]


def test_desasociar_autor_devuelve_204_y_lo_quita_del_libro(api: Api) -> None:
    libro, uno, otro = api.libro(), api.autor(), api.autor()
    api.cliente.post(f"/libros/{libro['id']}/autores/{uno['id']}")
    api.cliente.post(f"/libros/{libro['id']}/autores/{otro['id']}")

    respuesta = api.cliente.delete(f"/libros/{libro['id']}/autores/{uno['id']}")

    assert respuesta.status_code == 204
    autores = api.cliente.get(f"/libros/{libro['id']}").json()["autores"]
    assert [a["id"] for a in autores] == [otro["id"]]


def test_desasociar_un_autor_no_asociado_da_404(api: Api) -> None:
    libro, autor = api.libro(), api.autor()

    respuesta = api.cliente.delete(f"/libros/{libro['id']}/autores/{autor['id']}")

    assert respuesta.status_code == 404
    assert "no está asociado" in respuesta.json()["detail"]


def test_desasociar_con_libro_o_autor_inexistente_da_404(api: Api) -> None:
    libro, autor = api.libro(), api.autor()

    assert api.cliente.delete(f"/libros/9999/autores/{autor['id']}").status_code == 404
    assert api.cliente.delete(f"/libros/{libro['id']}/autores/9999").status_code == 404


def test_se_puede_reasociar_un_autor_despues_de_desasociarlo(api: Api) -> None:
    libro, autor = api.libro(), api.autor()
    api.cliente.post(f"/libros/{libro['id']}/autores/{autor['id']}")
    api.cliente.delete(f"/libros/{libro['id']}/autores/{autor['id']}")

    respuesta = api.cliente.post(f"/libros/{libro['id']}/autores/{autor['id']}")

    assert respuesta.status_code == 201
