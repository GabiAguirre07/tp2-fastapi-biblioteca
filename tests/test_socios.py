"""Tests de los socios: CRUD, validaciones y baja protegida por préstamos."""

import pytest

from tests.ayudas import Api

IDS_IMPOSIBLES = [0, -1, 2**63, 10**30]


# --------------------------------------------------------------------- alta


def test_crear_socio_devuelve_201_y_queda_activo_por_defecto(api: Api) -> None:
    respuesta = api.cliente.post(
        "/socios", json={"nombre": "Ana Gómez", "email": "ana@example.com"}
    )

    assert respuesta.status_code == 201
    assert respuesta.json() == {
        "id": 1,
        "nombre": "Ana Gómez",
        "email": "ana@example.com",
        "activo": True,
    }


def test_crear_socio_guarda_el_email_en_minusculas_y_sin_espacios(api: Api) -> None:
    respuesta = api.cliente.post(
        "/socios", json={"nombre": "Ana", "email": "  Ana@Example.COM "}
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["email"] == "ana@example.com"


def test_crear_socio_inactivo_es_posible(api: Api) -> None:
    respuesta = api.cliente.post(
        "/socios",
        json={"nombre": "Beto", "email": "beto@example.com", "activo": False},
    )

    assert respuesta.json()["activo"] is False


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"nombre": "A", "email": "a@example.com"},
        {"nombre": "A" * 101, "email": "a@example.com"},
        {"nombre": "   ", "email": "a@example.com"},
        {"nombre": "Ana", "email": "no-es-un-email"},
        {"nombre": "Ana", "email": "ana@"},
        {"nombre": "Ana", "email": ""},
        {"nombre": "Ana", "email": 12345},  # número en lugar de texto
        {"nombre": "Ana", "email": "ana@prueba.test"},  # dominio reservado
        {"nombre": "Ana", "email": "ana@example.com", "activo": "quizás"},
        {"nombre": "Ana"},
        {"email": "ana@example.com"},
    ],
)
def test_crear_socio_con_datos_invalidos_da_422(
    api: Api, cuerpo: dict[str, str | int]
) -> None:
    assert api.cliente.post("/socios", json=cuerpo).status_code == 422


# ------------------------------------------------------------------ listado


def test_listar_socios_ordenados_por_id_y_paginados(api: Api) -> None:
    ids = [api.socio()["id"] for _ in range(5)]

    todos = api.cliente.get("/socios").json()
    pagina = api.cliente.get("/socios?skip=3&limit=5").json()

    assert [s["id"] for s in todos] == ids
    assert [s["id"] for s in pagina] == ids[3:]


@pytest.mark.parametrize(
    "consulta", ["limit=0", "limit=101", "skip=-1", f"skip={10**30}"]
)
def test_listar_socios_con_paginacion_invalida_da_422(api: Api, consulta: str) -> None:
    assert api.cliente.get(f"/socios?{consulta}").status_code == 422


# ----------------------------------------------------------------- consulta


def test_obtener_socio_existente_devuelve_200(api: Api) -> None:
    socio = api.socio()

    respuesta = api.cliente.get(f"/socios/{socio['id']}")

    assert respuesta.status_code == 200
    assert respuesta.json() == socio


def test_obtener_socio_inexistente_da_404(api: Api) -> None:
    respuesta = api.cliente.get("/socios/9999")

    assert respuesta.status_code == 404
    assert "Socio" in respuesta.json()["detail"]


@pytest.mark.parametrize("id_socio", IDS_IMPOSIBLES)
def test_ids_imposibles_dan_404_y_no_500(api: Api, id_socio: int) -> None:
    assert api.cliente.get(f"/socios/{id_socio}").status_code == 404
    assert (
        api.cliente.patch(f"/socios/{id_socio}", json={"activo": False}).status_code
        == 404
    )
    assert api.cliente.delete(f"/socios/{id_socio}").status_code == 404
    assert api.cliente.get(f"/socios/{id_socio}/prestamos").status_code == 404


# ------------------------------------------------------------- modificación


def test_modificar_socio_cambia_solo_los_campos_enviados(api: Api) -> None:
    socio = api.socio()

    respuesta = api.cliente.patch(f"/socios/{socio['id']}", json={"nombre": "Nuevo"})

    assert respuesta.status_code == 200
    assert respuesta.json() == {**socio, "nombre": "Nuevo"}


def test_desactivar_y_reactivar_un_socio(api: Api) -> None:
    socio = api.socio()

    desactivado = api.cliente.patch(f"/socios/{socio['id']}", json={"activo": False})
    reactivado = api.cliente.patch(f"/socios/{socio['id']}", json={"activo": True})

    assert desactivado.json()["activo"] is False
    assert reactivado.json()["activo"] is True


def test_modificar_el_email_lo_normaliza(api: Api) -> None:
    socio = api.socio()

    respuesta = api.cliente.patch(
        f"/socios/{socio['id']}", json={"email": "NUEVO@Example.com"}
    )

    assert respuesta.json()["email"] == "nuevo@example.com"


def test_modificar_socio_con_el_email_de_otro_da_409(api: Api) -> None:
    uno, otro = api.socio(), api.socio()

    respuesta = api.cliente.patch(f"/socios/{uno['id']}", json={"email": otro["email"]})

    assert respuesta.status_code == 409
    assert "email" in respuesta.json()["detail"]
    assert api.cliente.get(f"/socios/{uno['id']}").json()["email"] == uno["email"]


def test_modificar_socio_con_su_propio_email_no_es_conflicto(api: Api) -> None:
    socio = api.socio()

    respuesta = api.cliente.patch(
        f"/socios/{socio['id']}", json={"email": socio["email"]}
    )

    assert respuesta.status_code == 200


@pytest.mark.parametrize(
    "cuerpo",
    [{"nombre": None}, {"email": None}, {"activo": None}, {"email": "mal"}],
)
def test_modificar_socio_con_datos_invalidos_da_422(
    api: Api, cuerpo: dict[str, str | None]
) -> None:
    socio = api.socio()

    assert api.cliente.patch(f"/socios/{socio['id']}", json=cuerpo).status_code == 422


def test_modificar_socio_inexistente_da_404(api: Api) -> None:
    assert api.cliente.patch("/socios/9999", json={"activo": False}).status_code == 404


# --------------------------------------------------------------------- baja


def test_eliminar_socio_sin_prestamos_devuelve_204_y_luego_404(api: Api) -> None:
    socio = api.socio()

    respuesta = api.cliente.delete(f"/socios/{socio['id']}")

    assert respuesta.status_code == 204
    assert api.cliente.get(f"/socios/{socio['id']}").status_code == 404


def test_eliminar_socio_inexistente_da_404(api: Api) -> None:
    assert api.cliente.delete("/socios/9999").status_code == 404


def test_eliminar_socio_con_prestamo_activo_da_409(api: Api) -> None:
    socio = api.socio()
    api.prestar_ok(socio["id"], api.libro()["id"])

    respuesta = api.cliente.delete(f"/socios/{socio['id']}")

    assert respuesta.status_code == 409
    assert "préstamos registrados" in respuesta.json()["detail"]
    assert api.cliente.get(f"/socios/{socio['id']}").status_code == 200


def test_eliminar_socio_con_prestamo_devuelto_tambien_da_409(api: Api) -> None:
    socio = api.socio()
    prestamo = api.prestar_ok(socio["id"], api.libro()["id"])
    api.devolver(prestamo["id"])

    assert api.cliente.delete(f"/socios/{socio['id']}").status_code == 409
