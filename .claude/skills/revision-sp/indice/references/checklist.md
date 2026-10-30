# Checklist de revisión de código — con severidad y cobertura

> **Cuándo leer este archivo:** en TODA revisión, después de correr el script, para recorrer los ítems que quedan como manuales y asignar severidad a lo que encuentres.

## Severidades

- **CRÍTICO** — riesgo de datos incorrectos, transacciones abiertas, inyección SQL o cambio silencioso del resultado en producción. Bloquea la aprobación.
- **INCUMPLE** — viola un estándar obligatorio de la política SQL Server de referencia. Bloquea la aprobación.
- **RECOMENDADO** — mejora sugerida; no bloquea.

> La asignación de CRÍTICO vs. INCUMPLE es una propuesta derivada de la guía (que solo distingue Obligatorio/Recomendado). Ambas bloquean; CRÍTICO indica qué atender primero. Validarla con el DBA.

## Cobertura

- **Auto** — `scripts/revisar_sp.py` lo detecta con certeza alta.
- **Auto (h)** — el script lo detecta por heurística: confirmar leyendo el código antes de reportarlo.
- **Manual** — requiere juicio o contexto (esquema, índices, datos, repositorio).
- **N/A SP** — no aplica a la revisión de un SP individual; solo a revisión de BD/PR completo.

| # | Ítem | Severidad | Cobertura | Referencia |
|---|---|---|---|---|
| 1 | No se usa `SELECT *` | INCUMPLE | Auto | consultas.md |
| 2 | Todos los JOINs son explícitos | INCUMPLE | Auto (h) | consultas.md |
| 3 | `IF EXISTS` en vez de `COUNT(*) > 0` | INCUMPLE | Auto | consultas.md |
| 4 | No hay `ISNULL()` en predicados WHERE/JOIN | INCUMPLE | Auto (h) | consultas.md |
| 5 | No hay código comentado sin justificación | INCUMPLE | Auto (h) | consultas.md |
| 6 | No hay `WHERE 1=1` innecesario | INCUMPLE | Auto (estático) / Manual (dinámico) | consultas.md |
| 7 | PKs y FKs tienen el mismo tipo de dato | INCUMPLE | Manual | modelo-datos.md |
| 8 | Toda FK tiene un índice non-clustered | INCUMPLE | Manual | indices.md |
| 9 | Índices de #Temp creados después del INSERT masivo | INCUMPLE | Auto | indices.md |
| 10 | SP usa `SET NOCOUNT ON` y `TRY/CATCH` | INCUMPLE (CRÍTICO si hay DML sin TRY/CATCH) | Auto | sp-transacciones.md |
| 11 | No hay SQL concatenado con parámetros de usuario | CRÍTICO | Auto (h) + Manual | seguridad.md |
| 12 | Transacciones cerradas con COMMIT o ROLLBACK en CATCH | CRÍTICO | Auto | sp-transacciones.md |
| 13 | No hay `ORDER BY` sin índice que lo soporte; ninguno en subconsultas/CTEs | INCUMPLE | Manual (índice) / Auto (h) (subconsulta) | consultas.md |
| 14 | NOLOCK solo en lectura no crítica, con justificación | INCUMPLE (CRÍTICO en lógica de negocio) | Auto | consultas.md |
| 15 | Validaciones de front-end documentadas y presentes | INCUMPLE | Manual, solo si se revisa la app | front-end.md |
| 16 | Nombres siguen las naming conventions (`usp_<Entidad>_<Accion>`) | INCUMPLE | Auto | sp-transacciones.md |
| 17 | Tipos de dato según tabla de referencia | INCUMPLE | Auto (h) | modelo-datos.md |
| 18 | No hay funciones escalares en SELECT masivo | RECOMENDADO | Manual | sp-transacciones.md |
| 19 | Query Store habilitado en producción | RECOMENDADO | N/A SP | operacion.md |
| 20 | Plan de mantenimiento de índices programado | RECOMENDADO | N/A SP | operacion.md |
| 21 | Refactor de agregación/NULL demuestra equivalencia | CRÍTICO | Manual | equivalencias-determinismo.md |
| 22 | Pre-agregación en CTE solo con funciones distributivas | CRÍTICO | Manual | equivalencias-determinismo.md |
| 23 | Conversiones que pueden fallar usan `TRY_CAST` | CRÍTICO | Manual | equivalencias-determinismo.md |
| 24 | `BETWEEN` → rango semiabierto declara ventana literal vs. intención | INCUMPLE (CRÍTICO si cambia la ventana sin declararlo) | Manual | equivalencias-determinismo.md |
| 25 | No hay `ORDER BY` en `SELECT ... INTO` ni `INSERT ... SELECT` | INCUMPLE | Auto | equivalencias-determinismo.md |
| 26 | `UNION ALL` detalle/totales con bandera de orden y `ORDER BY` final | INCUMPLE | Auto (h) | equivalencias-determinismo.md |
| 27 | Todo `TOP` tiene `ORDER BY`, y ordena por una columna que el `WHERE` no fija | INCUMPLE | Auto (falta ORDER BY) / Manual (columna fijada) | equivalencias-determinismo.md |
| 28 | Funciones de ventana con desempate hasta un criterio único | INCUMPLE | Manual | equivalencias-determinismo.md |
| 29 | Columnas de la clave clustered no aparecen en `INCLUDE` | INCUMPLE | Manual | indices.md |
| 30 | Índices filtrados no clavean la columna que filtran | INCUMPLE | Manual | indices.md |
| 31 | `SET ANSI_NULLS ON` y `SET QUOTED_IDENTIFIER ON` con índices filtrados | INCUMPLE | Auto | indices.md |
| 32 | Toda recomendación de índice tiene consumidor verificado | INCUMPLE | Manual | verificacion-repositorio.md |
| 33 | Se buscaron todas las definiciones del objeto (PROD/QA, init) | INCUMPLE | Manual, solo con acceso al repo | verificacion-repositorio.md |

## Reglas adicionales que también detecta el script (sin número en la guía)

| Regla | Severidad | Fuente en la guía |
|---|---|---|
| Encabezado sin autor / fecha / descripción / historial | INCUMPLE | consultas.md (Sec. 2) |
| Palabras reservadas en minúscula | INCUMPLE | consultas.md (Sec. 2) |
| Parámetro `(N)VARCHAR(MAX)` para dominio limitado | INCUMPLE | sp-transacciones.md (Sec. 4) |
| `CATCH` que no relanza el error (`THROW`) | INCUMPLE | sp-transacciones.md (patrón de Sec. 5) |
| `NOT IN (SELECT ...)` con posible NULL | INCUMPLE | equivalencias (comportamiento con NULL) |
| Prefijo `sp_` | INCUMPLE | sp-transacciones.md (naming) |
| Función sobre columna en `WHERE`/`ON` (no SARGable) | RECOMENDADO | consultas.md |
| Catch-all query `(@P IS NULL OR col = @P)` sin `OPTION (RECOMPILE)` | RECOMENDADO | consultas.md |
| Cursores | RECOMENDADO | metodologia-refactor.md (paso 4) |
| Archivo no UTF-8 | INCUMPLE | metodologia-refactor.md (paso 1) |
