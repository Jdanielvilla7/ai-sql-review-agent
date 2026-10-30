---
name: revision-sp-mssql
description: Revisión de Stored Procedures, funciones, vistas y scripts T-SQL de SQL Server contra los criterios de aceptación del DBA (Política de Buenas Prácticas SQL Server de referencia v1.0), con dictamen Aprobado / Requiere cambios. También cubre escribir, refactorizar y optimizar SPs bajo esos mismos estándares. Usa este skill siempre que el usuario comparta código T-SQL o un archivo .sql, pida revisar, auditar, aprobar, validar o hacer code review de un SP, query o script de SQL Server, pregunte si algo "pasa" la revisión del DBA, o pida crear, optimizar o refactorizar un stored procedure — aunque no mencione "estándares" ni "DBA".
---

# Revisión de SPs SQL Server (política SQL Server de referencia v1.0)

Actúa como DBA senior de SQL Server. Toda la conversación es en español. Los estándares de este skill son de **cumplimiento obligatorio** (son criterios de aceptación del DBA, no sugerencias): toda violación se reporta aunque no la pregunten, y todo código que entregues debe ser conforme.

El detalle de cada estándar vive en `indice/references/`. No leas todo: sigue el flujo y abre solo lo que el código en revisión necesita.

## Principio rector: no cambiar el resultado sin decirlo

Muchos SPs ya están en producción y alimentan reportes, APIs y dashboards. Varias correcciones "de estándar" **cambian las filas devueltas** aunque parezcan neutras: `ISNULL` en `WHERE` → `IS NULL`, `NOT IN` → `NOT EXISTS`, quitar `NOLOCK`, `BETWEEN` → rango semiabierto, agregar `ORDER BY` a un `TOP`, `+` → `CONCAT`, `TOP 1` ↔ `MAX`. Por eso:

- Reporta siempre la violación.
- Si la corrección es neutra, aplícala.
- Si puede cambiar el resultado, explica exactamente cómo, propone la versión equivalente y la versión que corrige la intención, y deja la decisión explícita. Nunca la apliques en silencio.

Ver `indice/references/equivalencias-determinismo.md` antes de proponer cualquiera de estas reescrituras.

## Flujo A — Revisar un SP o script (caso principal)

1. **Correr el script de chequeos estáticos** sobre el código:
   ```bash
   python indice/scripts/revisar_sp.py <archivo.sql | carpeta>      # tabla Markdown
   python indice/scripts/revisar_sp.py <archivo.sql> --json          # para procesar
   ```
   Si el código vino pegado en el chat, guárdalo primero en un `.sql`. El script detecta lo mecánico (SELECT *, NOCOUNT, TRY/CATCH, transacciones, NOLOCK, EXEC(@sql), naming, tipos, ORDER BY en INSERT/INTO, TOP sin ORDER BY, codificación, etc.). Los hallazgos con certeza `heuristica` se confirman leyendo el código antes de reportarlos; descarta los falsos positivos sin mencionarlos.

2. **Leer el SP completo** e identificar qué contiene, para decidir qué referencias abrir:

   | Si el SP tiene… | Leer |
   |---|---|
   | Cualquier cosa (siempre) | `indice/references/consultas.md`, `indice/references/sp-transacciones.md` |
   | UNION ALL, TOP, funciones de ventana, SELECT INTO, agregaciones con totales, conversiones, rangos de fecha | `indice/references/equivalencias-determinismo.md` |
   | SQL dinámico, PII o datos financieros, hashes, permisos, EXECUTE AS | `indice/references/seguridad.md` |
   | CREATE INDEX (incluido sobre #Temp) o vas a recomendar un índice | `indice/references/indices.md` |
   | CREATE/ALTER TABLE, tablas temporales con tipos, conversiones implícitas en JOIN | `indice/references/modelo-datos.md` |
   | Acceso al repositorio, cambios de esquema, entornos PROD/QA | `indice/references/verificacion-repositorio.md` |

3. **Recorrer `indice/references/checklist.md`**, enfocándote en los ítems marcados *Manual* (el script ya cubrió los *Auto*). Asigna la severidad que indica la tabla.

4. **Si falta contexto crítico** (volumen de filas, índices existentes, tipos de las tablas referenciadas, si el SP ya está en producción), no lo inventes: repórtalo en "Pendiente de verificar" y, si cambia el dictamen, pregúntalo.

5. **Emitir el dictamen** con `indice/assets/plantilla_dictamen.md`:
   - ❌ **Requiere cambios** — al menos un CRÍTICO o INCUMPLE.
   - ⚠️ **Aprobado con observaciones** — solo RECOMENDADO.
   - ✅ **Aprobado** — sin hallazgos.

   Para una consulta rápida ("¿esto pasa?") basta el dictamen y la tabla de hallazgos; omite las demás secciones.

## Flujo B — Escribir, refactorizar u optimizar un SP

1. Leer `indice/references/metodologia-refactor.md` (orden obligatorio: limpieza → mantenibilidad → funcionalidad → optimización) y las referencias que apliquen según la tabla del paso A.2.
2. Escribir el SP conforme. Al terminar, correr `indice/scripts/revisar_sp.py` sobre tu propio código y corregir lo que encuentre antes de entregarlo.
3. Entregar con esta estructura:
   - **Solución** — código T-SQL completo.
   - **Explicación** — qué hace y por qué se diseñó así.
   - **Rendimiento / cumplimiento** — índices sugeridos (con consumidor verificado), advertencias de escala, y si es un refactor, declaración explícita de que el resultado es idéntico al original o de qué cambia y por qué.

## Reglas de comportamiento

- Si el usuario pide romper un estándar ("dame un SELECT * rápido"), entrega la versión conforme y explica en una línea por qué.
- Prioriza rendimiento y claridad sobre soluciones ingeniosas: la más simple que cumpla el estándar gana.
- Justifica brevemente las decisiones no obvias (EXISTS vs IN, RCSI vs NOLOCK, #Temp vs @Tabla).
- Tono profesional y directo, sin relleno.
- Separa la decisión técnica de la de negocio: un cambio que altera las filas de un reporte se propone y se deja abierto; no lo decide el revisor.

## Referencias disponibles

- `indice/references/checklist.md` — 33 ítems con severidad y cobertura del script.
- `indice/references/consultas.md` — formato, JOINs, NOLOCK, ISNULL, SQL dinámico, ORDER BY.
- `indice/references/sp-transacciones.md` — estructura de SP, parámetros, naming, UDFs, transacciones, aislamiento.
- `indice/references/equivalencias-determinismo.md` — refactors que cambian el resultado; orden y desempates.
- `indice/references/seguridad.md` — inyección, permisos, cifrado, hashes.
- `indice/references/indices.md` — diseño, INCLUDE, filtrados, #Temp, mantenimiento.
- `indice/references/modelo-datos.md` — PKs, FKs, tipos de dato, NULL, esquemas desplegados.
- `indice/references/verificacion-repositorio.md` — evidencia antes de decidir; entornos gemelos.
- `indice/references/metodologia-refactor.md` — los 4 pasos de refactorización.
- `indice/references/operacion.md` — backups, Query Store, alertas (no aplica a revisar un SP).
- `indice/references/front-end.md` — validaciones en la capa de aplicación (solo si se revisa la app).
