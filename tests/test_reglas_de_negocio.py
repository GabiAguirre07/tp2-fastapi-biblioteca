"""Reglas de negocio de la consigna: un caso feliz y uno de error por regla.

Cada test lleva el número de la regla en su nombre (test_regla_1_...), tal
como figura en la tabla «Reglas de negocio» de la consigna. Así se puede
recorrer este archivo con la consigna al lado y ver que no falta ninguna.
Los casos borde de cada regla están en los archivos de cada entidad.
"""

from datetime import timedelta

from tests.ayudas import Api, Reloj

# ---------------------------------------------------------------------------
# Regla 1: un socio no puede tener más de 3 préstamos activos (409)
# ---------------------------------------------------------------------------


def test_regla_1_feliz_el_tercer_prestamo_activo_se_concede(api: Api) -> None:
    socio = api.socio()
    for _ in range(2):
        api.prestar_ok(socio["id"], api.libro(stock=5)["id"])

    respuesta = api.prestar(socio["id"], api.libro(stock=5)["id"])

    assert respuesta.status_code == 201


def test_regla_1_error_el_cuarto_prestamo_activo_da_409(api: Api) -> None:
    socio = api.socio()
    for _ in range(3):
        api.prestar_ok(socio["id"], api.libro(stock=5)["id"])
    cuarto_libro = api.libro(stock=5)

    respuesta = api.prestar(socio["id"], cuarto_libro["id"])

    assert respuesta.status_code == 409
    assert "3 préstamos activos" in respuesta.json()["detail"]
    assert api.stock(cuarto_libro["id"]) == 5  # el rechazo no descontó stock


# ---------------------------------------------------------------------------
# Regla 2: sin stock no se presta (409); al prestar se descuenta 1
# ---------------------------------------------------------------------------


def test_regla_2_feliz_prestar_descuenta_1_del_stock(api: Api) -> None:
    libro = api.libro(stock=2)

    respuesta = api.prestar(api.socio()["id"], libro["id"])

    assert respuesta.status_code == 201
    assert api.stock(libro["id"]) == 1


def test_regla_2_error_un_libro_sin_stock_no_se_presta_409(api: Api) -> None:
    libro = api.libro(stock=0)

    respuesta = api.prestar(api.socio()["id"], libro["id"])

    assert respuesta.status_code == 409
    assert "ejemplares" in respuesta.json()["detail"]
    assert api.stock(libro["id"]) == 0  # nunca queda negativo


# ---------------------------------------------------------------------------
# Regla 3: un socio inactivo no puede pedir préstamos (403)
# ---------------------------------------------------------------------------


def test_regla_3_feliz_un_socio_activo_puede_pedir_prestamos(api: Api) -> None:
    respuesta = api.prestar(api.socio(activo=True)["id"], api.libro()["id"])

    assert respuesta.status_code == 201


def test_regla_3_error_un_socio_inactivo_recibe_403(api: Api) -> None:
    socio = api.socio(activo=False)
    libro = api.libro(stock=2)

    respuesta = api.prestar(socio["id"], libro["id"])

    assert respuesta.status_code == 403
    assert "inactivo" in respuesta.json()["detail"]
    assert api.stock(libro["id"]) == 2


# ---------------------------------------------------------------------------
# Regla 4: el plazo es de 14 días (no tiene caso de error: la consigna dice n/a)
# ---------------------------------------------------------------------------


def test_regla_4_el_vencimiento_es_la_fecha_del_prestamo_mas_14_dias(
    api: Api, reloj: Reloj
) -> None:
    prestamo = api.prestar_ok(api.socio()["id"], api.libro()["id"])

    assert prestamo["fecha_prestamo"] == reloj.hoy.isoformat()
    vencimiento = reloj.hoy + timedelta(days=14)
    assert prestamo["fecha_vencimiento"] == vencimiento.isoformat()


# ---------------------------------------------------------------------------
# Regla 5: al devolver se repone el stock y se calcula la multa ($100 por día
# de atraso, 0 si llegó a tiempo). No tiene código de error: la consigna dice n/a
# ---------------------------------------------------------------------------


def test_regla_5_feliz_devolver_a_tiempo_repone_stock_y_no_cobra_multa(
    api: Api, reloj: Reloj
) -> None:
    libro = api.libro(stock=1)
    prestamo = api.prestar_ok(api.socio()["id"], libro["id"])
    assert api.stock(libro["id"]) == 0
    reloj.avanzar(14)  # justo el día del vencimiento: todavía a tiempo

    respuesta = api.devolver(prestamo["id"])

    assert respuesta.status_code == 200
    assert respuesta.json()["multa"] == 0
    assert respuesta.json()["fecha_devolucion"] == "2026-03-24"
    assert api.stock(libro["id"]) == 1


