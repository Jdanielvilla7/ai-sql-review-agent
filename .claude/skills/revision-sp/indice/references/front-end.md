# Front-end y capa de aplicación

> **Cuándo leer este archivo:** Leer solo si se revisa código de aplicación que llama a la BD o validaciones de entrada del cliente.
>
> Fuente: Política de Buenas Prácticas SQL Server de referencia v1.0. Cumplimiento obligatorio salvo donde diga "Recomendado".

### 8. Normalización en Front-End y Capa de Aplicación

- Validar tipo, longitud y formato en cliente, pero **siempre replicar validaciones críticas en el servidor** (el client-side nunca es suficiente por sí solo).
- Fechas: validar coherencia (nacimiento < actual; fin > inicio). Texto: Uppercase/Title Case según estándar, trim de espacios — no delegar esto al back-end ni a la BD.
- Limitar longitud de inputs a la longitud máxima de la columna destino.
- Sanitizar inputs contra XSS/inyección HTML/SQL desde el front-end. Nunca confiar en campos `hidden` para valores críticos de negocio (IDs, montos) — validar en servidor. HTTPS siempre; nunca datos sensibles en query strings.
- Toda llamada a BD desde la aplicación vía SPs parametrizados — no construir SQL en la capa de aplicación salvo excepción documentada. Reintentos con backoff exponencial para errores transitorios. Cerrar siempre conexiones (connection pooling correctamente configurado). Errores de BD manejados con mensajes amigables, sin exponer detalles técnicos.
