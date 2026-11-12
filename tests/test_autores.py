"""Tests de los autores: CRUD, validaciones, paginación y sus libros."""

import pytest

from tests.ayudas import Api

# Ids que no pueden existir. Los dos últimos superan el máximo de SQLite; antes
# de la corrección de la Etapa 4 daban 500 en vez de 404.
IDS_IMPOSIBLES = [0, -1, 2**63, 10**30]


# --------------------------------------------------------------------- alta


def test_crear_autor_devuelve_201_con_id(api: Api) -> None:
    respuesta = api.cliente.post(
        "/autores", json={"nombre": "Julio Cortázar", "nacionalidad": "Argentina"}
    )

    assert respuesta.status_code == 201
    assert respuesta.json() == {
        "id": 1,
        "nombre": "Julio Cortázar",
        "nacionalidad": "Argentina",
    }


def test_crear_autor_recorta_los_espacios(api: Api) -> None:
    respuesta = api.cliente.post(
        "/autores", json={"nombre": "  Ana  ", "nacionalidad": " Chile "}
    )

    assert respuesta.json()["nombre"] == "Ana"
    assert respuesta.json()["nacionalidad"] == "Chile"


def test_crear_autor_ignora_el_id_enviado_por_el_cliente(api: Api) -> None:
    respuesta = api.cliente.post(
        "/autores", json={"id": 99, "nombre": "Ana", "nacionalidad": "Chile"}
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["id"] == 1


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"nombre": "A", "nacionalidad": "Chile"},  # nombre de 1 letra (mín. 2)
        {"nombre": "A" * 101, "nacionalidad": "Chile"},  # nombre de 101 (máx. 100)
        {"nombre": "   ", "nacionalidad": "Chile"},  # queda vacío al recortar
        {"nombre": "Ana", "nacionalidad": "C"},  # nacionalidad de 1 letra
        {"nombre": "Ana", "nacionalidad": "C" * 61},  # nacionalidad de 61 (máx. 60)
        {"nombre": "Ana"},  # falta la nacionalidad
        {"nacionalidad": "Chile"},  # falta el nombre
        {},
    ],
)
def test_crear_autor_con_datos_invalidos_da_422(
    api: Api, cuerpo: dict[str, str]
) -> None:
    assert api.cliente.post("/autores", json=cuerpo).status_code == 422


def test_crear_autores_homonimos_esta_permitido(api: Api) -> None:
    api.autor(nombre="Juan Pérez")

    assert (
        api.cliente.post(
            "/autores", json={"nombre": "Juan Pérez", "nacionalidad": "Chile"}
        ).status_code
        == 201
    )


# ------------------------------------------------------------------ listado


def test_listar_autores_vacio_devuelve_lista_vacia(api: Api) -> None:
    respuesta = api.cliente.get("/autores")

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_listar_autores_ordenados_por_id_y_paginados(api: Api) -> None:
    ids = [api.autor()["id"] for _ in range(5)]

    todos = api.cliente.get("/autores").json()
    pagina = api.cliente.get("/autores?skip=1&limit=2").json()
    pasado_el_final = api.cliente.get("/autores?skip=100").json()

    assert [a["id"] for a in todos] == ids
    assert [a["id"] for a in pagina] == ids[1:3]
    assert pasado_el_final == []


@pytest.mark.parametrize(
    "consulta",
    ["limit=0", "limit=101", "skip=-1", f"skip={10**30}", "limit=abc"],
)
def test_listar_autores_con_paginacion_invalida_da_422(api: Api, consulta: str) -> None:
    assert api.cliente.get(f"/autores?{consulta}").status_code == 422


# ----------------------------------------------------------------- consulta


def test_obtener_autor_existente_devuelve_200(api: Api) -> None:
    autor = api.autor(nombre="Ana", nacionalidad="Chile")

    respuesta = api.cliente.get(f"/autores/{autor['id']}")

    assert respuesta.status_code == 200
    assert respuesta.json() == autor


def test_obtener_autor_inexistente_da_404(api: Api) -> None:
    respuesta = api.cliente.get("/autores/9999")

    assert respuesta.status_code == 404
    assert "Autor" in respuesta.json()["detail"]


@pytest.mark.parametrize("id_autor", IDS_IMPOSIBLES)
def test_ids_imposibles_dan_404_y_no_500(api: Api, id_autor: int) -> None:
    assert api.cliente.get(f"/autores/{id_autor}").status_code == 404
    assert api.cliente.delete(f"/autores/{id_autor}").status_code == 404
    assert api.cliente.get(f"/autores/{id_autor}/libros").status_code == 404


