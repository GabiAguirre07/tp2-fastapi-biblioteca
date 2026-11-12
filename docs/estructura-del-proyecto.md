# Estructura del proyecto

## Estado actual (Etapa 4)

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
│   ├── comunes.py          obtener_o_404, guardar, eliminar y transaccion reutilizables
│   ├── autores.py          CRUD de autores y libros de un autor
│   ├── libros.py           CRUD de libros, filtro y asociación con autores
│   ├── prestamos.py        Reglas de los préstamos: prestar, devolver y consultar
│   └── socios.py           CRUD de socios
├── routers/                Endpoints HTTP (delgados)
│   ├── __init__.py
│   ├── comunes.py          Paginación, respuestas de error documentadas y fecha de hoy
│   ├── manejadores.py      Traduce los errores de negocio a códigos HTTP
│   ├── autores.py          /autores y /autores/{id}/libros
│   ├── libros.py           /libros y /libros/{id}/autores/{autor_id}
│   ├── prestamos.py        /prestamos
│   └── socios.py           /socios y /socios/{id}/prestamos
├── docs/                   Documentación del proyecto
├── requirements.txt        Dependencias para ejecutar la aplicación
├── requirements-dev.txt    Dependencias de desarrollo (incluye las anteriores)
├── setup.cfg               Configuración de pycodestyle
├── .gitignore              Archivos que Git no versiona
└── README.md               Cómo instalar, ejecutar y verificar
```

Al ejecutar la aplicación se crea además `biblioteca.db` (la base SQLite). No se versiona.

La carpeta `tests/` que pide la consigna se agrega en la Etapa 5.

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
| `services/excepciones.py` | `ErrorDeNegocio` y sus subclases `RecursoNoEncontrado` (404), `ConflictoDeNegocio` (409) y `OperacionNoPermitida` (403). No dependen de FastAPI. |
| `services/comunes.py` | Operaciones compartidas por todas las entidades: `obtener_o_404` (también trata como inexistente un id fuera del rango de SQLite), `guardar` (convierte el `IntegrityError` en conflicto), `eliminar` y `transaccion`, que agrupa varios cambios para que se confirmen todos juntos o ninguno. |
| `services/autores.py`, `libros.py`, `socios.py` | Alta, listado, consulta, modificación y baja de cada entidad, con sus reglas (por ejemplo, no borrar un autor con libros). Además, `libros.py` filtra por disponibilidad y asocia y desasocia autores, y `autores.py` lista los libros de un autor. |
| `services/prestamos.py` | Las reglas de la Etapa 4: `crear_prestamo` (404, 403, límite de 3 y stock, con vencimiento a 14 días), `devolver_prestamo` (repone el stock y calcula la multa), `obtener_prestamo`, `listar_prestamos_de_socio` y `a_lectura`, que agrega los datos calculados `vencido` y `dias_atraso`. Las cifras de la consigna son constantes al inicio del archivo. |
| `routers/comunes.py` | `Paginacion` / `PaginacionDep` (`skip` y `limit`), las respuestas 403, 404 y 409 que se documentan en Swagger y `FechaHoyDep`, la dependencia que entrega la fecha de hoy (los tests la reemplazan por una fecha fija). |
| `routers/manejadores.py` | Traduce cada error de negocio a su código HTTP mediante el diccionario `CODIGOS_HTTP`. |
| `routers/autores.py`, `libros.py`, `socios.py` | Cinco endpoints por recurso, más los de relación (`POST` y `DELETE /libros/{id}/autores/{autor_id}`, `GET /autores/{id}/libros`) y `GET /socios/{id}/prestamos`. Solo reciben el pedido, llaman al servicio y devuelven el esquema de salida. |
| `routers/prestamos.py` | `POST /prestamos`, `POST /prestamos/{id}/devolucion` y `GET /prestamos/{id}`. Pasan la fecha de hoy al servicio y convierten el resultado con `a_lectura`; no deciden ninguna regla. |

## Dirección de las dependencias

```text
main.py ──► routers/ ──► services/ ──► models/
   │            │             │
   └────────────┴─────────────┴──► database.py (la sesión se inyecta)
```

- `models/` no depende de nada del resto del proyecto, solo de SQLModel, SQLAlchemy y Pydantic.
- `services/` conoce los modelos y la sesión, pero **no** FastAPI: sus reglas se pueden usar y probar sin HTTP.
- `routers/` es la única capa que conoce HTTP; delega todo en los servicios.
- `database.py` no conoce los modelos: crea las tablas de los que se hayan importado antes.
- Las referencias entre modelos que se miran entre sí se resuelven con `TYPE_CHECKING`, para no generar importaciones circulares: `models/libros.py` importa `Autor` y `AutorLeer` en tiempo de ejecución (los necesita para `LibroLeer`), y `models/autores.py` solo referencia `Libro` con `TYPE_CHECKING`, de modo que no hay ciclo.
