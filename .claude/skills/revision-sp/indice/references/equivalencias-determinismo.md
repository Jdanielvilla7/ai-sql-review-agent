# Equivalencias falsas y determinismo del resultado

> **Cuándo leer este archivo:** Leer SIEMPRE que se proponga o se revise un refactor (TOP/MAX, ISNULL/COALESCE, +/CONCAT, CAST, BETWEEN, pre-agregación) y siempre que el SP tenga UNION ALL, TOP, funciones de ventana, SELECT INTO o vistas con ORDER BY.
>
> Fuente: Política de Buenas Prácticas SQL Server de referencia v1.0. Cumplimiento obligatorio salvo donde diga "Recomendado".

### 9. Equivalencias falsas (refactors que cambian el resultado)

Las reescrituras de esta sección **parecen** neutras y no lo son. Antes de aplicar cualquiera —propia o sugerida en un code review— hay que demostrar la equivalencia, no asumirla. Cuando el SP o la vista ya está en producción, un cambio de este tipo altera el reporte sin que nadie lo note.

- **`TOP (1) ... ORDER BY col` no equivale a `MAX(col)`.** Con `ORDER BY` ascendente devuelve el **mínimo**; haría falta `DESC`. Y hay una segunda diferencia que suele pasarse por alto: un agregado sin `GROUP BY` **siempre devuelve una fila** (con `NULL` si no hay coincidencias), mientras que `TOP (1)` devuelve **cero filas**. Si un `OUTER APPLY` posterior se apoya en `WHERE X.col IS NULL` para decidir si se ejecuta, la sustitución rompe la lógica.
- **`ISNULL` y `COALESCE` no son intercambiables en una vista o SP publicado.** `ISNULL` devuelve el tipo del **primer argumento** y marca la columna `NOT NULL` en los metadatos; `COALESCE` resuelve por **precedencia de tipos** entre todos los argumentos y la marca nullable. Ambas cosas viajan al consumidor (BI, ORM, API). Además `COALESCE` se expande a un `CASE`, así que **puede evaluar su primer argumento dos veces** — relevante si es una subconsulta. Cambiar de uno a otro "por uniformidad de estilo" es un cambio de contrato, no de forma.
- **`+` y `CONCAT` difieren en el tratamiento de NULL, y eso cambia predicados.** `CONCAT` convierte NULL en cadena vacía; `+` propaga NULL (con `CONCAT_NULL_YIELDS_NULL ON`, que es el default). En un `JOIN` o un `NOT EXISTS`, pasar de `+` a `CONCAT` convierte un "no coincide" en un valor real que **puede emparejar por accidente**:

```sql
-- Con + : si Contenedor es NULL, la expresion es NULL, no hay match, la fila se descarta.
-- Con CONCAT: la expresion es '123_', que puede emparejar con un detalle terminado en '_'.
ON d.MANIFEST_ID = CAST(m.MANIFESTID AS NVARCHAR(50)) + '_' + rc.CONTAINERNUMBER
```

  En un anti-join que decide qué está pendiente de procesar, el `CONCAT` **oculta filas**. Preferir el fallo seguro y documentar la decisión.