def test_obtener_autor_con_id_no_numerico_da_422(api: Api) -> None:
    assert api.cliente.get("/autores/abc").status_code == 422


# ------------------------------------------------------------- modificación


def test_modificar_autor_cambia_solo_los_campos_enviados(api: Api) -> None:
    autor = api.autor(nombre="Ana", nacionalidad="Chile")

    respuesta = api.cliente.patch(f"/autores/{autor['id']}", json={"nombre": "Anita"})

    assert respuesta.status_code == 200
    assert respuesta.json() == {**autor, "nombre": "Anita"}
    assert api.cliente.get(f"/autores/{autor['id']}").json()["nombre"] == "Anita"


def test_modificar_autor_con_cuerpo_vacio_no_cambia_nada(api: Api) -> None:
    autor = api.autor()

    respuesta = api.cliente.patch(f"/autores/{autor['id']}", json={})

    assert respuesta.status_code == 200
    assert respuesta.json() == autor


@pytest.mark.parametrize(
    "cuerpo", [{"nombre": None}, {"nacionalidad": None}, {"nombre": "A"}]
)
def test_modificar_autor_con_datos_invalidos_da_422(
    api: Api, cuerpo: dict[str, str | None]
) -> None:
    autor = api.autor()

    assert api.cliente.patch(f"/autores/{autor['id']}", json=cuerpo).status_code == 422


def test_modificar_autor_inexistente_da_404(api: Api) -> None:
    respuesta = api.cliente.patch("/autores/9999", json={"nombre": "Ana"})

    assert respuesta.status_code == 404


# --------------------------------------------------------------------- baja


def test_eliminar_autor_devuelve_204_y_luego_da_404(api: Api) -> None:
    autor = api.autor()

    respuesta = api.cliente.delete(f"/autores/{autor['id']}")

    assert respuesta.status_code == 204
    assert respuesta.content == b""
    assert api.cliente.get(f"/autores/{autor['id']}").status_code == 404


def test_eliminar_autor_inexistente_da_404(api: Api) -> None:
    assert api.cliente.delete("/autores/9999").status_code == 404


def test_eliminar_autor_con_libros_da_409_hasta_desasociarlos(api: Api) -> None:
    autor, libro = api.autor(), api.libro()
    api.cliente.post(f"/libros/{libro['id']}/autores/{autor['id']}")

    bloqueado = api.cliente.delete(f"/autores/{autor['id']}")
    api.cliente.delete(f"/libros/{libro['id']}/autores/{autor['id']}")
    permitido = api.cliente.delete(f"/autores/{autor['id']}")

    assert bloqueado.status_code == 409
    assert "libros asociados" in bloqueado.json()["detail"]
    assert permitido.status_code == 204


# ----------------------------------------------------- libros de un autor


def test_libros_de_un_autor_incluyen_todos_sus_autores(api: Api) -> None:
    autor, coautor = api.autor(), api.autor()
    libros = [api.libro() for _ in range(3)]
    for libro in libros:
        api.cliente.post(f"/libros/{libro['id']}/autores/{autor['id']}")
    api.cliente.post(f"/libros/{libros[1]['id']}/autores/{coautor['id']}")
    ajeno = api.libro()
    api.cliente.post(f"/libros/{ajeno['id']}/autores/{coautor['id']}")

    respuesta = api.cliente.get(f"/autores/{autor['id']}/libros")

    assert respuesta.status_code == 200
    assert [x["id"] for x in respuesta.json()] == [x["id"] for x in libros]
    autores_del_segundo = respuesta.json()[1]["autores"]
    assert [a["id"] for a in autores_del_segundo] == [autor["id"], coautor["id"]]


def test_libros_de_un_autor_se_paginan(api: Api) -> None:
    autor = api.autor()
    libros = [api.libro() for _ in range(5)]
    for libro in libros:
        api.cliente.post(f"/libros/{libro['id']}/autores/{autor['id']}")

    respuesta = api.cliente.get(f"/autores/{autor['id']}/libros?skip=1&limit=2")

    assert [x["id"] for x in respuesta.json()] == [libros[1]["id"], libros[2]["id"]]
    assert (
        api.cliente.get(f"/autores/{autor['id']}/libros?limit=101").status_code == 422
    )


def test_autor_sin_libros_devuelve_lista_vacia(api: Api) -> None:
    autor = api.autor()

    respuesta = api.cliente.get(f"/autores/{autor['id']}/libros")

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_libros_de_un_autor_inexistente_da_404(api: Api) -> None:
    respuesta = api.cliente.get("/autores/9999/libros")

    assert respuesta.status_code == 404
    assert "Autor" in respuesta.json()["detail"]
