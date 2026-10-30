# revision-sp-mssql

Skill para **revisión, refactorización y optimización de Stored Procedures y código T-SQL de SQL Server** desde Claude Code.

El flujo combina validaciones mecánicas ejecutadas en Python con análisis contextual guiado por una política de buenas prácticas. La intención es que las comprobaciones determinísticas no dependan del LLM y que el análisis contextual se mantenga limitado a los criterios definidos por la política.

## Uso desde Claude Code

El skill se activa directamente desde el prompt. No es necesario ejecutar manualmente cada paso del proceso.

### Revisar un Stored Procedure

Si el procedimiento existe dentro del repositorio, basta con pedir:

```text
revisa "usp_Orden_Obtener"
```

Claude Code identifica el procedimiento y entra al flujo de revisión definido por el skill.

Durante la revisión:

1. Localiza y lee el Stored Procedure completo.
2. Ejecuta el analizador estático en Python.
3. Clasifica los hallazgos mecánicos por severidad y certeza.
4. Confirma los hallazgos heurísticos contra el código antes de reportarlos.
5. Detecta qué características contiene el SP y carga únicamente las referencias que aplican.
6. Recorre los puntos manuales del checklist que no pueden resolverse de forma determinística.
7. Si falta información necesaria para una conclusión, la registra como **Pendiente de verificar** en lugar de asumirla.
8. Evalúa el riesgo de que una corrección pueda cambiar el resultado funcional.
9. Genera el dictamen final de la revisión.

El resultado se resume como uno de los siguientes estados:

- **Requiere cambios** — existe al menos un hallazgo CRÍTICO o INCUMPLE.
- **Aprobado con observaciones** — únicamente existen hallazgos RECOMENDADOS.
- **Aprobado** — no existen hallazgos aplicables.

Además del dictamen, se muestra el resumen de hallazgos encontrados, su severidad, la explicación correspondiente y lo que debe corregirse o verificarse.

### Refactorizar u optimizar un Stored Procedure

Para solicitar cambios sobre un procedimiento:

```text
Refactoriza "usp_Orden_Obtener"
```

Claude Code entra al flujo de refactorización definido por el skill.

El proceso sigue este orden:

1. Lee el procedimiento original y determina su comportamiento actual.
2. Carga la metodología de refactorización y las referencias que correspondan al código encontrado.
3. Ejecuta primero las correcciones de limpieza y cumplimiento.
4. Mejora mantenibilidad y estructura cuando aplica.
5. Evalúa optimizaciones de rendimiento únicamente con evidencia disponible.
6. Evita aplicar silenciosamente cambios que puedan alterar las filas o resultados devueltos.
7. Genera la nueva versión del Stored Procedure.
8. Ejecuta nuevamente el analizador estático sobre el código generado.
9. Corrige cualquier incumplimiento detectado antes de finalizar.
10. Entrega el código resultante y un resumen del trabajo realizado.

Al finalizar, también muestra un **dictamen de la operación**, indicando el resultado de la revisión posterior al cambio y cualquier punto que deba verificarse antes de llevar el SP a producción.

## Cómo funciona internamente

```text
Prompt en Claude Code
        │
        ▼
Localización y lectura del SP
        │
        ▼
Analizador estático en Python
        │
        ├── Validaciones mecánicas
        ├── Severidad
        └── Certeza
        │
        ▼
Selección de referencias aplicables
        │
        ▼
Análisis contextual con Claude Code
        │
        ├── Política SQL Server
        ├── Checklist manual
        ├── Equivalencia de resultados
        └── Contexto disponible
        │
        ▼
Revisión / Refactorización
        │
        ▼
Validación final
        │
        ▼
Dictamen
```

La separación entre Python y Claude Code es intencional:

- **Python** ejecuta las validaciones que pueden comprobarse mecánicamente.
- **Claude Code** analiza los puntos que requieren contexto, intención o evaluación de una posible refactorización.
- **La política y las referencias** delimitan los criterios utilizados durante la revisión.

