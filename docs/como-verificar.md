# Cómo verificar el proyecto

Guía para comprobar, etapa por etapa, que el proyecto hace lo que dice. Se amplía al cerrar cada etapa.

Antes de empezar, instalar y activar el entorno virtual como indica el [README](../README.md#instalación-y-ejecución).

## Etapa 1: modelos y base de datos

### 1. La aplicación arranca

```bash
python -m uvicorn main:app --reload
```

**Resultado esperado:** la terminal muestra `Application startup complete.` sin errores y se crea el archivo `biblioteca.db` junto a `main.py`. La ubicación es la misma aunque el comando se lance desde otra carpeta.

### 2. Swagger responde

Abrir <http://127.0.0.1:8000/docs>.

**Resultado esperado:** se ve el título **Sistema de Biblioteca**. Desde la Etapa 2 aparecen los grupos **Autores**, **Libros** y **Socios** (ver la sección siguiente).

### 3. La base tiene las cinco tablas

Con la aplicación detenida (`Ctrl + C`), abrir el intérprete de Python en la carpeta del proyecto (comando `python`) y escribir:

```python
import sqlite3
con = sqlite3.connect("biblioteca.db")
con.execute("select name from sqlite_master where type='table' order by name").fetchall()
```

**Resultado esperado:**

```text
[('autor',), ('libro',), ('libroautor',), ('prestamo',), ('socio',)]
```

Para salir del intérprete: `exit()`.

### 4. Las claves foráneas están activas

En el intérprete de Python, desde la carpeta del proyecto:

```python
from database import engine
from sqlalchemy import text
with engine.connect() as c:
    print(c.execute(text("PRAGMA foreign_keys")).scalar())
```

(Después de la última línea, presionar `Enter` una vez más para ejecutar el bloque.)

**Resultado esperado:** `1`. Un `0` significaría que SQLite no está validando las claves foráneas.

### 5. La base rechaza un stock negativo

En el intérprete de Python, desde la carpeta del proyecto:

```python
from sqlmodel import Session
from database import engine
from models import Libro
with Session(engine) as s:
    s.add(Libro(titulo="X", isbn="1", stock=-1, anio=2000))
    s.commit()
```

(Igual que antes, presionar `Enter` una vez más al final.)

**Resultado esperado:** falla con `IntegrityError: CHECK constraint failed: ck_libro_stock_no_negativo`. No queda ningún dato guardado.

### 6. Calidad del código

Con el entorno virtual activado:

```bash
pip install -r requirements-dev.txt
python -m pycodestyle .
python -m pyright
```

**Resultado esperado:** `pycodestyle` no imprime nada y `pyright` termina con `0 errors, 0 warnings, 0 informations`.

## Etapa 2: CRUD de autores, libros y socios

Se prueba desde Swagger (<http://127.0.0.1:8000/docs>) con la aplicación en marcha. En cada endpoint: **Try it out**, completar el cuerpo y **Execute**. Si se cambió el esquema de alguna tabla, borrar antes `biblioteca.db` (la aplicación no migra tablas existentes).

### 7. Alta correcta (201)

| Endpoint | Cuerpo | Resultado esperado |
|---|---|---|
| `POST /autores` | `{"nombre": "Julio Cortázar", "nacionalidad": "Argentina"}` | 201 con el `id` asignado |
| `POST /libros` | `{"titulo": "Rayuela", "isbn": "978-84-376-0494-7", "stock": 3, "anio": 1963}` | 201; el `isbn` vuelve como `9788437604947` (sin guiones) |
| `POST /socios` | `{"nombre": "Ana Pérez", "email": "Ana@Example.com"}` | 201; el `email` vuelve como `ana@example.com` y `activo` vale `true` |

### 8. Datos inválidos (422)

Probar cada cuerpo y comprobar que la respuesta es 422 y que no se guarda nada:

| Endpoint | Cuerpo | Motivo |
|---|---|---|
| `POST /autores` | `{"nombre": "   ", "nacionalidad": "Argentina"}` | Nombre vacío tras recortar espacios |
| `POST /libros` | `{"titulo": "X", "isbn": "123", "stock": 1, "anio": 2000}` | ISBN que no tiene 10 ni 13 caracteres |
| `POST /libros` | `{"titulo": "X", "isbn": "9788437604947", "stock": -1, "anio": 2000}` | Stock negativo |
| `POST /libros` | `{"titulo": "X", "isbn": "9788437604947", "stock": 1, "anio": 1000}` | Año anterior a 1450 |
| `POST /socios` | `{"nombre": "Ana", "email": "no-es-un-email"}` | Formato de email inválido |

### 9. Duplicados (409)

| Endpoint | Cuerpo | Resultado esperado |
|---|---|---|
| `POST /libros` | el mismo ISBN del punto 7, escrito como `9788437604947` | 409: el ISBN ya existe |
| `POST /socios` | `{"nombre": "Otra Ana", "email": "ANA@example.com"}` | 409: el email ya existe (no distingue mayúsculas) |

### 10. Consulta, listado y paginación

| Endpoint | Resultado esperado |
|---|---|
| `GET /autores/1` | 200 con el autor creado |
| `GET /autores/999` | 404 con mensaje en español |
| `GET /libros?skip=0&limit=1` | 200 con una lista de a lo sumo 1 libro |
| `GET /libros?limit=0` | 422 (`limit` debe estar entre 1 y 100) |

### 11. Modificación parcial (PATCH)

| Endpoint | Cuerpo | Resultado esperado |
|---|---|---|
| `PATCH /socios/1` | `{"activo": false}` | 200; solo cambia `activo`, el resto queda igual |
| `PATCH /libros/1` | `{"stock": 10}` | 200 con el stock actualizado |
| `PATCH /libros/1` | `{}` | 200 sin cambios |
| `PATCH /libros/1` | `{"stock": null}` | 422 (ningún campo admite `null`) |
| `PATCH /autores/999` | `{"nombre": "Nadie"}` | 404 |

### 12. Baja (DELETE)

| Endpoint | Resultado esperado |
|---|---|
| `DELETE /socios/1` | 204 sin contenido |
| `GET /socios/1` | 404 (ya no existe) |
| `DELETE /socios/1` | 404 |

Las bajas protegidas (409) son: un autor con libros asociados y un libro o socio con préstamos. La de autores se prueba desde la Etapa 3 (punto 18); la de libros y socios con préstamos se prueba desde la Etapa 4 (punto 24).

### 13. Calidad del código

Igual que en el punto 6: `python -m pycodestyle .` no imprime nada y `python -m pyright` informa `0 errors`.

## Etapa 3: relaciones y consultas

Se prueba desde Swagger con la aplicación en marcha. Los ejemplos de esta sección suponen una base sin otros autores ni libros: si ya hay datos, se ven también los existentes y los `id` cambian (usar siempre los que devuelve cada alta). Para partir de una base limpia, detener la aplicación y borrar `biblioteca.db`.

### 14. Preparar los datos

| Endpoint | Cuerpo | Resultado esperado |
|---|---|---|
| `POST /autores` | `{"nombre": "Jorge Luis Borges", "nacionalidad": "Argentina"}` | 201 |
| `POST /autores` | `{"nombre": "Adolfo Bioy Casares", "nacionalidad": "Argentina"}` | 201 |
| `POST /libros` | `{"titulo": "El Aleph", "isbn": "9780307474728", "stock": 2, "anio": 1949}` | 201 con `"autores": []` |
| `POST /libros` | `{"titulo": "Ficciones", "isbn": "9780802130303", "stock": 0, "anio": 1944}` | 201 con `"autores": []` |

### 15. Asociar autores a un libro

Con los `id` devueltos en el punto 14: `{libro}` es el de El Aleph y `{autor1}` y `{autor2}` los de Borges y Bioy Casares.

| Endpoint | Resultado esperado |
|---|---|
| `POST /libros/{libro}/autores/{autor1}` | 201: el libro ya muestra a Borges en `autores` |
| `POST /libros/{libro}/autores/{autor1}` (repetido) | 409: el autor ya está asociado |
| `POST /libros/{libro}/autores/{autor2}` | 201: dos autores, ordenados por `id` |
| `POST /libros/99/autores/{autor1}` | 404: el libro no existe |
| `POST /libros/{libro}/autores/99` | 404: el autor no existe |
| `GET /libros/{libro}` | 200 con los dos autores |

### 16. Filtro por disponibilidad

| Endpoint | Resultado esperado |
|---|---|
| `GET /libros?disponibles=true` | Solo los libros con stock (El Aleph) |
| `GET /libros?disponibles=false` | Solo los agotados (Ficciones) |
| `GET /libros` | Todos |
| `GET /libros?disponibles=maybe` | 422 (valor que no es booleano) |
| `GET /libros?disponibles=true&limit=1&skip=0` | El primer libro disponible |
| `GET /libros?disponibles=true&limit=1&skip=1` | El segundo libro disponible; con un único disponible, lista vacía |

El filtro se aplica antes de paginar: `skip` y `limit` cuentan sobre los libros ya filtrados. Con otros libros cargados, `skip=1` devuelve el segundo disponible y no una lista vacía.

### 17. Libros de un autor

| Endpoint | Resultado esperado |
|---|---|
| `GET /autores/{autor1}/libros` | 200 con El Aleph, mostrando **todos** sus autores |
| `GET /autores/99/libros` | 404 |

### 18. Desasociar y borrar un autor

| Endpoint | Resultado esperado |
|---|---|
| `DELETE /autores/{autor1}` | 409: el autor tiene libros asociados |
| `DELETE /libros/{libro}/autores/{autor1}` | 204 |
| `DELETE /libros/{libro}/autores/{autor1}` (repetido) | 404: no está asociado |
| `DELETE /autores/{autor1}` | 204: ya no tiene libros |

### 19. Calidad del código

Igual que en el punto 6: `python -m pycodestyle .` no imprime nada y `python -m pyright` informa `0 errors`.

## Etapa 4: préstamos y reglas de negocio

Se prueba desde Swagger con la aplicación en marcha. Los `id` dependen de lo que ya haya en la base: usar siempre los que devuelve cada alta (aquí se los nombra: `{ana}`, `{beto}`, `{L1}`, etc.). Para partir de una base limpia, detener la aplicación y borrar `biblioteca.db`. Hay que tener en cuenta que **las fechas las decide el servidor**: `fecha_prestamo` es la de hoy.

### 20. Preparar los datos

| Endpoint | Cuerpo | Resultado esperado |
|---|---|---|
| `POST /socios` | `{"nombre": "Ana Pérez", "email": "ana@example.com"}` | 201 (`{ana}`) |
| `POST /socios` | `{"nombre": "Beto Gómez", "email": "beto@example.com", "activo": false}` | 201 (`{beto}`, inactivo) |
| `POST /libros` | `{"titulo": "L1", "isbn": "9780000000011", "stock": 2, "anio": 2000}` | 201 (`{L1}`) |
| `POST /libros` | `{"titulo": "L2", "isbn": "9780000000028", "stock": 1, "anio": 2000}` | 201 (`{L2}`) |
| `POST /libros` | `{"titulo": "L3", "isbn": "9780000000035", "stock": 0, "anio": 2000}` | 201 (`{L3}`) |
| `POST /libros` | `{"titulo": "L4", "isbn": "9780000000042", "stock": 5, "anio": 2000}` | 201 (`{L4}`) |
| `POST /libros` | `{"titulo": "L5", "isbn": "9780000000059", "stock": 5, "anio": 2000}` | 201 (`{L5}`) |

### 21. Prestar y reglas del alta

| Endpoint | Cuerpo | Resultado esperado |
|---|---|---|
| `POST /prestamos` | `{"socio_id": {ana}, "libro_id": {L1}}` | 201: `fecha_vencimiento` = hoy + 14 días, `fecha_devolucion` nula, `multa` 0, `vencido` false, `dias_atraso` 0 |
| `GET /libros/{L1}` | — | `stock` pasó de 2 a 1 |
| `POST /prestamos` | socio `{beto}` y libro `{L1}` | 403: el socio está inactivo |
| `POST /prestamos` | socio `{ana}` y libro `{L3}` (stock 0) | 409: no tiene ejemplares disponibles |
| `POST /prestamos` | socio `9999`; luego libro `9999` | 404 en ambos casos |
| `POST /prestamos` | `{ana}` pide `{L4}` y después `{L5}` | 201 y 201 (ya tiene 3 activos) |
| `POST /prestamos` | `{ana}` pide `{L2}` | 409: ya tiene 3 préstamos activos. `GET /libros/{L2}` sigue con stock 1 |

### 22. Listar los préstamos de un socio

| Endpoint | Resultado esperado |
|---|---|
| `GET /socios/{ana}/prestamos?activos=true` | Los 3 préstamos |
| `GET /socios/9999/prestamos` | 404 |

### 23. Devolver

| Endpoint | Resultado esperado |
|---|---|
| `POST /prestamos/{id del préstamo de L1}/devolucion` | 200: `fecha_devolucion` = hoy, `multa` 0. `GET /libros/{L1}` vuelve a stock 2 |
| el mismo `POST` repetido | 409: el préstamo ya fue devuelto; el stock sigue en 2 |
| `POST /prestamos/9999/devolucion` | 404 |
| `GET /socios/{ana}/prestamos` con `activos=true`, `activos=false` y sin parámetro | 2, 1 y 3 préstamos |
| `POST /prestamos` de `{ana}` con `{L2}` y luego de `{beto}` (reactivado con `PATCH /socios/{beto}` `{"activo": true}`) con `{L2}` | 201 y 409 (el último ejemplar ya está prestado) |
| `GET /prestamos/{id}` y `GET /prestamos/9999` | 200 y 404 |

### 24. Borrados protegidos por los préstamos

| Endpoint | Resultado esperado |
|---|---|
| `DELETE /libros/{L1}` | 409: tiene préstamos, incluso uno ya devuelto (se conserva el historial) |
| `DELETE /socios/{ana}` | 409: tiene préstamos |

### 25. Ids fuera de rango

| Endpoint | Resultado esperado |
|---|---|
| `GET /socios/99999999999999999999` | 404 (antes de la Etapa 4 daba 500) |
| `GET /libros?skip=99999999999999999999` | 422 |

### 26. Lo que no se puede ver desde Swagger el mismo día

Una **multa mayor a 0**, o un préstamo con `vencido: true` y `dias_atraso > 0`, requieren que pasen los 14 días del plazo, porque la fecha la decide el servidor. Esos casos se verificaron con pruebas que reemplazan la fecha de hoy (atrasos de −5 a 366 días) y se cubrirán con los tests de la Etapa 5.

### 27. Calidad del código

Igual que en el punto 6: `python -m pycodestyle .` no imprime nada y `python -m pyright` informa `0 errors`.

## Compatibilidad comprobada

| Sistema | Versiones de Python | Qué se comprobó |
|---|---|---|
| Linux | 3.10, 3.11, 3.12, 3.13 y 3.14 | La aplicación arranca y crea las tablas con solo `requirements.txt`. |
| Linux | 3.10, 3.11, 3.12, 3.13 y 3.14 | Los 15 endpoints de la Etapa 2 con una batería de unas 80 comprobaciones (códigos 200, 201, 204, 404, 409 y 422). |
| Linux | 3.10, 3.12 y 3.14 | `pycodestyle` y `pyright` sin errores. |
| Linux | 3.10, 3.11, 3.12, 3.13 y 3.14 | Los endpoints de relaciones y el filtro de la Etapa 3 con una batería de 74 comprobaciones, y también con las versiones más viejas que permiten los rangos de `requirements.txt`. |
| Linux | 3.10, 3.12 y 3.14 | Servidor real sobre una base creada con el código de la Etapa 2: asociar, duplicado, filtros y persistencia tras reiniciar. |
| Windows (PowerShell) | 3.14 | Instalación en un entorno virtual limpio y arranque de la aplicación. |
| Windows (PowerShell) | — | Recorrido completo de la Etapa 3 desde Swagger. |
| Linux | 3.10, 3.12 y 3.14 | Los endpoints de préstamos con una batería de 173 comprobaciones (cada regla, el orden de las validaciones, multas de −5 a 366 días de atraso, pedidos simultáneos y pruebas de mutación), y también con las versiones más viejas que permiten los rangos de `requirements.txt`. |
| Linux | 3.10 y 3.14 | Servidor real sobre una base creada con el código de la Etapa 3, lanzado desde otra carpeta y en una ruta con espacios y `Ñ`: datos viejos legibles, préstamos y devoluciones correctos y 25 + 30 + 20 pedidos HTTP simultáneos sin violar el stock ni el máximo. |
| Windows (PowerShell) | 3.14 | Recorrido completo de la Etapa 4 desde Swagger. |
