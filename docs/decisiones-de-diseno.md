# Decisiones de diseño

Registro de las decisiones que la consigna no fija, cada una con su fundamento. Este documento se amplía al cerrar cada etapa.

La consigna manda sobre cualquier otra referencia: se respeta su estructura de carpetas (`models/`, `routers/`, `services/`, `tests/`) y sus requerimientos.

## Criterios generales

1. **Pensado para quien evalúa.** El proyecto se puede clonar, instalar, ejecutar y probar con el mínimo esfuerzo y en cualquier sistema operativo: pocas dependencias, base de datos sin servidor, ninguna variable de entorno obligatoria y configuración versionada dentro del repositorio.
2. **Sin capa `repositories/`.** La `Session` de SQLModel ya cumple el rol de repositorio (patrón *unit of work*); agregar otra capa encima duplicaría abstracciones sin necesidad. La separación de responsabilidades pasa por otro lado: los routers traducen HTTP y los *services* aplican las reglas de negocio (principio de responsabilidad única).
3. **SQLite.** Es un archivo local, no requiere instalar nada y SQLModel abstrae el motor: cambiar a otra base casi no afectaría al código.
4. **Tablas y esquemas separados.** Para entrada y salida de la API se usarán esquemas distintos de la tabla (por ejemplo, el cliente nunca envía el `id`). Se implementó en la Etapa 2 (decisión 23).
5. **Los códigos HTTP son parte del contrato.** Cada regla de negocio responde con su código (404, 409, 403). Los *services* lanzan errores propios y la capa HTTP los traduce (decisión 24).

## Etapa 1: modelos y base de datos

### Modelo

6. **Nombres de columnas idénticos a la consigna** (`anio`, `fecha_prestamo`, `fecha_vencimiento`, `fecha_devolucion`, etc.). Quien compare el código con el enunciado encuentra los mismos nombres.
7. **Validaciones en las clases `Base`, no en las tablas.** Las clases tabla no validan sus campos; las reglas de formato y de largo se definen junto con los esquemas de entrada, que es donde se ejecutan. En la Etapa 1 solo se declaran las restricciones que exige la consigna: ISBN y email únicos y `stock >= 0`.
8. **Año del libro entre 1450 y el año actual.** 1450 es el año de la imprenta de tipos móviles, así que ningún libro puede ser anterior. El mínimo se valida en `LibroBase` y se refuerza con un `CHECK` en la base; el máximo no lleva `CHECK` porque cambia con el tiempo, por lo que el año actual se calcula al iniciar la aplicación.

### Base de datos

9. **Claves foráneas activadas en cada conexión** (`PRAGMA foreign_keys=ON`). SQLite no las valida por defecto: sin esto aceptaría un préstamo de un socio que no existe. El *listener* se registra sobre la clase `Engine` y no sobre un engine concreto, para que también alcance a las bases en memoria que usarán los tests.
10. **`lifespan` en lugar de `on_event("startup")`** para crear las tablas al iniciar, porque `on_event` está deprecado en FastAPI.
11. **Ruta de la base anclada al proyecto.** `biblioteca.db` se guarda junto al código (`Path(__file__).resolve().parent`), sin importar desde qué carpeta se lance la aplicación, y la URL se construye con `URL.create` en lugar de un texto armado a mano para que las rutas con espacios o caracteres como `Ñ` no den problemas.
12. **Sin migraciones.** Las tablas se crean con `create_all`, que no modifica tablas ya existentes. Si cambia el esquema durante el desarrollo hay que borrar `biblioteca.db` y volver a arrancar. El archivo no se versiona (está en `.gitignore`), así que quien clone el repositorio siempre parte de una base nueva.

### Código

13. **Anotaciones de tipo en `database.py` y `main.py`** (`Iterator[Session]`, `AsyncIterator[None]`, `-> None`). El contrato de cada función se lee en su firma y `pyright` puede comprobarlo.
14. **`pycodestyle` con 88 columnas**, configurado en `setup.cfg`. PEP 8 sugiere 79, pero 88 es la medida estándar de los formateadores automáticos más usados (Black y Ruff); alinear el chequeo con ellos evita que el formateador y el control se contradigan. Está en un archivo versionado y no en la configuración del editor, así que vale para cualquier herramienta y cualquier persona.

### Dependencias y entorno

15. **Dependencias de ejecución y de desarrollo separadas.** `requirements.txt` tiene solo lo necesario para correr la aplicación; `requirements-dev.txt` incluye ese archivo más las herramientas de control (`pycodestyle`, `pyright`, y más adelante `pytest` y `pytest-cov`). Quien solo quiere ejecutar la API instala lo mínimo.
16. **Solo las dependencias directas, con rangos de versión.** `requirements.txt` lista `fastapi`, `uvicorn`, `sqlmodel` y `email-validator` con un piso (la versión con la que se probó) y un tope (la siguiente versión mayor, para que una actualización con cambios incompatibles no rompa el proyecto). Se descartó un `pip freeze` completo porque fija versiones exactas de decenas de paquetes y puede no instalarse en otra versión de Python. `email-validator` figura aunque ningún archivo lo importe, porque `EmailStr` lo necesita. Tampoco se usa `fastapi[standard]`, que instala muchos paquetes que el proyecto no necesita.
17. **Python 3.10 como versión mínima.** Los modelos usan la sintaxis `int | None`, que SQLModel evalúa al arrancar. La aplicación se probó de la versión 3.10 a la 3.14.
18. **Arranque con `python -m uvicorn main:app --reload`.** Con `python -m` el comando funciona igual en cualquier sistema operativo y no depende de que la carpeta de scripts del entorno virtual esté en el `PATH`. No se usa `fastapi dev` porque forma parte de `fastapi[standard]`.
19. **Archivos de requisitos en ASCII.** En PowerShell, el operador `>` escribe en UTF-16, que GitHub muestra como binario y algunas herramientas no leen; por eso estos archivos se generan en ASCII.

