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

Las bajas protegidas (409) son: un autor con libros asociados y un libro o socio con préstamos. **Todavía no se pueden provocar desde Swagger**, porque los libros se asocian a autores en la Etapa 3 y los préstamos se crean en la Etapa 4; se comprueban por Swagger al cerrar esas etapas. Mientras tanto se verificaron insertando los registros directamente en la base.

### 13. Calidad del código

Igual que en el punto 6: `python -m pycodestyle .` no imprime nada y `python -m pyright` informa `0 errors`.

## Compatibilidad comprobada

| Sistema | Versiones de Python | Qué se comprobó |
|---|---|---|
| Linux | 3.10, 3.11, 3.12, 3.13 y 3.14 | La aplicación arranca y crea las tablas con solo `requirements.txt`. |
| Linux | 3.10, 3.11, 3.12, 3.13 y 3.14 | Los 15 endpoints de la Etapa 2 con una batería de unas 80 comprobaciones (códigos 200, 201, 204, 404, 409 y 422). |
| Linux | 3.10, 3.12 y 3.14 | `pycodestyle` y `pyright` sin errores. |
| Windows (PowerShell) | 3.14 | Instalación en un entorno virtual limpio y arranque de la aplicación. |
