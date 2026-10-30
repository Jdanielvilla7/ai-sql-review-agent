# Verificar antes de decidir; definiciones duplicadas y entornos gemelos

> **Cuándo leer este archivo:** Leer antes de recomendar índices o cambios de esquema, y antes de cerrar cualquier cambio cuando trabajas con acceso al repositorio.
>
> Fuente: Política de Buenas Prácticas SQL Server de referencia v1.0. Cumplimiento obligatorio salvo donde diga "Recomendado".

### 11. Verificar antes de decidir

Una recomendación de índice, de tipo de dato o de refactor solo vale si está respaldada por evidencia del propio repositorio. Antes de aceptar o rechazar una sugerencia —propia o de un revisor— responder:

- **¿El objeto está versionado aquí?** Si la tabla, la función o el índice viven en otra base de datos que no se versiona en este repositorio, el cambio queda fuera de alcance. En ese caso, agrupar todas las peticiones equivalentes en **una sola tarea de DBA** en vez de repetirlas archivo por archivo.
- **¿Quién consume realmente este objeto?** Buscar las vistas, SP y scripts que lo leen antes de diseñar un índice. El patrón de acceso real siempre gana sobre la suposición: un covering index construido sobre un query que nadie ejecuta es costo puro.
- **¿La tabla es nueva o ya está desplegada?** El control de versiones lo responde comparando el archivo contra la rama base.
- **¿Cuántas filas tiene?** Los scripts de datos del propio repositorio suelen decirlo. El tamaño cambia por completo la recomendación de índices y de mantenimiento.
- **Si el revisor propone una consulta de validación, ejecutarla.** No asumir el resultado en ninguna dirección: puede confirmar el problema o descartarlo, y ambas respuestas son útiles.
- **Distinguir la decisión técnica de la decisión de negocio.** Un filtro que cambia el conjunto de filas de un reporte, una ventana de retención o la activación de un módulo no son decisiones del desarrollador: se documentan, se proponen y se dejan abiertas para quien corresponda.

### 12. Definiciones duplicadas y entornos gemelos

- **El mismo objeto puede estar definido en más de un archivo:** un DDL independiente y un script de inicialización, o un par de entornos gemelos (producción y QA). Corregir uno y no el otro genera una divergencia silenciosa que solo aparece al desplegar.
- Antes de dar por cerrado cualquier cambio de esquema, **buscar todas las definiciones del objeto** en el repositorio, no solo el archivo que se está editando.
- **Las diferencias entre gemelos suelen ser intencionales** —sufijos de nombre, secuencias propias y sobre todo referencias a otras bases de datos— y se conservan. Nunca "normalizarlas" como si fueran inconsistencias.
- Tras aplicar un cambio a un par de gemelos, **verificar con el control de versiones que ninguna línea de referencia entre bases cambió** salvo la intencionada.
- Esta regla aplica igual a los documentos de estándares y a los scripts de configuración: si conviven varias copias, hay que declarar cuál es la autoritativa y retirar las demás.
