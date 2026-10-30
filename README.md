# revision-sp-mssql

Skill para revisión, refactorización y optimización de Stored Procedures y código T-SQL de SQL Server.

La revisión combina validaciones mecánicas ejecutadas en Python con análisis contextual guiado por una política de buenas prácticas. El objetivo es separar lo que puede validarse de forma determinística de lo que requiere revisar intención, equivalencia de resultados, esquema, índices o contexto del repositorio.

El skill está preparado para Claude Code. Python resuelve los chequeos determinísticos y el agente utiliza las referencias únicamente para los puntos que requieren análisis contextual.

## Flujo

1. Ejecutar `revisar_sp.py` sobre el archivo o carpeta.
2. Confirmar los hallazgos heurísticos leyendo el código.
3. Cargar únicamente las referencias que apliquen al SP revisado.
4. Revisar los puntos manuales del checklist.
5. No asumir información que no esté disponible. Se registra como pendiente de verificar.
6. Generar el dictamen usando la plantilla incluida.
7. Si se solicita refactorización u optimización, verificar que el cambio no altere silenciosamente el resultado.

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

## Chequeos estáticos

Desde la raíz del repositorio:

```bash
python .claude/skills/revision-sp/indice/scripts/revisar_sp.py examples/usp_Orden_Obtener.sql
python .claude/skills/revision-sp/indice/scripts/revisar_sp.py examples/usp_Orden_Obtener.sql --json
```

El script detecta los puntos mecánicos y clasifica cada hallazgo por severidad y certeza. Un resultado sin hallazgos no equivale a aprobación: los puntos manuales todavía deben revisarse con las referencias correspondientes.

## Alcance

La política incluida en este repositorio es de referencia y no depende de información de una organización específica. Para utilizar el flujo con una política propia se pueden reemplazar las referencias y el checklist manteniendo el mismo proceso de validación.
