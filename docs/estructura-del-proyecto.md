# Estructura del proyecto

## Estado actual (Etapa 7)

```text
tp2-fastapi-biblioteca/
├── main.py                 Punto de entrada: crea la aplicación FastAPI
├── database.py             Base de datos: engine, creación de tablas y sesión
├── models/                 Tablas y esquemas de entrada/salida
│   ├── __init__.py         Importa todos los modelos para registrar las tablas
│   ├── comunes.py          Tipos validados y clase base de los PATCH
│   ├── autores.py          Autor, AutorBase, AutorCrear, AutorActualizar, AutorLeer
│   ├── libros.py           Libro y sus esquemas (con sus validaciones)
│   ├── libro_autor.py      LibroAutor: tabla intermedia Libro N-N Autor
│   ├── socios.py           Socio y sus esquemas
│   └── prestamos.py        Prestamo, PrestamoCrear, PrestamoLeer
├── services/               Reglas de negocio (no conocen HTTP)
│   ├── __init__.py
│   ├── excepciones.py      Errores de negocio propios
│   ├── seguridad.py        Roles, identificación de quien pide y reglas de autorización
│   ├── comunes.py          obtener_o_404, guardar, eliminar y transaccion reutilizables
│   ├── autores.py          CRUD de autores y libros de un autor
│   ├── libros.py           CRUD de libros, filtro y asociación con autores
│   ├── prestamos.py        Reglas de los préstamos: prestar, devolver y consultar
│   └── socios.py           CRUD de socios
├── routers/                Endpoints HTTP (delgados)
│   ├── __init__.py
│   ├── comunes.py          Paginación, respuestas de error documentadas y fecha de hoy
│   ├── manejadores.py      Traduce los errores de negocio a códigos HTTP
│   ├── seguridad.py        Lee X-Rol y X-Socio-Id y ofrece las dependencias de permisos
│   ├── autores.py          /autores y /autores/{id}/libros
│   ├── libros.py           /libros y /libros/{id}/autores/{autor_id}
│   ├── prestamos.py        /prestamos
│   └── socios.py           /socios y /socios/{id}/prestamos
├── tests/                  Tests automáticos (pytest)
│   ├── __init__.py
│   ├── conftest.py         Fixtures: base en memoria, reloj, cliente HTTP (bibliotecario), cliente anónimo y ayudante de API
│   ├── ayudas.py           Reloj (fecha de «hoy» controlable) y Api (crea datos por la API)
│   ├── test_reglas_de_negocio.py   Caso feliz y de error de cada regla de la consigna
│   ├── test_autores.py     CRUD y validaciones de autores
│   ├── test_libros.py      CRUD, ISBN, filtro, paginación y asociación con autores
│   ├── test_socios.py      CRUD y validaciones de socios
│   ├── test_prestamos.py   Préstamos, devoluciones, multas y listados
│   ├── test_seguridad.py   Roles, credenciales, permisos y documentación en Swagger
│   ├── test_servicios.py   Funciones de services/ probadas directamente
│   ├── test_modelos.py     Restricciones de las tablas contra la base
│   ├── test_aplicacion.py  Arranque, lifespan, Swagger y manejo de errores
│   └── test_concurrencia.py  Pedidos simultáneos con hilos sobre una base en archivo
├── docs/                   Documentación del proyecto
├── requirements.txt        Dependencias para ejecutar la aplicación
├── requirements-dev.txt    Dependencias de desarrollo y tests (incluye las anteriores)
├── setup.cfg               Configuración de pycodestyle, pytest y cobertura
├── .gitignore              Archivos que Git no versiona
└── README.md               Cómo instalar, ejecutar y verificar
```

Al ejecutar la aplicación se crea además `biblioteca.db` (la base SQLite). No se versiona.

Al correr los tests se generan `.coverage` y `.pytest_cache/`, que tampoco se versionan.

## Responsabilidad de cada archivo

