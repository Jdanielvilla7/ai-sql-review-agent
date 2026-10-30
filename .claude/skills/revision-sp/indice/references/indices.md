# Índices: diseño, INCLUDE, filtrados, temporales, mantenimiento

> **Cuándo leer este archivo:** Leer cuando el SP crea índices (incluidos los de #Temp), cuando vas a recomendar un índice, o cuando el problema reportado es de rendimiento.
>
> Fuente: Política de Buenas Prácticas SQL Server de referencia v1.0. Cumplimiento obligatorio salvo donde diga "Recomendado".

### 3. Normalización de Índices

- Toda consulta crítica debe estar respaldada por un índice; revisar el plan de ejecución y confirmar ausencia de Index Scans en tablas grandes.
- No crear índices a ciegas: usar `sys.dm_db_missing_index_details`, `sys.dm_db_index_usage_stats` y Query Store para identificar candidatos.
- Eliminar índices duplicados o raramente usados.
- Cada tabla: exactamente un índice clustered (generalmente la PK INT IDENTITY). Evitar clustered en columnas de alta volatilidad.
- Toda FK es candidata a índice non-clustered (SQL Server no lo crea automáticamente). Considerar índices compuestos según selectividad (más selectivo primero). Usar `INCLUDE` para lograr Covering Index (Key Lookup = 0).
- Tablas temporales (`#Temp`): crear índices **después** del INSERT masivo, nunca antes.
- Variables tipo tabla (`@Table`): no soportan `CREATE INDEX` adicional una vez declaradas (solo PK/UNIQUE inline). Preferir `#Temp` para conjuntos grandes que requieran índices.
- Mantenimiento: `REORGANIZE` si fragmentación <30%, `REBUILD` si ≥30%. Actualizar estadísticas tras cargas masivas (`UPDATE STATISTICS`). Monitorear con `sys.dm_db_index_physical_stats`.
- Índices filtrados para columnas con distribución sesgada (muchos NULL/inactivos): `CREATE INDEX ... WHERE EstadoId = 1`.

**Reglas adicionales sobre `INCLUDE` e índices filtrados**

- **Las columnas de la clave clustered ya están en las hojas de todo índice no agrupado** — nunca van en `INCLUDE`. Incluirlas las almacena dos veces sin ningún beneficio.
- **Un índice filtrado cuya clave es la columna que filtra tiene clave constante.** `ON (Col) WHERE Col IS NULL` no permite seek: todas las entradas comparten la misma clave. El filtro útil es el inverso (`IS NOT NULL`), o se clavea por otra columna y el filtro actúa solo como predicado.
- **En SQL Server los `NULL` sí se indexan.** Por eso un índice sin filtro sobre una columna de *soft delete* contiene prácticamente toda la tabla con un único valor de clave.
- **Si el `INCLUDE` propuesto abarca todas las columnas restantes, lo correcto es un índice CLUSTERED.** Misma cobertura —porque *es* la tabla—, sin duplicar los datos ni pagar dos escrituras por fila.
- **Los índices filtrados exigen `ANSI_NULLS ON` y `QUOTED_IDENTIFIER ON`**, no solo al crearlos sino en toda sesión que haga DML sobre la tabla; de lo contrario el `INSERT` falla con error 1934. Es la razón por la que esos `SET` son obligatorios en el encabezado del script, no una cortesía de estilo.
- **No indexar tablas que caben en una página.** Con unas decenas de filas el optimizador nunca elegirá el índice; solo cuesta escrituras y espacio.
- **No agregar `INCLUDE` de cobertura sin un consumidor verificado.** Localizar la vista o el SP que realmente proyecta esas columnas antes de proponerlo.
- **En tablas temporales preferir un índice `CLUSTERED`** cuando la temporal se lee entera: cubre todas las columnas por definición. Evitar `UNIQUE` salvo que la unicidad esté garantizada por construcción — si la premisa falla, revienta el SP completo.