El agente no debe completar información que no esté disponible. Si una recomendación depende, por ejemplo, de índices existentes, volumen de datos, tipos reales de columnas o consumidores del SP, el punto queda marcado para verificación.

## Principio de equivalencia

Una corrección técnicamente válida puede cambiar el resultado de un Stored Procedure.

Casos como estos se tratan de forma explícita:

```text
ISNULL(...)  → IS NULL
NOT IN       → NOT EXISTS
NOLOCK       → otro nivel de aislamiento
BETWEEN      → rango semiabierto
TOP          → TOP + ORDER BY
+            → CONCAT
TOP 1        → MAX
```

Si una modificación puede cambiar las filas devueltas, el skill no debe aplicarla silenciosamente. Debe indicar la diferencia entre:

- la versión equivalente al comportamiento existente;
- la versión que corrige la intención o estándar;
- el impacto potencial del cambio.

## Ejemplo rápido

### Revisión

```text
> revisa "usp_Orden_Obtener"
```

Salida resumida esperada:

```text
Dictamen: Requiere cambios

CRÍTICO     1
INCUMPLE    3
RECOMENDADO 2

Pendiente de verificar:
- Índices existentes sobre las tablas consultadas.
- Volumen aproximado de filas.
```

### Refactorización

```text
> Refactoriza "usp_Orden_Obtener"
```

Salida resumida esperada:

```text
Operación: Refactorización completada
Dictamen posterior: Aprobado con observaciones

Cambios aplicados:
- Correcciones de cumplimiento.
- Simplificación de consultas.
- Ajustes de manejo de errores.
- Validación estática posterior al cambio.

Pendiente de verificar:
- Recomendación de índice sujeta a evidencia del entorno.
```

## Estructura

```text
.claude/skills/revision-sp/
├── SKILL.md
└── indice/
    ├── assets/
    │   └── plantilla_dictamen.md
    ├── references/
    │   ├── checklist.md
    │   ├── consultas.md
    │   ├── equivalencias-determinismo.md
    │   ├── front-end.md
    │   ├── indices.md
    │   ├── metodologia-refactor.md
    │   ├── modelo-datos.md
    │   ├── operacion.md
    │   ├── seguridad.md
    │   ├── sp-transacciones.md
    │   └── verificacion-repositorio.md
    └── scripts/
        └── revisar_sp.py
examples/
├── usp_Orden_Obtener.sql
└── resultado_revision.md
```

## Analizador estático

El analizador también puede ejecutarse directamente desde la raíz del repositorio:

```bash
python .claude/skills/revision-sp/indice/scripts/revisar_sp.py examples/usp_Orden_Obtener.sql
python .claude/skills/revision-sp/indice/scripts/revisar_sp.py examples/usp_Orden_Obtener.sql --json
```

El script detecta los puntos mecánicos y clasifica los hallazgos por severidad y certeza.

Un resultado sin hallazgos automáticos **no equivale a una aprobación**. Los criterios manuales todavía deben ser evaluados por el flujo del skill.

## Cobertura

El checklist contiene **33 criterios** distribuidos entre validaciones automáticas y manuales. Entre otros puntos, el flujo contempla:

- estructura y convenciones de Stored Procedures;
- `SET NOCOUNT ON`;
- manejo de errores;
- transacciones;
- SQL dinámico;
- `NOLOCK`;
- `SELECT *`;
- `TOP` y determinismo;
- tipos de datos y conversiones;
- seguridad;
- índices;
- equivalencia funcional;
- validaciones que requieren revisar esquema o repositorio.

## Política

La política incluida en este repositorio es de referencia y no depende de información de una organización específica.

Para adaptar el flujo a otro conjunto de estándares se pueden reemplazar el checklist y las referencias manteniendo la misma arquitectura:

```text
validación determinística
        +
política versionada
        +
análisis contextual
        +
guardrails de equivalencia
        +
dictamen estructurado
```
