"""Tests de los préstamos: endpoints, casos borde, vencidos y multas."""

import pytest

from tests.ayudas import Api, Reloj

IDS_IMPOSIBLES = [0, -1, 2**63, 10**30]

CAMPOS_DE_UN_PRESTAMO = {
    "id",
    "socio_id",
    "libro_id",
    "fecha_prestamo",
    "fecha_vencimiento",
    "fecha_devolucion",
    "multa",
    "vencido",
    "dias_atraso",
}


# ---------------------------------------------------------- POST /prestamos


def test_prestar_devuelve_201_con_el_prestamo_completo(api: Api) -> None:
    socio, libro = api.socio(), api.libro(stock=2)

    respuesta = api.prestar(socio["id"], libro["id"])

    assert respuesta.status_code == 201
    assert respuesta.json() == {
        "id": 1,
        "socio_id": socio["id"],
        "libro_id": libro["id"],
        "fecha_prestamo": "2026-03-10",
        "fecha_vencimiento": "2026-03-24",
        "fecha_devolucion": None,
        "multa": 0,
        "vencido": False,
        "dias_atraso": 0,
    }


def test_el_cliente_no_puede_imponer_fechas_ni_multa(api: Api) -> None:
    socio, libro = api.socio(), api.libro()

    respuesta = api.cliente.post(
        "/prestamos",
        json={
            "socio_id": socio["id"],
            "libro_id": libro["id"],
            "fecha_prestamo": "2000-01-01",
            "fecha_devolucion": "2000-01-02",
            "multa": 5000,
        },
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["fecha_prestamo"] == "2026-03-10"
    assert respuesta.json()["fecha_devolucion"] is None
    assert respuesta.json()["multa"] == 0


@pytest.mark.parametrize(
    "cuerpo",
    [
        {},
        {"socio_id": 1},
        {"libro_id": 1},
        {"socio_id": "a", "libro_id": 1},
        {"socio_id": None, "libro_id": 1},
        {"socio_id": 1, "libro_id": 1.5},
    ],
)
def test_prestar_con_cuerpo_invalido_da_422(
    api: Api, cuerpo: dict[str, object]
) -> None:
    assert api.cliente.post("/prestamos", json=cuerpo).status_code == 422


def test_prestar_sin_cuerpo_da_422(api: Api) -> None:
    assert api.cliente.post("/prestamos").status_code == 422


@pytest.mark.parametrize("id_imposible", IDS_IMPOSIBLES)
def test_prestar_con_ids_imposibles_da_404_y_no_500(
    api: Api, id_imposible: int
) -> None:
    socio, libro = api.socio(), api.libro()

    assert api.prestar(id_imposible, libro["id"]).status_code == 404
    assert api.prestar(socio["id"], id_imposible).status_code == 404
    assert api.stock(libro["id"]) == 1


def test_prestar_el_mismo_libro_varias_veces_al_mismo_socio_esta_permitido(
    api: Api,
) -> None:
    socio, libro = api.socio(), api.libro(stock=10)

    codigos = [api.prestar(socio["id"], libro["id"]).status_code for _ in range(4)]

    assert codigos == [201, 201, 201, 409]  # el cuarto choca con el máximo de 3
    assert api.stock(libro["id"]) == 7


def test_el_ultimo_ejemplar_lo_obtiene_un_solo_socio(api: Api) -> None:
    libro = api.libro(stock=1)
    uno, otro = api.socio(), api.socio()

    primero = api.prestar(uno["id"], libro["id"])
    segundo = api.prestar(otro["id"], libro["id"])

    assert (primero.status_code, segundo.status_code) == (201, 409)
    assert api.stock(libro["id"]) == 0


def test_un_socio_puede_volver_a_pedir_cuando_devuelve_un_libro(api: Api) -> None:
    socio = api.socio()
    prestamos = [
        api.prestar_ok(socio["id"], api.libro(stock=5)["id"]) for _ in range(3)
    ]
    otro_libro = api.libro(stock=5)
    assert api.prestar(socio["id"], otro_libro["id"]).status_code == 409

    api.devolver(prestamos[0]["id"])

    assert api.prestar(socio["id"], otro_libro["id"]).status_code == 201
    assert api.prestar(socio["id"], api.libro()["id"]).status_code == 409


def test_los_prestamos_de_un_socio_no_afectan_el_limite_de_otro(api: Api) -> None:
    lleno, libre = api.socio(), api.socio()
    for _ in range(3):
        api.prestar_ok(lleno["id"], api.libro(stock=5)["id"])

    assert api.prestar(libre["id"], api.libro()["id"]).status_code == 201


def test_socio_inexistente_y_libro_inexistente_informa_primero_el_socio(
    api: Api,
) -> None:
    respuesta = api.prestar(9999, 9999)

    assert respuesta.status_code == 404
    assert "Socio" in respuesta.json()["detail"]


# ----------------------------------------- orden de las validaciones (dec. 34)


def test_orden_el_404_del_libro_va_antes_que_el_403_del_socio_inactivo(
    api: Api,
) -> None:
    inactivo = api.socio(activo=False)

    assert api.prestar(inactivo["id"], 9999).status_code == 404


def test_orden_el_403_va_antes_que_el_limite_y_que_el_stock(api: Api) -> None:
    inactivo = api.socio(activo=False)
    agotado = api.libro(stock=0)

    assert api.prestar(inactivo["id"], agotado["id"]).status_code == 403


def test_orden_el_limite_de_3_va_antes_que_la_falta_de_stock(api: Api) -> None:
    socio = api.socio()
    for _ in range(3):
        api.prestar_ok(socio["id"], api.libro(stock=5)["id"])
    agotado = api.libro(stock=0)

    respuesta = api.prestar(socio["id"], agotado["id"])

    assert respuesta.status_code == 409
    assert "3 préstamos activos" in respuesta.json()["detail"]


def test_un_rechazo_no_deja_efectos_ni_prestamo_ni_stock_descontado(api: Api) -> None:
    socio = api.socio()
    for _ in range(3):
        api.prestar_ok(socio["id"], api.libro(stock=5)["id"])
    libro = api.libro(stock=5)

    api.prestar(socio["id"], libro["id"])  # 409 por el límite

    assert api.stock(libro["id"]) == 5
    prestamos = api.cliente.get(f"/socios/{socio['id']}/prestamos").json()
    assert len(prestamos) == 3


def test_un_socio_reactivado_puede_pedir_y_uno_desactivado_deja_de_poder(
    api: Api,
) -> None:
    socio, libro = api.socio(activo=False), api.libro(stock=3)
    assert api.prestar(socio["id"], libro["id"]).status_code == 403

    api.cliente.patch(f"/socios/{socio['id']}", json={"activo": True})
    assert api.prestar(socio["id"], libro["id"]).status_code == 201

    api.cliente.patch(f"/socios/{socio['id']}", json={"activo": False})
    assert api.prestar(socio["id"], libro["id"]).status_code == 403
    assert api.stock(libro["id"]) == 2


# ------------------------------------------------------------- GET /prestamos/{id}


def test_obtener_prestamo_devuelve_el_mismo_json_que_el_alta(api: Api) -> None:
    prestamo = api.prestar_ok(api.socio()["id"], api.libro()["id"])

    respuesta = api.cliente.get(f"/prestamos/{prestamo['id']}")

    assert respuesta.status_code == 200
    assert respuesta.json() == prestamo
    assert set(respuesta.json()) == CAMPOS_DE_UN_PRESTAMO


@pytest.mark.parametrize("id_prestamo", [9999, *IDS_IMPOSIBLES])
def test_obtener_o_devolver_un_prestamo_inexistente_da_404(
    api: Api, id_prestamo: int
) -> None:
    consulta = api.cliente.get(f"/prestamos/{id_prestamo}")
    devolucion = api.devolver(id_prestamo)

    assert consulta.status_code == 404
    assert devolucion.status_code == 404
    assert "Prestamo" in devolucion.json()["detail"]


def test_un_id_de_prestamo_no_numerico_da_422(api: Api) -> None:
    assert api.cliente.get("/prestamos/abc").status_code == 422
    assert api.cliente.post("/prestamos/abc/devolucion").status_code == 422


# ----------------------------------------------------- devolución y multas


def test_devolver_marca_la_fecha_y_el_get_lo_refleja(api: Api, reloj: Reloj) -> None:
    prestamo = api.prestar_ok(api.socio()["id"], api.libro()["id"])
    reloj.avanzar(5)

    devuelto = api.devolver(prestamo["id"])

    assert devuelto.status_code == 200
    assert devuelto.json()["fecha_devolucion"] == "2026-03-15"
    assert devuelto.json()["fecha_prestamo"] == "2026-03-10"
    assert devuelto.json()["fecha_vencimiento"] == "2026-03-24"
    assert api.cliente.get(f"/prestamos/{prestamo['id']}").json() == devuelto.json()


@pytest.mark.parametrize(
    ("dias_de_atraso", "multa_esperada"),
    [(-5, 0), (-1, 0), (0, 0), (1, 100), (2, 200), (10, 1000), (366, 36600)],
)
def test_la_multa_es_100_por_cada_dia_de_atraso(
    api: Api,
    reloj: Reloj,
    dias_de_atraso: int,
    multa_esperada: int,
) -> None:
    prestamo = api.prestar_ok(api.socio()["id"], api.libro()["id"])
    reloj.avanzar(14 + dias_de_atraso)

    devuelto = api.devolver(prestamo["id"])

    assert devuelto.status_code == 200
    assert devuelto.json()["multa"] == multa_esperada
    assert devuelto.json()["dias_atraso"] == max(0, dias_de_atraso)
    assert devuelto.json()["vencido"] is False  # ya devuelto: deja de estar vencido


def test_la_multa_queda_fija_aunque_pasen_los_dias_despues_de_devolver(
    api: Api, reloj: Reloj
) -> None:
    prestamo = api.prestar_ok(api.socio()["id"], api.libro()["id"])
    reloj.avanzar(14 + 4)
    api.devolver(prestamo["id"])

    reloj.avanzar(100)
    consultado = api.cliente.get(f"/prestamos/{prestamo['id']}").json()

    assert consultado["multa"] == 400
    assert consultado["dias_atraso"] == 4
    assert consultado["fecha_devolucion"] == "2026-03-28"


def test_una_segunda_devolucion_no_cambia_ni_la_fecha_ni_la_multa(
    api: Api, reloj: Reloj
) -> None:
    prestamo = api.prestar_ok(api.socio()["id"], api.libro()["id"])
    reloj.avanzar(14 + 2)
    primera = api.devolver(prestamo["id"]).json()

    reloj.avanzar(60)
    segunda = api.devolver(prestamo["id"])

    assert segunda.status_code == 409
    assert api.cliente.get(f"/prestamos/{prestamo['id']}").json() == primera


def test_un_socio_inactivo_puede_devolver_sus_libros(api: Api) -> None:
    socio, libro = api.socio(), api.libro(stock=1)
    prestamo = api.prestar_ok(socio["id"], libro["id"])
    api.cliente.patch(f"/socios/{socio['id']}", json={"activo": False})

    devuelto = api.devolver(prestamo["id"])

    assert devuelto.status_code == 200
    assert api.stock(libro["id"]) == 1


# ----------------------------------------------------------------- vencidos


def test_un_prestamo_activo_pasado_de_fecha_figura_como_vencido(
    api: Api, reloj: Reloj
) -> None:
    prestamo = api.prestar_ok(api.socio()["id"], api.libro()["id"])

    reloj.avanzar(14)  # el día del vencimiento todavía no está vencido
    en_el_dia = api.cliente.get(f"/prestamos/{prestamo['id']}").json()
    reloj.avanzar(1)
    un_dia_despues = api.cliente.get(f"/prestamos/{prestamo['id']}").json()
    reloj.avanzar(10)
    once_dias_despues = api.cliente.get(f"/prestamos/{prestamo['id']}").json()

    assert (en_el_dia["vencido"], en_el_dia["dias_atraso"]) == (False, 0)
    assert (un_dia_despues["vencido"], un_dia_despues["dias_atraso"]) == (True, 1)
    assert (once_dias_despues["vencido"], once_dias_despues["dias_atraso"]) == (
        True,
        11,
    )
    assert once_dias_despues["multa"] == 0  # la multa se cobra recién al devolver


def test_un_prestamo_vencido_sigue_activo_y_cuenta_para_el_maximo(
    api: Api, reloj: Reloj
) -> None:
    socio = api.socio()
    for _ in range(3):
        api.prestar_ok(socio["id"], api.libro(stock=5)["id"])
    reloj.avanzar(90)  # los tres están vencidos

    respuesta = api.prestar(socio["id"], api.libro()["id"])

    assert respuesta.status_code == 409


def test_un_prestamo_vencido_no_bloquea_pedir_si_hay_cupo(
    api: Api, reloj: Reloj
) -> None:
    socio = api.socio()
    api.prestar_ok(socio["id"], api.libro()["id"])
    reloj.avanzar(90)

    assert api.prestar(socio["id"], api.libro()["id"]).status_code == 201


# ------------------------------------------- GET /socios/{id}/prestamos


def preparar_socio_con_prestamos(api: Api) -> tuple[dict[str, int], list[int]]:
    """Un socio con 4 préstamos, de los cuales el 1.º y el 2.º están devueltos.

    Devuelve el socio y los ids de sus préstamos en orden de alta.
    """
    socio = api.socio()
    ids = [
        api.prestar_ok(socio["id"], api.libro(stock=9)["id"])["id"] for _ in range(3)
    ]
    api.devolver(ids[0])
    api.devolver(ids[1])
    ids.append(api.prestar_ok(socio["id"], api.libro(stock=9)["id"])["id"])
    return socio, ids


def test_listar_prestamos_del_socio_sin_filtro_devuelve_todos_ordenados(
    api: Api,
) -> None:
    socio, ids = preparar_socio_con_prestamos(api)

    respuesta = api.cliente.get(f"/socios/{socio['id']}/prestamos")

    assert respuesta.status_code == 200
    assert [p["id"] for p in respuesta.json()] == ids
    assert all(p["socio_id"] == socio["id"] for p in respuesta.json())


def test_listar_prestamos_activos_true_devuelve_solo_los_no_devueltos(
    api: Api,
) -> None:
    socio, ids = preparar_socio_con_prestamos(api)

    respuesta = api.cliente.get(f"/socios/{socio['id']}/prestamos?activos=true")

    assert [p["id"] for p in respuesta.json()] == [ids[2], ids[3]]
    assert all(p["fecha_devolucion"] is None for p in respuesta.json())


def test_listar_prestamos_activos_false_devuelve_solo_los_devueltos(api: Api) -> None:
    socio, ids = preparar_socio_con_prestamos(api)

    respuesta = api.cliente.get(f"/socios/{socio['id']}/prestamos?activos=false")

    assert [p["id"] for p in respuesta.json()] == [ids[0], ids[1]]
    assert all(p["fecha_devolucion"] is not None for p in respuesta.json())


def test_listar_prestamos_no_mezcla_los_de_otros_socios(api: Api) -> None:
    socio, _ = preparar_socio_con_prestamos(api)
    otro = api.socio()
    api.prestar_ok(otro["id"], api.libro()["id"])

    propios = api.cliente.get(f"/socios/{socio['id']}/prestamos").json()
    ajenos = api.cliente.get(f"/socios/{otro['id']}/prestamos").json()

    assert len(propios) == 4
    assert len(ajenos) == 1


def test_listar_prestamos_se_pagina_sobre_lo_ya_filtrado(api: Api) -> None:
    socio, ids = preparar_socio_con_prestamos(api)

    pagina = api.cliente.get(f"/socios/{socio['id']}/prestamos?skip=1&limit=2").json()
    filtrada = api.cliente.get(
        f"/socios/{socio['id']}/prestamos?activos=true&skip=1&limit=1"
    ).json()
    vacia = api.cliente.get(f"/socios/{socio['id']}/prestamos?skip=100").json()

    assert [p["id"] for p in pagina] == ids[1:3]
    assert [p["id"] for p in filtrada] == [ids[3]]
    assert vacia == []


def test_un_socio_sin_prestamos_devuelve_lista_vacia(api: Api) -> None:
    socio = api.socio()

    respuesta = api.cliente.get(f"/socios/{socio['id']}/prestamos?activos=true")

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_listar_prestamos_de_un_socio_inexistente_da_404(api: Api) -> None:
    respuesta = api.cliente.get("/socios/9999/prestamos")

    assert respuesta.status_code == 404
    assert "Socio" in respuesta.json()["detail"]


@pytest.mark.parametrize(
    ("consulta", "codigo"),
    [
        ("activos=1", 200),
        ("activos=0", 200),
        ("activos=TRUE", 200),
        ("activos=maybe", 422),
        ("activos=", 422),
        ("limit=0", 422),
        ("limit=101", 422),
        ("skip=-1", 422),
        (f"skip={10**30}", 422),
    ],
)
def test_listar_prestamos_valida_sus_parametros(
    api: Api, consulta: str, codigo: int
) -> None:
    socio = api.socio()

    respuesta = api.cliente.get(f"/socios/{socio['id']}/prestamos?{consulta}")

    assert respuesta.status_code == codigo


def test_el_listado_calcula_vencido_con_la_fecha_de_hoy(api: Api, reloj: Reloj) -> None:
    socio, _ = preparar_socio_con_prestamos(api)
    reloj.avanzar(30)

    activos = api.cliente.get(f"/socios/{socio['id']}/prestamos?activos=true").json()
    devueltos = api.cliente.get(f"/socios/{socio['id']}/prestamos?activos=false").json()

    assert all(p["vencido"] and p["dias_atraso"] > 0 for p in activos)
    assert not any(p["vencido"] for p in devueltos)