## Etapa 2: CRUD de autores, libros y socios

### Validación de los datos

20. **Largos de los textos.** Nombres (autor y socio) de 2 a 100 caracteres, título de 1 a 200 y nacionalidad de 2 a 60: rechazan datos claramente inválidos sin molestar con nombres o títulos largos reales. Se definen una sola vez en `models/comunes.py` y las entidades las reutilizan. Los espacios al inicio y al final se recortan y un texto que queda vacío se rechaza.
21. **ISBN de 10 o 13 caracteres, con guiones opcionales, guardado normalizado.** Acepta `978-0-13-468599-1` y lo guarda como `9780134685991`, de modo que el mismo ISBN escrito de dos maneras se detecte como duplicado (409). El último carácter de un ISBN-10 puede ser X. **No se valida el dígito verificador**: un ISBN inventado de ejemplo (como `1234567890`) sería rechazado por una persona que prueba la API sin conocer la regla de cálculo, y la consigna solo pide que el ISBN sea único. Los dígitos se comprueban con `[0-9]` y no con `\d`, porque `\d` también acepta dígitos de otros alfabetos.
22. **Email guardado en minúsculas.** `C@x.com` y `c@x.com` se consideran el mismo email y el segundo da 409, como pide la regla 8. Normalizar antes de guardar funciona igual en cualquier motor de base de datos, a diferencia de una comparación sin distinción de mayúsculas propia de SQLite. La respuesta devuelve el email ya normalizado.

### Estructura

23. **Esquemas de entrada y salida en el archivo de cada modelo** (`...Crear`, `...Actualizar`, `...Leer`), sin carpeta `schemas/`. Respeta las cuatro carpetas que sugiere la consigna y evita importaciones circulares cuando el libro incluya a sus autores.
24. **Reglas del CRUD en `services/` y routers delgados.** El router solo recibe el pedido, llama al servicio y devuelve el resultado. Los servicios lanzan errores de negocio propios (`RecursoNoEncontrado`, `ConflictoDeNegocio`) que no dependen de FastAPI, y un único manejador (`routers/manejadores.py`) los traduce a 404 y 409 mediante un diccionario `CODIGOS_HTTP`: sumar un código nuevo (el 403 de los préstamos) es agregar una línea. Las funciones comunes (`obtener_o_404`, `guardar`, `eliminar`) se reutilizan en las tres entidades y en los préstamos.
25. **Endpoints síncronos (`def`).** La sesión de SQLModel es síncrona; FastAPI ejecuta estas funciones en un grupo de hilos y no bloquea el servidor.

### Comportamiento de la API

26. **Modificación con `PATCH` parcial, sin `PUT`.** Se envían solo los campos a cambiar. Permite, por ejemplo, desactivar un socio con `{"activo": false}` sin reenviar todos sus datos. Un cuerpo vacío (`{}`) responde 200 sin cambios; enviar un campo con `null` responde 422, porque ninguna columna admite nulos y de otro modo la base lo rechazaría con un error 500. El `stock` se puede modificar directamente (nunca negativo), ya que representa los ejemplares disponibles.
27. **Unicidad resuelta por la restricción de la base.** Se guarda y, si la base rechaza el duplicado, se responde 409. No se consulta antes si el ISBN o el email existen: entre la consulta y el guardado otro pedido podría insertar el mismo valor, mientras que la restricción `UNIQUE` es atómica. Tras el error se revierte la transacción para que la sesión siga siendo utilizable. Un `PATCH` que deja el ISBN o el email igual no entra en conflicto consigo mismo.
28. **Borrado protegido.** Un libro o un socio con **cualquier** préstamo, incluso devuelto, no se puede borrar (409): se conserva el historial, y la base lo exige además por clave foránea. Para impedir que un socio pida más, se lo desactiva (`activo=false`). Un autor con libros asociados tampoco se puede borrar (409) para no modificar el catálogo sin aviso. Al borrar un libro sus vínculos con autores se eliminan junto con él, porque no tienen sentido sin el libro.
29. **Autores homónimos permitidos.** El nombre del autor no es único: la consigna solo exige unicidad de ISBN y email, y dos autores distintos pueden llamarse igual.
30. **Listado paginado.** `GET` de cada recurso admite `?skip=0&limit=100` (`limit` entre 1 y 100) y devuelve los registros ordenados por `id`; sin un orden fijo, la paginación podría repetir u omitir registros entre páginas. Los filtros propios (`disponibles`) se agregan en la Etapa 3.
31. **Mensajes de error.** Los 404 y 409 llevan un mensaje en español (`{"detail": "..."}`). Los 422 los genera Pydantic y quedan en inglés: traducirlos requeriría código y dependencias que la consigna no pide.
32. **Swagger documenta los códigos.** Cada operación declara sus respuestas posibles (201, 204, 404, 409), para que quien evalúa vea el contrato sin tener que adivinarlo.

### Limitación conocida

33. **Emails con dominios reservados.** La librería `email-validator` rechaza (422) dominios como `.test`, `.local` y `localhost`; `example.com` y los dominios reales se aceptan. Se indica en el README para quien pruebe la API.