| Archivo | Responsabilidad |
|---|---|
| `main.py` | Crea la aplicación (`FastAPI`) y, mediante `lifespan`, crea las tablas al iniciar. Importa el paquete `models` para que todas las tablas queden registradas antes de crearlas, registra los manejadores de errores e incluye los routers. |
| `database.py` | Único lugar donde se configura el acceso a la base: ruta del archivo, `engine`, activación de claves foráneas, `crear_tablas()` y la dependencia `obtener_sesion()` con su alias `SesionDep`. El resto de la aplicación recibe la sesión por inyección y nunca abre conexiones propias. |
| `models/comunes.py` | Tipos con validación reutilizables (`NombreTexto`, `TituloTexto`, `NacionalidadTexto`, `IsbnTexto`, `EmailNormalizado`) y `ActualizacionParcial`, base de los esquemas de `PATCH`. |
| `models/autores.py` | `AutorBase` (campos compartidos), `Autor` (tabla) y los esquemas `AutorCrear`, `AutorActualizar` y `AutorLeer`. |
| `models/libros.py` | `LibroBase` (campos y validaciones), `Libro` (tabla, con las restricciones `CHECK` y la relación con los autores cargada junto con el libro) y sus esquemas; `LibroLeer` incluye los autores. |
| `models/libro_autor.py` | `LibroAutor`: tabla intermedia con clave primaria compuesta. |
| `models/socios.py` | `SocioBase` (campos, formato de email), `Socio` (tabla) y sus esquemas. |
| `models/prestamos.py` | `Prestamo` (tabla: vincula un socio con un libro y guarda las fechas y la multa) y sus esquemas: `PrestamoCrear` (entrada: solo `socio_id` y `libro_id`) y `PrestamoLeer` (salida: los campos de la tabla más `vencido` y `dias_atraso`). |
| `models/__init__.py` | Reexporta las clases del paquete. |
| `services/excepciones.py` | `ErrorDeNegocio` y sus subclases `RecursoNoEncontrado` (404), `ConflictoDeNegocio` (409) y `OperacionNoPermitida` (403) y `NoAutenticado` (401). No dependen de FastAPI. |
| `services/comunes.py` | Operaciones compartidas por todas las entidades: `obtener_o_404` (también trata como inexistente un id fuera del rango de SQLite), `guardar` (convierte el `IntegrityError` en conflicto), `eliminar` y `transaccion`, que agrupa varios cambios para que se confirmen todos juntos o ninguno. |
| `services/autores.py`, `libros.py`, `socios.py` | Alta, listado, consulta, modificación y baja de cada entidad, con sus reglas (por ejemplo, no borrar un autor con libros). Además, `libros.py` filtra por disponibilidad y asocia y desasocia autores, y `autores.py` lista los libros de un autor. |
| `services/seguridad.py` | `Rol`, `Usuario` (rol y, si es socio, su id), `identificar_usuario` (convierte los valores de `X-Rol` y `X-Socio-Id` en un `Usuario` o lanza 401) y las dos reglas de autorización, `exigir_bibliotecario` y `exigir_propietario` (403). No conoce HTTP ni FastAPI. |
| `services/prestamos.py` | Las reglas de la Etapa 4: `crear_prestamo` (404, 403, límite de 3 y stock, con vencimiento a 14 días), `devolver_prestamo` (repone el stock y calcula la multa), `obtener_prestamo`, `listar_prestamos_de_socio` y `a_lectura`, que agrega los datos calculados `vencido` y `dias_atraso`. Las cifras de la consigna son constantes al inicio del archivo. |
| `tests/conftest.py` | Las fixtures compartidas: `motor` (automática: reemplaza `database.engine` por una base SQLite en memoria para cada test), `tablas`, `reloj`, `cliente` (`TestClient` con la sesión y la fecha reemplazadas mediante `dependency_overrides`, que se identifica como bibliotecario en cada pedido), `anonimo` (cliente sin credenciales) y `api`. |
| `tests/ayudas.py` | `Reloj`, que entrega la fecha de «hoy» y permite avanzarla (`avanzar(dias)`), y `Api`, un ayudante que crea autores, libros, socios y préstamos a través de la propia API con valores únicos. |
| `tests/test_*.py` | Un archivo por entidad, uno con las reglas de negocio de la consigna y cinco transversales (servicios, modelos, aplicación, concurrencia y seguridad). |
| `routers/comunes.py` | `Paginacion` / `PaginacionDep` (`skip` y `limit`), las respuestas 401, 403, 404 y 409 que se documentan en Swagger y `FechaHoyDep`, la dependencia que entrega la fecha de hoy (los tests la reemplazan por una fecha fija). |
| `routers/seguridad.py` | Único archivo que sabe cómo viajan las credenciales: declara los encabezados `X-Rol` y `X-Socio-Id` como esquemas de seguridad (botón *Authorize* de Swagger), arma el `Usuario` con `obtener_usuario` y ofrece `SOLO_BIBLIOTECARIO` y `EL_PROPIO_SOCIO_O_BIBLIOTECARIO` para los decoradores. |
| `routers/manejadores.py` | Traduce cada error de negocio a su código HTTP mediante el diccionario `CODIGOS_HTTP`. |
| `routers/autores.py`, `libros.py`, `socios.py` | Cinco endpoints por recurso, más los de relación (`POST` y `DELETE /libros/{id}/autores/{autor_id}`, `GET /autores/{id}/libros`) y `GET /socios/{id}/prestamos`. Solo reciben el pedido, llaman al servicio y devuelven el esquema de salida; cada endpoint declara en su decorador quién puede usarlo. |
| `routers/prestamos.py` | `POST /prestamos`, `POST /prestamos/{id}/devolucion` y `GET /prestamos/{id}`. Pasan la fecha de hoy al servicio y convierten el resultado con `a_lectura`; no deciden ninguna regla. Registrar y devolver son del bibliotecario; consultar un préstamo, del bibliotecario o del socio dueño. |

## Dirección de las dependencias

```text
main.py ──► routers/ ──► services/ ──► models/
   │            │             │
   └────────────┴─────────────┴──► database.py (la sesión se inyecta)
```

- `models/` no depende de nada del resto del proyecto, solo de SQLModel, SQLAlchemy y Pydantic.
- `services/` conoce los modelos y la sesión, pero **no** FastAPI: sus reglas se pueden usar y probar sin HTTP.
- `routers/` es la única capa que conoce HTTP; delega todo en los servicios. La autorización de la Etapa 7 sigue esa división: los routers leen los encabezados y los servicios deciden quién puede qué.
- `database.py` no conoce los modelos: crea las tablas de los que se hayan importado antes.
- Las referencias entre modelos que se miran entre sí se resuelven con `TYPE_CHECKING`, para no generar importaciones circulares: `models/libros.py` importa `Autor` y `AutorLeer` en tiempo de ejecución (los necesita para `LibroLeer`), y `models/autores.py` solo referencia `Libro` con `TYPE_CHECKING`, de modo que no hay ciclo.
