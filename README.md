# TP N°2 Python — Sistema de Biblioteca

API REST para gestionar el catálogo de una biblioteca (autores, libros y socios) y sus préstamos, con las reglas de negocio de la consigna y los roles opcionales `bibliotecario` y `socio`. Está hecha con **FastAPI** y **SQLModel** sobre **SQLite**.

**Para evaluar:** instalar y ejecutar (abajo), abrir `/docs` y seguir el [recorrido de 5 minutos](#probar-en-5-minutos-desde-docs). El mapa punto por punto de la consigna y la rúbrica está en [docs/cumplimiento-de-la-consigna.md](docs/cumplimiento-de-la-consigna.md).

## Requisitos

- **Python 3.10 o superior**.
- `pip` (viene con Python). No hace falta instalar ni configurar ningún servidor de base de datos: SQLite ya viene incluido en Python.

## Instalación y ejecución

Los comandos se ejecutan desde la carpeta del proyecto. Los dos primeros pasos cambian según la terminal.

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación por la política de ejecución, habilitarla solo para esa ventana con
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` y volver a activar.

**Linux / macOS (bash o zsh)**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Luego, en cualquiera de los dos sistemas**

```bash
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Con la aplicación en marcha, abrir <http://127.0.0.1:8000/docs> (Swagger). El archivo `biblioteca.db` se crea solo, junto al código, la primera vez que arranca: no hace falta ningún paso manual ni variables de entorno. Para detener la aplicación: `Ctrl + C`.

**Para empezar con datos vacíos:** detener la aplicación y borrar `biblioteca.db` (`Remove-Item biblioteca.db` en PowerShell, `rm biblioteca.db` en bash). Se vuelve a crear al arrancar.

## Probar en 5 minutos desde `/docs`

**1. Identificarse.** Pulsar **Authorize** (arriba a la derecha), escribir `bibliotecario` en el campo `Rol`, dejar `SocioId` vacío y pulsar *Authorize*. Sin este paso, los endpoints de escritura responden 401; el catálogo (`GET` de autores y libros) se puede consultar sin identificarse.

**2. Cargar datos** (con `Try it out` en cada endpoint, en este orden):

| # | Llamada | Cuerpo | Responde |
|---|---|---|---|
| 1 | `POST /autores` | `{"nombre":"Jorge Luis Borges","nacionalidad":"Argentina"}` | 201 |
| 2 | `POST /libros` | `{"titulo":"El Aleph","isbn":"9788499089515","stock":1,"anio":1949}` | 201 |
| 3 | `POST /libros/1/autores/1` | — | 201, el libro con su autor |
| 4 | `POST /socios` | `{"nombre":"Ana Perez","email":"ana@example.com"}` | 201 |
| 5 | `POST /socios` | `{"nombre":"Beto Gomez","email":"beto@example.com","activo":false}` | 201 |

**3. Reglas de negocio:**

| # | Llamada | Responde | Regla |
|---|---|---|---|
| 6 | `POST /prestamos` con `{"socio_id":1,"libro_id":1}` | 201, vence a los 14 días | 2 y 4 |
| 7 | el mismo pedido otra vez | 409, sin stock | 2 |
| 8 | `POST /prestamos` con `{"socio_id":2,"libro_id":1}` | 403, socio inactivo | 3 |
| 9 | `POST /prestamos` con `{"socio_id":99,"libro_id":1}` | 404 | 7 |
| 10 | `POST /libros` con el mismo ISBN | 409 | 8 |
| 11 | `POST /prestamos/1/devolucion` | 200, multa 0, el stock vuelve a 1 | 5 |
| 12 | la misma devolución otra vez | 409 | 6 |
| 13 | `GET /socios/1/prestamos?activos=true` | 200, lista vacía | — |

La regla 1 (máximo de 3 préstamos activos) se ve cargando un libro con `stock` 5 y pidiéndolo cuatro veces para el socio 1: la cuarta responde 409.

**4. Roles.** Cerrar sesión en *Authorize* y entrar con `Rol` = `socio` y `SocioId` = `1`: puede ver sus préstamos (`GET /socios/1/prestamos`, `GET /prestamos/1`) pero recibe 403 en `GET /socios/2/prestamos`, `GET /socios` y `POST /prestamos`.

**5. La multa con atraso.** La fecha de los préstamos la decide el servidor, así que una multa mayor a 0 no se puede producir el mismo día desde Swagger. Se comprueba con los tests, que reemplazan la fecha de «hoy»:

```bash
python -m pytest tests/test_reglas_de_negocio.py -k "regla_4 or regla_5" -v --no-cov
```

## Roles (parte opcional de la consigna)

| Rol | Qué puede hacer |
|---|---|
| Sin credenciales | Consultar el catálogo (`GET` de autores y libros) y la documentación. Todo lo demás: 401 |
| `socio` | El catálogo y **únicamente sus propios préstamos** (`GET /socios/{su id}/prestamos` y `GET /prestamos/{id}` de un préstamo suyo). El resto: 403 |
| `bibliotecario` | Todo: administra el catálogo y los socios, registra préstamos y devoluciones y consulta cualquier préstamo |

**La identificación es simulada:** se hace con los encabezados `X-Rol` y `X-Socio-Id` (el botón *Authorize* los envía solos) y el servidor cree lo que el cliente declara; no hay contraseñas ni tokens. Es una decisión consciente para poder probar los permisos en un clic; la autorización (qué puede hacer cada rol) sí se aplica de verdad. Con `curl`:

```bash
curl -H "X-Rol: bibliotecario" http://127.0.0.1:8000/socios
curl -H "X-Rol: socio" -H "X-Socio-Id: 1" http://127.0.0.1:8000/socios/1/prestamos
```

Pasar a un mecanismo real (por ejemplo JWT) solo exigiría cambiar `identificar_usuario` y `obtener_usuario`; ver [docs/decisiones-de-diseno.md](docs/decisiones-de-diseno.md).

## Endpoints

Cada recurso (`/autores`, `/libros`, `/socios`) ofrece alta (`POST`), listado (`GET`), consulta por id (`GET /{id}`), modificación parcial (`PATCH /{id}`) y baja (`DELETE /{id}`). **La modificación es solo con `PATCH`** (no hay `PUT`): se envían únicamente los campos a cambiar. El listado admite `?skip=0&limit=100` (máximo 100) y viene ordenado por id.

| Endpoint | Qué hace | Quién | Códigos |
|---|---|---|---|
| `POST /libros/{id}/autores/{autor_id}` | Asocia un autor a un libro | bibliotecario | 201, 404, 409 (ya asociados) |
| `GET /libros?disponibles=true` | Libros con stock mayor a 0 (`false`: agotados) | público | 200, 422 |
| `POST /prestamos` | Registra un préstamo y descuenta 1 del stock | bibliotecario | 201, 403, 404, 409 |
| `POST /prestamos/{id}/devolucion` | Registra la devolución, repone el stock y calcula la multa | bibliotecario | 200, 404, 409 |
| `GET /socios/{id}/prestamos?activos=true` | Préstamos del socio (`activos=true` sin devolver, `false` devueltos) | bibliotecario o el propio socio | 200, 403, 404 |

Endpoints que **la consigna no pide** y se agregaron: `DELETE /libros/{id}/autores/{autor_id}` (desasociar), `GET /autores/{id}/libros` y `GET /prestamos/{id}`. También se agregaron los campos calculados `vencido` y `dias_atraso` en cada préstamo (informan, no bloquean nada).

Códigos: **201** alta, **200** consulta y modificación, **204** baja, **401** sin identificar, **403** sin permiso o socio inactivo, **404** no existe, **409** conflicto (duplicado, regla de préstamo incumplida o borrado no permitido) y **422** datos inválidos.

**Aviso para las pruebas:** al cargar un socio, usar un email con un dominio normal o de ejemplo (`ana@example.com`). Los dominios reservados como `.test`, `.local` o `localhost` se rechazan con 422.

## Tests y chequeos de calidad

Con el entorno virtual activado:

```bash
pip install -r requirements-dev.txt
python -m pytest --cov
python -m pycodestyle .
python -m pyright
```

- `pytest --cov` ejecuta todos los tests (reglas de negocio con caso feliz y de error, CRUD, relaciones, roles y concurrencia) y muestra la cobertura por archivo. Debe terminar con `passed` y `Required test coverage of 80.0% reached`; la cobertura supera ampliamente ese mínimo. Si bajara de 80 %, el comando falla.
- `pycodestyle` no debe imprimir nada. Su límite de línea es de 88 caracteres (no los 79 de PEP 8), configurado en `setup.cfg` para coincidir con el formateador usado.
- `pyright` debe terminar con `0 errors`. La primera vez descarga componentes y necesita conexión a internet.

Los tests usan una base SQLite **en memoria** y una fecha de «hoy» controlada: no tocan `biblioteca.db` y no dependen del día en que se ejecuten. Más detalle en [docs/como-verificar.md](docs/como-verificar.md).

## Estructura

`models/` (tablas y esquemas), `routers/` (HTTP), `services/` (reglas de negocio, sin conocer HTTP) y `tests/`, como sugiere la consigna. Detalle en [docs/estructura-del-proyecto.md](docs/estructura-del-proyecto.md).

## Documentación

| Documento | Contenido |
|---|---|
| [docs/cumplimiento-de-la-consigna.md](docs/cumplimiento-de-la-consigna.md) | Cada punto de la consigna y la rúbrica: dónde está implementado y qué test lo comprueba |
| [docs/modelo-de-datos.md](docs/modelo-de-datos.md) | Tablas, campos, restricciones y diagrama entidad-relación |
| [docs/decisiones-de-diseno.md](docs/decisiones-de-diseno.md) | Decisiones que la consigna no fija, con su fundamento |
| [docs/estructura-del-proyecto.md](docs/estructura-del-proyecto.md) | Carpetas, archivos y responsabilidad de cada uno |
| [docs/como-verificar.md](docs/como-verificar.md) | Qué comprobar en cada etapa y cómo hacerlo |
