# Normalización de consultas T-SQL

> **Cuándo leer este archivo:** Leer en TODA revisión de SP: cubre formato, JOINs, NOLOCK, ISNULL en predicados, SQL dinámico y ORDER BY.
>
> Fuente: Política de Buenas Prácticas SQL Server de referencia v1.0. Cumplimiento obligatorio salvo donde diga "Recomendado".

### 2. Normalización de Consultas SQL

- **Mayúsculas** en toda palabra reservada de T-SQL (`SELECT`, `FROM`, `WHERE`, `JOIN`...).
- Indentar subconsultas, CTEs y bloques lógicos.
- Encabezado de comentario en cada SP/función: autor, fecha, descripción, historial de cambios.
- Eliminar todo código comentado que ya no sea necesario (usar control de versiones para historial).
- **JOINs siempre explícitos.** Nunca implicit joins (`FROM A, B WHERE A.id = B.idA`).
- Verificar que los campos de JOIN tengan el mismo tipo de dato (evita conversiones implícitas que inhabilitan índices).
- Mover validaciones con datos fijos del `ON` al `WHERE`.
- Eliminar `WHERE 1=1` / `WHERE 0=0` salvo que sean generados dinámicamente con justificación documentada.
- **Nunca `SELECT *`.** Especificar siempre columnas necesarias.
- Alias descriptivos en columnas calculadas y subconsultas.
- Evitar funciones escalares en el `SELECT` que se ejecuten fila por fila (scalar UDFs pre-SS2019 son cuello de botella).
- **`IF EXISTS` en vez de `COUNT(*) > 0`** para verificar existencia.
- Evitar `ORDER BY` salvo que sea estrictamente necesario para el resultado final; si se usa, debe existir un índice que lo cubra. **Nunca `ORDER BY` en subconsultas o CTEs intermedias.** En paginación, preferir `OFFSET`/`FETCH NEXT` con índice ordenado.
- Eliminar `COLLATE` innecesarios; solo cuando hay cruce de BDs/servidores con distinta collation.
- `WITH (NOLOCK)` únicamente en tablas transaccionales y solo en lectura no crítica (reportes, dashboards) — nunca en lógica de negocio o actualizaciones. Preferir **RCSI** (`READ_COMMITTED_SNAPSHOT`) a nivel de BD como alternativa a NOLOCK masivo.
- Evitar parsear JSON/XML en SQL; mover ese procesamiento a la capa de aplicación o a SPs bien definidos. `OPENJSON`/`FOR XML` solo para integraciones externas documentadas.
- Evitar `ISNULL()` en predicados `WHERE`/`JOIN` (inhabilita índices, fuerza full scan). Usar `IS NOT NULL` + comparación, o modelar con valor centinela documentado. `ISNULL()` en la proyección del `SELECT` sí es aceptable.
- Todo SQL dinámico (`sp_executesql`) debe parametrizarse — nunca concatenar input de usuario. Documentar el motivo de usar SQL dinámico. Validar y sanear parámetros antes de pasarlos.
- **Catch-all queries** del tipo `(@Param = -1 OR col = @Param)` o `(@Param IS NULL OR col = @Param)` generan un plan único que sirve mal a todos los valores. Mitigación: `OPTION (RECOMPILE)` en reportes de baja frecuencia de ejecución, o `sp_executesql` parametrizado cuando la frecuencia es alta.