def test_regla_5_con_atraso_la_multa_es_100_por_dia(api: Api, reloj: Reloj) -> None:
    libro = api.libro(stock=1)
    prestamo = api.prestar_ok(api.socio()["id"], libro["id"])
    reloj.avanzar(14 + 3)  # tres días después del vencimiento

    respuesta = api.devolver(prestamo["id"])

    assert respuesta.status_code == 200
    assert respuesta.json()["multa"] == 300
    assert api.stock(libro["id"]) == 1


# ---------------------------------------------------------------------------
# Regla 6: no se puede devolver un préstamo ya devuelto (409)
# ---------------------------------------------------------------------------


def test_regla_6_feliz_la_primera_devolucion_se_acepta(api: Api) -> None:
    prestamo = api.prestar_ok(api.socio()["id"], api.libro()["id"])

    respuesta = api.devolver(prestamo["id"])

    assert respuesta.status_code == 200
    assert respuesta.json()["fecha_devolucion"] is not None


def test_regla_6_error_devolver_dos_veces_da_409_y_no_repone_dos_veces(
    api: Api,
) -> None:
    libro = api.libro(stock=1)
    prestamo = api.prestar_ok(api.socio()["id"], libro["id"])
    api.devolver(prestamo["id"])

    respuesta = api.devolver(prestamo["id"])

    assert respuesta.status_code == 409
    assert "ya fue devuelto" in respuesta.json()["detail"]
    assert api.stock(libro["id"]) == 1  # repuesto una sola vez


# ---------------------------------------------------------------------------
# Regla 7: recurso inexistente (404)
# ---------------------------------------------------------------------------


def test_regla_7_feliz_los_recursos_existentes_se_consultan_con_200(api: Api) -> None:
    autor, libro, socio = api.autor(), api.libro(), api.socio()
    prestamo = api.prestar_ok(socio["id"], libro["id"])

    assert api.cliente.get(f"/autores/{autor['id']}").status_code == 200
    assert api.cliente.get(f"/libros/{libro['id']}").status_code == 200
    assert api.cliente.get(f"/socios/{socio['id']}").status_code == 200
    assert api.cliente.get(f"/prestamos/{prestamo['id']}").status_code == 200


def test_regla_7_error_los_recursos_inexistentes_dan_404(api: Api) -> None:
    cliente = api.cliente
    socio, libro = api.socio(), api.libro()

    assert cliente.get("/autores/9999").status_code == 404
    assert cliente.get("/libros/9999").status_code == 404
    assert cliente.get("/socios/9999").status_code == 404
    assert cliente.get("/prestamos/9999").status_code == 404
    assert cliente.patch("/libros/9999", json={"stock": 1}).status_code == 404
    assert cliente.delete("/socios/9999").status_code == 404
    assert api.prestar(9999, libro["id"]).status_code == 404  # socio inexistente
    assert api.prestar(socio["id"], 9999).status_code == 404  # libro inexistente
    assert api.devolver(9999).status_code == 404  # préstamo inexistente
    assert cliente.post(f"/libros/{libro['id']}/autores/9999").status_code == 404
    assert cliente.get("/socios/9999/prestamos").status_code == 404


# ---------------------------------------------------------------------------
# Regla 8: ISBN o email duplicado (409)
# ---------------------------------------------------------------------------


def test_regla_8_feliz_isbn_y_email_distintos_se_aceptan(api: Api) -> None:
    cliente = api.cliente

    for isbn in ("9780306406157", "9780131103627"):
        libro = {"titulo": "Libro", "isbn": isbn, "stock": 1, "anio": 2000}
        assert cliente.post("/libros", json=libro).status_code == 201
    for email in ("ana@example.com", "beto@example.com"):
        socio = {"nombre": "Socio", "email": email}
        assert cliente.post("/socios", json=socio).status_code == 201


def test_regla_8_error_un_isbn_repetido_da_409(api: Api) -> None:
    libro = api.libro()

    respuesta = api.cliente.post(
        "/libros",
        json={"titulo": "Otro", "isbn": libro["isbn"], "stock": 1, "anio": 2000},
    )

    assert respuesta.status_code == 409
    assert "ISBN" in respuesta.json()["detail"]


def test_regla_8_error_un_email_repetido_da_409_sin_importar_mayusculas(
    api: Api,
) -> None:
    socio = api.socio()

    respuesta = api.cliente.post(
        "/socios", json={"nombre": "Otro", "email": socio["email"].upper()}
    )

    assert respuesta.status_code == 409
    assert "email" in respuesta.json()["detail"]
