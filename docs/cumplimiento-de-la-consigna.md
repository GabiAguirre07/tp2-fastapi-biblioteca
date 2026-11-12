# Cumplimiento de la consigna

Mapa de cada punto de la consigna y de la rúbrica: dónde está implementado y qué test lo comprueba. Para correr los tests de un punto: `python -m pytest <archivo> -k <fragmento del nombre> -v --no-cov`.

## 1. Modelo y relaciones (20 pts)

| Consigna | Implementación | Tests |
|---|---|---|
| Entidades `Autor`, `Libro`, `LibroAutor`, `Socio`, `Prestamo` con los campos de la consigna | `models/autores.py`, `libros.py`, `libro_autor.py`, `socios.py`, `prestamos.py` | `tests/test_modelos.py::test_las_tablas_tienen_las_columnas_de_la_consigna` |
| `isbn` único | `Libro.isbn` (restricción `UNIQUE`) | `test_la_base_rechaza_un_isbn_repetido` |
| `email` único | `Socio.email` (restricción `UNIQUE`) | `test_la_base_rechaza_un_email_repetido` |
| `stock` ≥ 0 | `CHECK` en la tabla `libro` y validación en el esquema | `test_la_base_rechaza_un_stock_negativo` |
| `fecha_devolucion` admite nulo; el resto no | `Prestamo` | `test_solo_la_fecha_de_devolucion_admite_nulo_en_prestamo` |
| Libro N-N Autor | tabla `LibroAutor` con clave primaria compuesta | `test_la_relacion_libro_autor_se_navega_en_los_dos_sentidos`, `test_la_base_rechaza_asociar_dos_veces_el_mismo_autor_al_mismo_libro` |
| Préstamo N-1 Socio y N-1 Libro | claves foráneas activadas en cada conexión (`database.py`) | `test_un_prestamo_conoce_a_su_socio_y_a_su_libro_y_viceversa`, `test_las_claves_foraneas_estan_activadas` |

Diagrama y detalle en [modelo-de-datos.md](modelo-de-datos.md).

## 2. Endpoints y códigos HTTP (20 pts)

| Endpoint de la consigna | Dónde | Códigos | Tests |
|---|---|---|---|
| CRUD `/autores` | `routers/autores.py`, `services/autores.py` | 201, 200, 204, 404, 409, 422 | `tests/test_autores.py` |
| CRUD `/libros` | `routers/libros.py`, `services/libros.py` | 201, 200, 204, 404, 409, 422 | `tests/test_libros.py` |
| CRUD `/socios` | `routers/socios.py`, `services/socios.py` | 201, 200, 204, 404, 409, 422 | `tests/test_socios.py` |
| `POST /libros/{id}/autores/{autor_id}` | `routers/libros.py`, `services/libros.py` | 201, 404, 409 | `test_asociar_autor_devuelve_201_con_el_libro_y_sus_autores`, `test_asociar_dos_veces_el_mismo_autor_da_409_y_no_duplica` |
| `GET /libros?disponibles=true` | `services/libros.py` (filtro en SQL) | 200, 422 | `test_filtro_disponibles_true_lista_solo_los_que_tienen_stock` |
| `POST /prestamos` | `routers/prestamos.py`, `services/prestamos.py::crear_prestamo` | 201, 403, 404, 409 | `tests/test_prestamos.py`, reglas 1 a 4 |
| `POST /prestamos/{id}/devolucion` | `services/prestamos.py::devolver_prestamo` | 200, 404, 409 | `tests/test_prestamos.py`, reglas 5 y 6 |
| `GET /socios/{id}/prestamos?activos=true` | `routers/socios.py`, `services/prestamos.py::listar_prestamos_de_socio` | 200, 403, 404 | `test_listar_prestamos_activos_true_devuelve_solo_los_no_devueltos` |

Las respuestas de error están documentadas en Swagger (`responses=` en cada endpoint) y los errores de negocio se traducen a su código en un solo lugar, `routers/manejadores.py`.

## 3. Reglas de negocio (25 pts)

Todas viven en `services/`, no en los routers. Los tests están en `tests/test_reglas_de_negocio.py` (caso feliz y de error de cada regla, con el número de la regla en el nombre): `python -m pytest tests/test_reglas_de_negocio.py -v --no-cov`.

| # | Regla | Dónde | Test (caso feliz / caso de error) |
|---|---|---|---|
| 1 | Máximo 3 préstamos activos → 409 | `crear_prestamo`, constante `MAXIMO_ACTIVOS` | `test_regla_1_feliz_el_tercer_prestamo_activo_se_concede` / `test_regla_1_error_el_cuarto_prestamo_activo_da_409` |
| 2 | Sin stock no se presta → 409; al prestar se descuenta 1 | `crear_prestamo` (`UPDATE` condicional del stock) | `test_regla_2_feliz_prestar_descuenta_1_del_stock` / `test_regla_2_error_un_libro_sin_stock_no_se_presta_409` |
| 3 | Socio inactivo no pide → 403 | `crear_prestamo` | `test_regla_3_feliz_un_socio_activo_puede_pedir_prestamos` / `test_regla_3_error_un_socio_inactivo_recibe_403` |
| 4 | Vencimiento = préstamo + 14 días | constante `PLAZO_DIAS` | `test_regla_4_el_vencimiento_es_la_fecha_del_prestamo_mas_14_dias` |
| 5 | Al devolver se repone el stock y la multa es $100 × días de atraso (0 si llegó a tiempo) | `devolver_prestamo`, `calcular_multa`, constante `MULTA_POR_DIA` | `test_regla_5_feliz_devolver_a_tiempo_repone_stock_y_no_cobra_multa` / `test_regla_5_con_atraso_la_multa_es_100_por_dia`; además multas de −5 a 366 días en `tests/test_prestamos.py` |
| 6 | No se devuelve dos veces → 409 | `devolver_prestamo` | `test_regla_6_feliz_la_primera_devolucion_se_acepta` / `test_regla_6_error_devolver_dos_veces_da_409_y_no_repone_dos_veces` |
| 7 | Recurso inexistente → 404 | `services/comunes.py::obtener_o_404` | `test_regla_7_feliz_los_recursos_existentes_se_consultan_con_200` / `test_regla_7_error_los_recursos_inexistentes_dan_404` |
| 8 | ISBN o email duplicado → 409 | restricción `UNIQUE` y `services/comunes.py::guardar` | `test_regla_8_feliz_isbn_y_email_distintos_se_aceptan` / `test_regla_8_error_un_isbn_repetido_da_409`, `test_regla_8_error_un_email_repetido_da_409_sin_importar_mayusculas` |

