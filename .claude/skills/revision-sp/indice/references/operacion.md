# Mantenimiento y monitoreo

> **Cuándo leer este archivo:** Leer solo si la tarea es de backups, Query Store, jobs o alertas. No aplica a la revisión de un SP individual.
>
> Fuente: Política de Buenas Prácticas SQL Server de referencia v1.0. Cumplimiento obligatorio salvo donde diga "Recomendado".

### 7. Mantenimiento y Monitoreo

- Backups definidos según RPO/RTO del sistema. Validar con `RESTORE VERIFYONLY` y restore de prueba en ambiente separado. Jobs de mantenimiento: rebuild/reorganize de índices, actualización de estadísticas, limpieza de logs de error.
- Query Store habilitado cuando aplique (`ALTER DATABASE [BD] SET QUERY_STORE = ON`). Revisar periódicamente "Top Resource Consuming Queries" para detectar regresiones tras cambios de plan.

**Alertas y métricas clave**

| Métrica | Umbral de alerta |
|---|---|
| CPU SQL Server | > umbral definido por sistema |
| Memoria disponible | < umbral definido por sistema |
| Tamaño de log de transacciones | > umbral definido por sistema |
| Fragmentación de índices | > umbral definido por sistema |
| Duración de consultas lentas | > umbral definido por sistema |
| Espacio en disco | < umbral definido por sistema |
