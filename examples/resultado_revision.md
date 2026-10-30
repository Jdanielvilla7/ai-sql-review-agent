
## examples/usp_Orden_Obtener.sql  (codificación: UTF-8)
CRITICO: 0 | INCUMPLE: 9 | RECOMENDADO: 0

| Sev. | Línea | Ítem | Regla | Certeza | Detalle |
|---|---|---|---|---|---|
| INCUMPLE | 1 | 10 | Falta SET NOCOUNT ON | alta | Agregar al inicio del cuerpo del SP. |
| INCUMPLE | 1 | 10 | Falta BEGIN TRY / BEGIN CATCH | alta | Encapsular en TRY/CATCH. |
| INCUMPLE | 1 | 16 | Prefijo sp_ en 'sp_Orden_Obtener' | alta | Reservado para sistema (SQL Server busca primero en master). Usar usp_<Entidad>_<Accion>. |
| INCUMPLE | 1 | - | Encabezado incompleto | alta | Falta en el comentario de encabezado: autor, fecha, descripción, historial. |
| INCUMPLE | 2 | - | Parámetro @ClienteId como (N)VARCHAR(MAX) | heuristica | Usar longitud precisa si el dominio es limitado. |
| INCUMPLE | 5 | 1 | SELECT * | alta | Especificar columnas explícitas. |
| INCUMPLE | 6 | 14 | NOLOCK / READ UNCOMMITTED | alta | Solo permitido en lectura no crítica con justificación documentada. Preferir RCSI. |
| INCUMPLE | 7 | 4 | ISNULL() en predicado WHERE | heuristica | Inhabilita índices. Reescribir con IS NULL / IS NOT NULL + comparación. OJO: verificar equivalencia del resultado (ver equivalencias-determinismo.md). |
| INCUMPLE | 7 | 4 | ISNULL() en predicado WHERE | heuristica | Inhabilita índices. Reescribir con IS NULL / IS NOT NULL + comparación. OJO: verificar equivalencia del resultado (ver equivalencias-determinismo.md). |

### Pendiente de revisión manual (el script no puede verificarlo)
- [7] PK/FK con el mismo tipo de dato
- [8] Toda FK con índice non-clustered
- [13] ORDER BY final respaldado por índice
- [15] Validaciones de front-end
- [18] Funciones escalares en SELECT masivo
- [21] Refactors demuestran equivalencia
- [22] Pre-agregación solo con funciones distributivas
- [23] Conversiones que pueden fallar usan TRY_CAST
- [24] BETWEEN → rango semiabierto declarado
- [27] TOP ordena por columna que el WHERE no fija
- [28] Funciones de ventana con desempate único
- [29] Clave clustered no aparece en INCLUDE
- [30] Índice filtrado no clavea la columna que filtra
- [32] Índice propuesto con consumidor verificado
- [33] Todas las definiciones del objeto revisadas (PROD/QA, init)
- [-] SQL dinámico construido dentro de cadenas (no analizado por el script)
