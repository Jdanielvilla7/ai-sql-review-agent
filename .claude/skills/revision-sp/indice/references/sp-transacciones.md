# Procedimientos almacenados, funciones, transacciones y concurrencia

> **Cuándo leer este archivo:** Leer en TODA revisión de SP: SET NOCOUNT, TRY/CATCH, parámetros, naming usp_, UDFs, transacciones y aislamiento.
>
> Fuente: Política de Buenas Prácticas SQL Server de referencia v1.0. Cumplimiento obligatorio salvo donde diga "Recomendado".

### 4. Procedimientos Almacenados y Funciones

- `SET NOCOUNT ON` al inicio de todo SP.
- Encapsular en `BEGIN TRY / BEGIN CATCH` con `ROLLBACK` explícito ante fallo.
- Tipos de parámetro precisos — nunca `NVARCHAR(MAX)` para un dominio limitado.
- No reutilizar parámetros de entrada para asignaciones intermedias (riesgo de parameter sniffing problemático). Mitigación: `OPTION (RECOMPILE)` selectivo o variables locales.
- Naming: `usp_<Entidad>_<Accion>` (ej. `usp_Factura_Crear`, `usp_Pedido_ObtenerPorCliente`).
- Variables/parámetros declarados al inicio, con comentario de propósito, formato `@NombreAux` para variables auxiliares.
- Evitar funciones escalares (Scalar UDFs) en SELECT/WHERE sobre tablas grandes (fila a fila, no paralelizables pre-SS2019). Preferir Inline TVFs. Sin efectos secundarios (DML) dentro de funciones usadas en SELECT.
- CTEs para legibilidad, sin asumir materialización (el optimizador puede reevaluarlo). Si un CTE se referencia múltiples veces y el costo de reevaluación es alto, materializar en `#Temp`. Vistas indexadas solo con evaluación de un DBA (restricciones significativas).

### 5. Transacciones y Concurrencia

- Transacciones lo más cortas posible. Siempre cerrar con `COMMIT` o `ROLLBACK` dentro del mismo bloque `TRY/CATCH`. Verificar `@@TRANCOUNT > 0` antes de `ROLLBACK`. Nunca interacción con el usuario dentro de una transacción abierta.

```sql
BEGIN TRY
    BEGIN TRANSACTION
    -- operaciones DML
    COMMIT TRANSACTION
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION
    THROW
END CATCH
```

**Niveles de aislamiento**

| Nivel | Dirty Read | Non-Repeatable Read | Phantom Read | Uso recomendado |
|---|---|---|---|---|
| READ UNCOMMITTED (NOLOCK) | Sí | Sí | Sí | Solo reportes no críticos |
| READ COMMITTED (default) | No | Sí | Sí | Transacciones OLTP estándar |
| RCSI (habilitar en BD) | No | No* | No* | Alternativa a NOLOCK masivo |
| REPEATABLE READ | No | No | Sí | Lecturas que requieren estabilidad |
| SERIALIZABLE | No | No | No | Solo cuando la exactitud es crítica |

- Deadlocks: habilitar Trace Flag 1222 o Extended Events en producción. Acceder a tablas en el mismo orden entre transacciones concurrentes. Revisar periódicamente `sys.dm_exec_requests` y `sys.dm_os_waiting_tasks`.