**Cómo se ve la multa con atraso:** la fecha de los préstamos la decide el servidor, así que la multa mayor a 0 no se produce el mismo día desde Swagger. Los tests reemplazan la fecha de «hoy» (`dependency_overrides[obtener_fecha_hoy]`): `python -m pytest tests/test_reglas_de_negocio.py -k "regla_4 or regla_5" -v --no-cov`.

**Pedidos simultáneos:** el stock y el máximo de 3 se protegen con un `UPDATE` condicional dentro de una transacción; `tests/test_concurrencia.py` lo prueba con 12 hilos.

## 4. Tests y cobertura (20 pts)

| Consigna | Cómo se cumple |
|---|---|
| pytest con base en memoria | fixture automática `motor` en `tests/conftest.py`: SQLite en memoria, nueva en cada test; ningún test toca `biblioteca.db` |
| Cada regla, caso feliz y de error | `tests/test_reglas_de_negocio.py` (tabla anterior) |
| Cobertura ≥ 80 % | `python -m pytest --cov` mide `main`, `database`, `models`, `routers` y `services`; `fail_under = 80` en `setup.cfg` hace fallar el comando si baja. La cobertura real es superior al 99 % |
| Además | CRUD de cada entidad, relaciones, roles y permisos, concurrencia y arranque de la aplicación |

## 5. Estructura y claridad del código (15 pts)

| Aspecto | Cómo se cumple |
|---|---|
| Carpetas `models/`, `routers/`, `services/`, `tests/` | tal cual la consigna |
| Reglas de negocio fuera del router | los routers solo reciben el pedido, llaman al servicio y devuelven el resultado; los servicios no conocen HTTP |
| Sin duplicación | paginación, respuestas de error, `obtener_o_404`, `guardar` y `transaccion` se escriben una vez y se reutilizan |
| Claridad | docstrings en español en cada módulo, clase y función; `pycodestyle` y `pyright` sin errores |
| Entrega | README con instalación (PowerShell y bash), ejecución y tests |

Detalle de capas y dependencias en [estructura-del-proyecto.md](estructura-del-proyecto.md) y decisiones en [decisiones-de-diseno.md](decisiones-de-diseno.md).

## 6. Opcional: roles `bibliotecario` y `socio`

| Consigna | Cómo se cumple | Tests |
|---|---|---|
| Solo el bibliotecario administra el catálogo | los `POST`, `PATCH` y `DELETE` de autores, libros y la asociación de autores exigen el rol (403 a un socio, 401 sin identificar) | `test_un_socio_no_puede_usar_los_endpoints_del_bibliotecario`, `test_sin_credenciales_los_endpoints_del_bibliotecario_dan_401` |
| El socio ve únicamente sus préstamos | `GET /socios/{id}/prestamos` y `GET /prestamos/{id}` solo para el bibliotecario o el socio dueño; el resto, 403 | `test_un_socio_ve_sus_propios_prestamos`, `test_un_socio_no_ve_los_prestamos_de_otro_socio`, `test_un_socio_consulta_un_prestamo_propio_pero_no_uno_ajeno` |

Todos en `tests/test_seguridad.py`. **Alcance y límite:** la autorización es real, pero la identificación es simulada con los encabezados `X-Rol` y `X-Socio-Id` (sin contraseñas ni tokens), decisión 104.

## 7. Qué se agregó fuera de la consigna

- Endpoints: `DELETE /libros/{id}/autores/{autor_id}`, `GET /autores/{id}/libros` y `GET /prestamos/{id}`.
- Campos calculados `vencido` y `dias_atraso` en los préstamos (informan; no bloquean).
- Paginación `?skip=&limit=` en los listados.
- Validaciones de formato (ISBN de 10 o 13 dígitos, email, largos de texto, año entre 1450 y el actual).
- Control de concurrencia de stock y máximo de préstamos.

## 8. Limitaciones conocidas

| Limitación | Detalle |
|---|---|
| Identificación simulada | cualquiera puede declararse bibliotecario (decisión 104); pasar a JWT solo exige cambiar `identificar_usuario` y `obtener_usuario` |
| Solo `PATCH` | no hay `PUT` para modificar (decisión 26) |
| Multa con atraso | no reproducible desde Swagger el mismo día; se comprueba con los tests (decisión 60) |
| Emails reservados | dominios como `.test`, `.local` o `localhost` dan 422; usar `example.com` |
| Concurrencia | las garantías son las de SQLite (decisión 61) |
| 401 sin `WWW-Authenticate` | desvío del estándar HTTP, sin efecto en Swagger ni en `curl` (decisión 105) |
| `pycodestyle` a 88 columnas | PEP 8 recomienda 79; se configuró 88 (decisión 14) |
