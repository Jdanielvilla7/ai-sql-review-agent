# Modelo de datos: PKs, FKs, tipos de dato, NULL, esquemas desplegados

> **Cuándo leer este archivo:** Leer cuando el SP o script crea/altera tablas, declara tablas temporales con tipos, o cuando hay conversiones implícitas por tipos distintos entre columnas.
>
> Fuente: Política de Buenas Prácticas SQL Server de referencia v1.0. Cumplimiento obligatorio salvo donde diga "Recomendado".

### 1. Modelo de Datos (Normalización de Entidades)

**Claves Primarias (PK)**
- Siempre INT o BIGINT como PK. Nunca VARCHAR, NVARCHAR o UNIQUEIDENTIFIER como PK clustered.
- BIGINT en vez de INT si se anticipa superar los ~2,147 millones de registros.
- Si no hay candidato natural (incluyendo PKs compuestas), usar `IDENTITY(1,1)` como última opción.
- Si se requiere GUID por negocio: usarlo como PK no agrupada (non-clustered) y agregar un INT `IDENTITY` como índice clustered. Un GUID como PK clustered genera fragmentación severa — nunca hacerlo.
- Documentar el significado de cada PK en el diccionario de datos.

**Claves Foráneas (FK)**
- Siempre declarar FK con restricción referenciada en la BD. Nunca depender solo de lógica de aplicación.
- El tipo de dato de la FK debe coincidir exactamente con el de la PK referenciada (mismo tipo, precisión, signo).
- Toda FK es candidata a índice non-clustered (ver Sección 3).
- Nombrar: `FK_<TablaHija>_<TablaPadreOCampo>`.

**Tipos de Datos — usar siempre la columna "Recomendado", nunca la de "Evitar"**

| Caso de uso | Recomendado | Evitar | Motivo |
|---|---|---|---|
| Identificadores / IDs | INT / BIGINT | VARCHAR, GUID clustered | Menor espacio, búsqueda más rápida |
| Fechas y horas | DATETIME2(3) | DATETIME, VARCHAR | Mayor precisión, menor espacio |
| Solo fecha | DATE | DATETIME, VARCHAR | Evita conversiones implícitas |
| Valores monetarios | DECIMAL(18,4) | FLOAT, REAL | FLOAT tiene imprecisión binaria |
| Textos cortos (<50 car.) | NVARCHAR(n) fijo | TEXT, NTEXT | TEXT/NTEXT obsoletos |
| Textos largos | NVARCHAR(MAX) | TEXT | TEXT obsoleto |
| Indicadores Sí/No | BIT | CHAR(1), INT | Semántica clara, menor espacio |
| Enumerados simples | TINYINT con FK | VARCHAR con valores libres | Integridad referencial garantizada |

**Valores NULL**
- Ninguna columna acepta NULL salvo que el modelo lo exija explícitamente por regla de negocio.
- Si una columna tiene muchos NULL, considerar dividir la tabla (5NF) o usar tablas de atributos opcionales.
- Documentar en el diccionario de datos el motivo por el que una columna acepta NULL.
- Nunca comparar con `IS NULL` dentro de índices filtrados sin analizar antes la selectividad.

**Diseño general**
- Nunca tablas "catch-all" (God Table) con decenas de columnas opcionales.
- Separar entidades transaccionales (cambian frecuentemente) de maestras (cambian poco).
- Naming: tablas en PascalCase singular (`Factura`, no `Facturas` ni `tbl_factura`).
- Versionar el esquema de BD en control de fuentes (Liquibase, Flyway o scripts numerados).

**Esquemas ya desplegados vs. objetos nuevos**

- Antes de proponer un cambio de tipo, de nulabilidad o una restricción nueva, determinar si la tabla **ya está desplegada** o se crea en esta misma entrega. En un objeto nuevo el cambio es gratuito; en uno desplegado implica migración, y `ALTER TABLE ... ALTER COLUMN TYPE` reescribe la tabla tomando lock exclusivo.
- Distinguir un **script ejecutable** de un **volcado del esquema**. Editar un volcado no cambia la base de datos: lo que hace falta es una migración. Señales de volcado: cláusulas que el propio motor añade al generar el DDL, capitalización mixta e inconsistente, y restricciones expresadas en su forma normalizada interna en vez de como se escribieron.
- `ADD CONSTRAINT` sobre una tabla con datos **valida las filas existentes** y puede fallar en producción. Verificar antes que ninguna fila la viole, o usar el mecanismo de validación diferida del motor.
- Nunca agregar una columna que la aplicación no vaya a poblar. Una columna siempre nula hace que el dato mienta según la propia convención del modelo. Las migraciones que dependen de la aplicación se levantan como ticket conjunto de BD y app, no como edición del DDL.
