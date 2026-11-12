"""Tests de la Etapa 7: roles, credenciales y permisos.

Los demás tests trabajan como bibliotecario (el cliente de conftest lo envía
siempre). Acá se prueba lo que cambia con el rol: quién puede qué, qué pasa
sin credenciales o con credenciales inválidas, y que Swagger lo documente.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session

from services import seguridad as servicio
from services.excepciones import NoAutenticado, OperacionNoPermitida
from services.seguridad import Rol, Usuario
from tests.ayudas import Api

# Endpoints que solo puede usar el bibliotecario. Los ids no existen: la
# autorización se decide antes de buscar nada, así que el resultado no depende
# de los datos.
SOLO_BIBLIOTECARIO = [
    ("POST", "/autores"),
    ("PATCH", "/autores/1"),
    ("DELETE", "/autores/1"),
    ("POST", "/libros"),
    ("PATCH", "/libros/1"),
    ("DELETE", "/libros/1"),
    ("POST", "/libros/1/autores/1"),
    ("DELETE", "/libros/1/autores/1"),
    ("POST", "/socios"),
    ("GET", "/socios"),
    ("GET", "/socios/1"),
    ("PATCH", "/socios/1"),
    ("DELETE", "/socios/1"),
    ("POST", "/prestamos"),
    ("POST", "/prestamos/1/devolucion"),
]


def como_socio(socio_id: int | str) -> dict[str, str]:
    """Encabezados con los que un socio se identifica."""
    return {"X-Rol": "socio", "X-Socio-Id": str(socio_id)}


# --- Sin credenciales y credenciales inválidas (401) -------------------------


@pytest.mark.parametrize(("metodo", "ruta"), SOLO_BIBLIOTECARIO)
def test_sin_credenciales_los_endpoints_del_bibliotecario_dan_401(
    anonimo: TestClient, metodo: str, ruta: str
) -> None:
    respuesta = anonimo.request(metodo, ruta)

    assert respuesta.status_code == 401
    assert "X-Rol" in respuesta.json()["detail"]


def test_sin_credenciales_tambien_se_exige_para_consultar_un_prestamo(
    anonimo: TestClient,
) -> None:
    assert anonimo.get("/prestamos/1").status_code == 401
    assert anonimo.get("/socios/1/prestamos").status_code == 401


@pytest.mark.parametrize(
    ("encabezados", "fragmento"),
    [
        ({}, "Falta el encabezado X-Rol"),
        ({"X-Rol": "admin"}, "no es válido"),
        ({"X-Rol": "socio"}, "requiere el encabezado X-Socio-Id"),
        ({"X-Rol": "socio", "X-Socio-Id": "abc"}, "número entero positivo"),
        ({"X-Rol": "socio", "X-Socio-Id": "-1"}, "número entero positivo"),
        ({"X-Rol": "socio", "X-Socio-Id": "1.5"}, "número entero positivo"),
        ({"X-Rol": "socio", "X-Socio-Id": "0"}, "no existe"),
        ({"X-Rol": "socio", "X-Socio-Id": "999"}, "no existe"),
        ({"X-Rol": "socio", "X-Socio-Id": "9" * 19}, "no existe"),
        ({"X-Rol": "socio", "X-Socio-Id": "99999999999999999999"}, "no existe"),
        ({"X-Rol": "socio", "X-Socio-Id": "9" * 5000}, "no existe"),
    ],
)
def test_credenciales_invalidas_dan_401_con_su_motivo(
    anonimo: TestClient, encabezados: dict[str, str], fragmento: str
) -> None:
    respuesta = anonimo.get("/prestamos/1", headers=encabezados)

    assert respuesta.status_code == 401
    assert fragmento in respuesta.json()["detail"]


def test_la_autenticacion_se_evalua_antes_que_la_validacion_del_cuerpo(
    anonimo: TestClient, api: Api
) -> None:
    socio = api.socio()

    sin_credenciales = anonimo.post("/autores", json={})
    como_un_socio = anonimo.post("/autores", json={}, headers=como_socio(socio["id"]))

    assert sin_credenciales.status_code == 401
    assert como_un_socio.status_code == 403  # y no 422 por el cuerpo vacío


# --- Rol socio en los endpoints del bibliotecario (403) ----------------------


@pytest.mark.parametrize(("metodo", "ruta"), SOLO_BIBLIOTECARIO)
def test_un_socio_no_puede_usar_los_endpoints_del_bibliotecario(
    api: Api, metodo: str, ruta: str
) -> None:
    socio = api.socio()

    respuesta = api.cliente.request(metodo, ruta, headers=como_socio(socio["id"]))

    assert respuesta.status_code == 403
    assert "solo para el bibliotecario" in respuesta.json()["detail"]


def test_un_socio_no_puede_pedirse_un_prestamo_a_si_mismo(api: Api) -> None:
    socio = api.socio()
    libro = api.libro(stock=1)

    respuesta = api.cliente.post(
        "/prestamos",
        json={"socio_id": socio["id"], "libro_id": libro["id"]},
        headers=como_socio(socio["id"]),
    )

    assert respuesta.status_code == 403
    assert api.stock(libro["id"]) == 1  # no se prestó nada


# --- Catálogo público --------------------------------------------------------


def test_el_catalogo_se_puede_consultar_sin_credenciales(
    api: Api, anonimo: TestClient
) -> None:
    autor = api.autor()
    libro = api.libro()
    api.cliente.post(f"/libros/{libro['id']}/autores/{autor['id']}")

    consultas = [
        "/autores",
        f"/autores/{autor['id']}",
        f"/autores/{autor['id']}/libros",
        "/libros",
        "/libros?disponibles=true",
        f"/libros/{libro['id']}",
    ]

    for ruta in consultas:
        assert anonimo.get(ruta).status_code == 200, ruta


def test_un_socio_tambien_consulta_el_catalogo(api: Api) -> None:
    socio = api.socio()
    libro = api.libro()

    respuesta = api.cliente.get(
        f"/libros/{libro['id']}", headers=como_socio(socio["id"])
    )

    assert respuesta.status_code == 200


def test_la_documentacion_de_la_api_es_publica(anonimo: TestClient) -> None:
    assert anonimo.get("/docs").status_code == 200
    assert anonimo.get("/openapi.json").status_code == 200


# --- El socio ve únicamente sus préstamos ------------------------------------


@pytest.fixture
def dos_socios_con_prestamos(api: Api) -> dict[str, int]:
    """Ana con dos préstamos (uno devuelto) y Beto con uno."""
    ana = api.socio(nombre="Ana")
    beto = api.socio(nombre="Beto")
    libro = api.libro(stock=5)
    ana_1 = api.prestar_ok(ana["id"], libro["id"])
    ana_2 = api.prestar_ok(ana["id"], libro["id"])
    beto_1 = api.prestar_ok(beto["id"], libro["id"])
    assert api.devolver(ana_1["id"]).status_code == 200
    return {
        "ana": ana["id"],
        "beto": beto["id"],
        "ana_1": ana_1["id"],
        "ana_2": ana_2["id"],
        "beto_1": beto_1["id"],
    }


def test_un_socio_ve_sus_propios_prestamos(
    api: Api, dos_socios_con_prestamos: dict[str, int]
) -> None:
    ids = dos_socios_con_prestamos

    todos = api.cliente.get(
        f"/socios/{ids['ana']}/prestamos", headers=como_socio(ids["ana"])
    )
    activos = api.cliente.get(
        f"/socios/{ids['ana']}/prestamos?activos=true", headers=como_socio(ids["ana"])
    )

    assert todos.status_code == 200
    assert [p["id"] for p in todos.json()] == [ids["ana_1"], ids["ana_2"]]
    assert [p["id"] for p in activos.json()] == [ids["ana_2"]]


def test_un_socio_no_ve_los_prestamos_de_otro_socio(
    api: Api, dos_socios_con_prestamos: dict[str, int]
) -> None:
    ids = dos_socios_con_prestamos

    respuesta = api.cliente.get(
        f"/socios/{ids['beto']}/prestamos", headers=como_socio(ids["ana"])
    )

    assert respuesta.status_code == 403
    assert "propios préstamos" in respuesta.json()["detail"]


def test_un_socio_no_puede_averiguar_si_existe_otro_socio(api: Api) -> None:
    socio = api.socio()

    respuesta = api.cliente.get(
        "/socios/999/prestamos", headers=como_socio(socio["id"])
    )

    assert respuesta.status_code == 403  # y no 404: no revela qué ids existen


def test_el_bibliotecario_ve_los_prestamos_de_cualquier_socio(
    api: Api, dos_socios_con_prestamos: dict[str, int]
) -> None:
    ids = dos_socios_con_prestamos

    de_ana = api.cliente.get(f"/socios/{ids['ana']}/prestamos")
    de_beto = api.cliente.get(f"/socios/{ids['beto']}/prestamos")

    assert len(de_ana.json()) == 2
    assert [p["id"] for p in de_beto.json()] == [ids["beto_1"]]


def test_el_listado_de_un_socio_inexistente_sigue_dando_404_al_bibliotecario(
    api: Api,
) -> None:
    assert api.cliente.get("/socios/999/prestamos").status_code == 404


def test_un_socio_consulta_un_prestamo_propio_pero_no_uno_ajeno(
    api: Api, dos_socios_con_prestamos: dict[str, int]
) -> None:
    ids = dos_socios_con_prestamos
    de_ana = como_socio(ids["ana"])

    propio = api.cliente.get(f"/prestamos/{ids['ana_2']}", headers=de_ana)
    ajeno = api.cliente.get(f"/prestamos/{ids['beto_1']}", headers=de_ana)
    inexistente = api.cliente.get("/prestamos/999", headers=de_ana)

    assert propio.status_code == 200
    assert propio.json()["socio_id"] == ids["ana"]
    assert ajeno.status_code == 403
    assert inexistente.status_code == 404


def test_el_bibliotecario_consulta_cualquier_prestamo(
    api: Api, dos_socios_con_prestamos: dict[str, int]
) -> None:
    ids = dos_socios_con_prestamos

    assert api.cliente.get(f"/prestamos/{ids['beto_1']}").status_code == 200


def test_un_socio_inactivo_puede_consultar_sus_prestamos(api: Api) -> None:
    socio = api.socio()
    libro = api.libro()
    api.prestar_ok(socio["id"], libro["id"])
    api.cliente.patch(f"/socios/{socio['id']}", json={"activo": False})

    respuesta = api.cliente.get(
        f"/socios/{socio['id']}/prestamos", headers=como_socio(socio["id"])
    )

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1


# --- Forma de los encabezados ------------------------------------------------


def test_el_rol_no_distingue_mayusculas_ni_espacios(api: Api) -> None:
    socio = api.socio()

    como_bibliotecario = api.cliente.get(
        "/socios", headers={"X-Rol": " Bibliotecario "}
    )
    como_un_socio = api.cliente.get(
        f"/socios/{socio['id']}/prestamos",
        headers={"X-Rol": "SOCIO", "X-Socio-Id": f" {socio['id']} "},
    )

    assert como_bibliotecario.status_code == 200
    assert como_un_socio.status_code == 200


def test_el_bibliotecario_ignora_el_encabezado_de_socio(api: Api) -> None:
    respuesta = api.cliente.get(
        "/socios", headers={"X-Rol": "bibliotecario", "X-Socio-Id": "abc"}
    )

    assert respuesta.status_code == 200


# --- Documentación en Swagger ------------------------------------------------


def test_swagger_declara_los_dos_encabezados_como_esquemas_de_seguridad(
    anonimo: TestClient,
) -> None:
    esquemas = anonimo.get("/openapi.json").json()["components"]["securitySchemes"]

    assert esquemas["Rol"]["type"] == "apiKey"
    assert esquemas["Rol"]["in"] == "header"
    assert esquemas["Rol"]["name"] == "X-Rol"
    assert esquemas["SocioId"]["name"] == "X-Socio-Id"


def test_swagger_marca_solo_los_endpoints_que_exigen_credenciales(
    anonimo: TestClient,
) -> None:
    rutas = anonimo.get("/openapi.json").json()["paths"]

    for metodo, ruta in [("post", "/autores"), ("get", "/prestamos/{prestamo_id}")]:
        assert rutas[ruta][metodo]["security"], (metodo, ruta)
    for metodo, ruta in [("get", "/autores"), ("get", "/libros/{libro_id}")]:
        assert "security" not in rutas[ruta][metodo], (metodo, ruta)


def test_swagger_documenta_el_401_y_el_403_donde_corresponde(
    anonimo: TestClient,
) -> None:
    rutas = anonimo.get("/openapi.json").json()["paths"]

    assert {"401", "403"} <= set(rutas["/autores"]["post"]["responses"])
    assert {"401", "403", "404"} <= set(
        rutas["/prestamos/{prestamo_id}"]["get"]["responses"]
    )
    assert {"401", "403", "404"} <= set(
        rutas["/socios/{socio_id}/prestamos"]["get"]["responses"]
    )


# --- Capa de servicios (sin HTTP) --------------------------------------------


def test_identificar_usuario_devuelve_el_rol_y_el_id_del_socio(
    api: Api, motor: Engine
) -> None:
    socio = api.socio()

    with Session(motor) as sesion:
        bibliotecario = servicio.identificar_usuario(sesion, "bibliotecario", None)
        un_socio = servicio.identificar_usuario(sesion, "socio", str(socio["id"]))

    assert bibliotecario == Usuario(Rol.BIBLIOTECARIO)
    assert un_socio == Usuario(Rol.SOCIO, socio["id"])


def test_exigir_bibliotecario_solo_rechaza_al_socio() -> None:
    servicio.exigir_bibliotecario(Usuario(Rol.BIBLIOTECARIO))

    with pytest.raises(OperacionNoPermitida):
        servicio.exigir_bibliotecario(Usuario(Rol.SOCIO, 1))


def test_exigir_propietario_acepta_al_bibliotecario_y_al_propio_socio() -> None:
    servicio.exigir_propietario(Usuario(Rol.BIBLIOTECARIO), 7)
    servicio.exigir_propietario(Usuario(Rol.SOCIO, 7), 7)

    with pytest.raises(OperacionNoPermitida):
        servicio.exigir_propietario(Usuario(Rol.SOCIO, 7), 8)


def test_identificar_usuario_sin_rol_lanza_no_autenticado(motor: Engine) -> None:
    with Session(motor) as sesion, pytest.raises(NoAutenticado):
        servicio.identificar_usuario(sesion, None, None)


@pytest.mark.parametrize("id_de_socio", ["²", "١", "１"])
def test_un_id_con_digitos_que_no_son_ascii_no_se_acepta(
    motor: Engine, id_de_socio: str
) -> None:
    # isdigit() devuelve True para estos caracteres (exponente, dígito árabe,
    # dígito de ancho completo) y int() convertiría los dos últimos: se
    # rechazan antes. Un cliente HTTP ni siquiera puede enviarlos en un
    # encabezado, por eso la prueba se hace sobre el servicio.
    with Session(motor) as sesion, pytest.raises(NoAutenticado) as error:
        servicio.identificar_usuario(sesion, "socio", id_de_socio)

    assert "número entero positivo" in error.value.mensaje