- **Pre-agregar antes de totalizar solo es válido con funciones distributivas.** `SUM(SUM(x))` ≡ `SUM(x)`, y lo mismo aplica a `MIN` y `MAX`. Pero `SUM(COUNT(DISTINCT x))` **≠** `COUNT(DISTINCT x)`, porque los duplicados entre grupos se cuentan varias veces. Antes de aceptar un refactor a CTE `Base` + `Totales`, verificar que **todas** las agregaciones de la rama de totales sean distributivas.
- **`CAST` no arregla una conversión que falla.** Si un `varchar` no numérico revienta la conversión implícita, un `CAST(... AS int)` explícito falla exactamente igual. El arreglo es **`TRY_CAST`**, que devuelve `NULL` y simplemente no hace match — comportamiento seguro en un `LEFT JOIN` o un lookup.
- **`COALESCE(NULLIF(x, ''), x)` es siempre `x`**, para cualquier valor incluidos `''` y `NULL`. Es un patrón de código muerto frecuente. Corolario importante: **los identificadores de SQL Server no distinguen mayúsculas**, así que `t.COLUMNA` y `t.Columna` son la misma columna. Una diferencia de capitalización puede estar ocultando que una expresión entera no filtra nada.
- **Convertir `BETWEEN` en rango semiabierto no es mecánico: hay que decidir si se preserva la ventana literal o se corrige la intención.** `BETWEEN @A AND @B` sobre una columna `datetime` incluye `@B` exacto, así que con anclas de tipo `date` cubre hasta la medianoche del último día, no el día completo. Calcular primero la ventana literal, compararla con la intención aparente y **declarar explícitamente cuál de las dos se implementa**:

```sql
-- Literal: BETWEEN @F-1 AND @F+1  cubre [@F-1 00:00, @F+1 00:00]
--   = los dias @F-1 y @F completos, mas el primer instante de @F+1.
-- Equivalencia estricta:   >= DATEADD(DAY,-1,@F) AND < DATEADD(DAY, 1,@F)
-- Correccion de intencion: >= DATEADD(DAY,-1,@F) AND < DATEADD(DAY, 2,@F)   -- 3 dias completos
```

  Las dos versiones difieren en un día de datos. Si el ancla es `datetime` en vez de `date`, la diferencia además desplaza la ventana y puede cambiar el ganador de un `TOP 1`.

### 10. Determinismo del resultado

Un SP puede ser correcto, rápido y conforme al estándar y aun así devolver las filas en distinto orden entre ejecuciones. En reportes que se exportan a Excel o alimentan un dashboard, eso se percibe como un error de datos.

- **`ORDER BY` en `SELECT ... INTO` o `INSERT ... SELECT` no garantiza nada.** No define el orden físico de la tabla destino; solo agrega un `Sort` al plan. Se elimina. El orden se resuelve en el `SELECT` final, o se materializa con un índice **agrupado** sobre la tabla temporal.
- **`UNION ALL` no garantiza el orden entre ramas.** Un patrón detalle + totales puede intercalar las filas de totales. Patrón obligatorio: bandera de orden explícita en ambas ramas, usada tanto en el `ORDER BY` final como en la función de ventana:

```sql
;WITH Base AS ( ... ),                       -- detalle agregado una sola vez
Unificado AS (
    SELECT 0 AS _kind, ... FROM Base
    UNION ALL
    SELECT 1,          ... FROM Base GROUP BY ...   -- totales derivados de Base
)
SELECT ROW_NUMBER() OVER (ORDER BY u._kind, u.Fecha, u.Localidad) AS 'No.', ...
FROM Unificado u
ORDER BY u._kind, u.Fecha, u.Localidad;
```

  La bandera `_kind` cumple dos funciones: fija el orden y permite suprimir columnas en la fila de totales (`CASE WHEN u._kind = 1 THEN '' ...`) sin duplicar la consulta.
- **Un `TOP 1` solo es determinista si el `ORDER BY` va sobre una columna que realmente varía.** Si el `WHERE` ya fija esa columna, ordenar por ella no desempata nada. Identificar qué distingue a las filas candidatas antes de elegir el criterio.
- **`ROW_NUMBER() OVER (ORDER BY col)` con `col` repetida produce numeración inestable** entre ejecuciones. Todo `ROW_NUMBER`, `RANK` y `DENSE_RANK` necesita desempate hasta llegar a un criterio único.
- **Una vista no puede imponer orden.** `ORDER BY` dentro de una vista solo es legal con `TOP`/`OFFSET`, y aun así **el orden no se propaga** a quien consulta la vista. El `ORDER BY` es responsabilidad de la consulta externa; si el consumidor es un reporte, debe declararlo él.
