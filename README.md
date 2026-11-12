# TP N°2 Python — Sistema de Biblioteca

API REST para gestionar el catálogo de una biblioteca (autores, libros y socios) y sus préstamos. Está desarrollada con **FastAPI** y **SQLModel** sobre **SQLite** para el Trabajo Práctico N°2.

## Estado del desarrollo

| Etapa | Contenido | Estado |
|---|---|---|
| 0 | Repositorio y entorno | Finalizada |
| 1 | Modelos y base de datos | Finalizada |
| 2 | CRUD de Autor, Libro y Socio | Finalizada |
| 3 | Relaciones y consultas | Finalizada |
| 4 | Préstamos y reglas de negocio | Finalizada |
| 5 | Tests y cobertura | Pendiente |
| 6 | README final y entrega | Pendiente |

Hoy la aplicación crea la base de datos con las cinco tablas, expone el CRUD completo de autores, libros y socios, permite asociar autores a los libros y filtrar los libros disponibles, y registra préstamos y devoluciones aplicando las reglas de negocio (máximo de préstamos, stock, socio inactivo, vencimiento y multa).

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

Con la aplicación en marcha, abrir <http://127.0.0.1:8000/docs> para ver Swagger. El archivo `biblioteca.db` se crea solo, junto al código, la primera vez que arranca (no hace falta ningún paso manual ni variables de entorno).

Para detener la aplicación: `Ctrl + C`.

## Endpoints disponibles

Cada recurso ofrece alta (`POST`), listado (`GET`), consulta por id (`GET /{id}`), modificación parcial (`PATCH /{id}`) y baja (`DELETE /{id}`). El listado admite paginación con `?skip=0&limit=100` (máximo 100) y viene ordenado por id.

| Recurso | Reglas destacadas |
|---|---|
| `/autores` | Nombre y nacionalidad obligatorios. No se puede borrar un autor con libros asociados (409). |
| `/libros` | El ISBN es único (409) y se guarda sin guiones. Stock mayor o igual a 0 y año entre 1450 y el año actual. Toda respuesta incluye los autores del libro. El listado admite `?disponibles=true` (con stock) o `?disponibles=false` (agotados). No se puede borrar un libro con préstamos (409). |
| `/socios` | El email es único sin distinguir mayúsculas (409) y se guarda en minúsculas. No se puede borrar un socio con préstamos (409). |

### Relación entre libros y autores

| Endpoint | Qué hace | Códigos |
|---|---|---|
| `POST /libros/{libro_id}/autores/{autor_id}` | Asocia un autor a un libro y devuelve el libro con todos sus autores | 201, 404 (libro o autor inexistente), 409 (ya estaban asociados) |
| `DELETE /libros/{libro_id}/autores/{autor_id}` | Quita la asociación | 204, 404 (libro, autor o asociación inexistente) |
| `GET /autores/{autor_id}/libros` | Lista paginada de los libros de un autor | 200, 404 |

Los dos últimos no los pide la consigna: se agregaron para poder deshacer una asociación y para ver qué libros impiden borrar un autor.

### Préstamos

| Endpoint | Qué hace | Códigos |
|---|---|---|
| `POST /prestamos` | Registra un préstamo (`{"socio_id": 1, "libro_id": 1}`): descuenta 1 del stock y fija el vencimiento a 14 días | 201, 403 (socio inactivo), 404 (socio o libro inexistente), 409 (3 préstamos activos o libro sin stock), 422 |
| `POST /prestamos/{prestamo_id}/devolucion` | Registra la devolución: repone 1 al stock y calcula la multa | 200, 404, 409 (ya estaba devuelto) |
| `GET /socios/{socio_id}/prestamos` | Lista paginada de los préstamos del socio. `?activos=true` solo los no devueltos, `?activos=false` solo los devueltos, sin el parámetro todos | 200, 404, 422 |
| `GET /prestamos/{prestamo_id}` | Consulta un préstamo (no lo pide la consigna) | 200, 404 |

Las fechas las decide el servidor (el cliente no las envía). La multa es de **$100 por cada día de atraso** respecto del vencimiento. Cada préstamo se devuelve con dos datos calculados al responder, `vencido` y `dias_atraso`, que informan pero **no bloquean** nada.

Códigos de respuesta: **201** alta, **200** consulta y modificación, **204** baja, **403** el socio no está habilitado (inactivo), **404** el recurso no existe, **409** conflicto (duplicado, asociación repetida, regla de préstamo incumplida o borrado no permitido) y **422** datos inválidos.

**Para probar desde Swagger:** al cargar un socio, usar un email con un dominio real o de ejemplo (`ana@example.com`). Los dominios reservados como `.test`, `.local` o `localhost` se rechazan con 422.

## Chequeos de calidad (desarrollo)

Con el entorno virtual activado:

```bash
pip install -r requirements-dev.txt
python -m pycodestyle .
python -m pyright
```

`pycodestyle` no debe imprimir nada y `pyright` debe terminar con `0 errors`. La configuración de `pycodestyle` está en `setup.cfg` (líneas de hasta 88 caracteres).

Los tests (`pytest`) se incorporan en la Etapa 5.

## Documentación

| Documento | Contenido |
|---|---|
| [docs/modelo-de-datos.md](docs/modelo-de-datos.md) | Tablas, campos, restricciones y diagrama entidad-relación |
| [docs/decisiones-de-diseno.md](docs/decisiones-de-diseno.md) | Decisiones que la consigna no fija, con su fundamento |
| [docs/estructura-del-proyecto.md](docs/estructura-del-proyecto.md) | Carpetas, archivos y responsabilidad de cada uno |
| [docs/como-verificar.md](docs/como-verificar.md) | Qué comprobar en cada etapa y cómo hacerlo |
