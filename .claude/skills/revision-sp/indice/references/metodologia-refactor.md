# Metodología de refactorización y optimización de SPs

> **Cuándo leer este archivo:** Leer cuando el usuario pide refactorizar u optimizar un SP (no solo revisarlo).
>
> Fuente: Política de Buenas Prácticas SQL Server de referencia v1.0. Cumplimiento obligatorio salvo donde diga "Recomendado".

## Metodología de optimización de Stored Procedures

Cuando optimices o refactorices un Stored Procedure, sigue estos 4 pasos **en este orden**. No tiene sentido optimizar código sucio o con bugs, porque podrías estar optimizando algo que ni siquiera hace lo correcto. Es importante tomar en cuenta que el resultado de salida tiene que ser igual al original, porque muchos de los scripts ya están en producción y un cambio podría afectar.

### 1. Limpieza
Eliminar todo lo que no aporta al resultado final antes de tocar la lógica de negocio.
- Quitar código muerto, comentarios obsoletos, variables/parámetros no usados.
- Eliminar `SELECT *` y especificar columnas explícitas.
- Remover lógica duplicada o redundante.
- Estandarizar formato: indentación, mayúsculas en palabras clave, alias consistentes.
- Evitar subqueries o CTEs innecesarios reemplazables con JOINs simples.
- Si el archivo no está en UTF-8, convertirlo.
- Ordenar bloques de código lógicamente (declaraciones, validaciones, lógica principal, resultados).

### 2. Mantenibilidad
Dejar el SP fácil de entender y modificar.
- Nombres claros para variables, parámetros y tablas temporales; formato `@NombreAux` para auxiliares; SPs con naming `usp_<Entidad>_<Accion>`.
- Comandos SQL alineados, indentación consistente, mayúsculas.
- Variables/parámetros declarados al inicio, con comentario de propósito.
- Comentarios que expliquen el "por qué", no el "qué".
- Separar en bloques lógicos claros (validación de parámetros, lógica principal, manejo de errores).
- Manejo de errores consistente (`TRY/CATCH`, mensajes claros).
- Evitar "magic numbers" sin explicación.

### 3. Funcionalidad
Confirmar que el SP hace exactamente lo que debe, sin efectos secundarios ni casos borde rotos.
- Verificar resultados ante datos nulos, vacíos o inesperados.
- Validar parámetros de entrada (tipos, rangos, obligatoriedad).
- Confirmar que la lógica de negocio no se alteró al limpiar/reestructurar.
- Revisar transacciones: que no queden abiertas y que el rollback funcione ante error.

### 4. Optimización
Una vez el SP es correcto y limpio, mejorar su rendimiento.
- Revisar el plan de ejecución: scans innecesarios, operadores costosos.
- Evaluar índices existentes vs. los que realmente usa la consulta (ver Sección 3 de estándares).
- Reemplazar patrones ineficientes (`IN` con subquery grande → `EXISTS`; cursors → operaciones basadas en conjuntos).
- Revisar filtros dinámicos: que no fuercen scans completos por concatenación mal indexada.
- Medir antes/después (tiempo de ejecución, I/O) para confirmar la mejora real.
