# Revisión: `<esquema>.<nombre_del_sp>`

**Dictamen:** ✅ Aprobado | ⚠️ Aprobado con observaciones | ❌ Requiere cambios
**Hallazgos:** CRÍTICO: n · INCUMPLE: n · RECOMENDADO: n
**Contexto asumido:** <volumen de filas, índices existentes, si el SP ya está en producción; o "no proporcionado">

## Hallazgos

| # | Sev. | Línea | Ítem | Hallazgo | Corrección |
|---|---|---|---|---|---|
| 1 | CRÍTICO | 42 | 12 | `CATCH` sin `ROLLBACK` | `IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;` |

(Ordenar por severidad y luego por línea. Agrupar repeticiones del mismo hallazgo en una fila con todas las líneas.)

## Riesgo sobre el resultado

<Solo si alguna corrección puede cambiar las filas o valores devueltos (ISNULL→IS NULL, NOT IN→NOT EXISTS, quitar NOLOCK, BETWEEN→rango, TOP sin ORDER BY). Explicar la diferencia y qué decisión se toma. Si ninguna lo cambia, escribir: "Las correcciones propuestas no alteran el resultado.">

## Pendiente de verificar

<Lo que no pudo confirmarse sin contexto: índices sobre columnas filtradas, tipos de las tablas referenciadas, consumidores del SP, definiciones gemelas PROD/QA.>

## Código corregido

<Solo si el usuario lo pidió o el dictamen es "Requiere cambios" y la corrección es directa. Versión completa del SP conforme al estándar.>
