# Seguridad y acceso a datos

> **Cuándo leer este archivo:** Leer cuando hay SQL dinámico, manejo de PII/datos financieros, contraseñas/hashes, permisos, EXECUTE AS o GRANT.
>
> Fuente: Política de Buenas Prácticas SQL Server de referencia v1.0. Cumplimiento obligatorio salvo donde diga "Recomendado".

### 6. Seguridad y Acceso a Datos

- Principio de mínimo privilegio: usuarios de aplicación nunca con DML directo sobre tablas; acceso solo vía SPs. Roles por función (`rol_lectura`, `rol_escritura`, `rol_admin`), no permisos directos. Auditar permisos al menos trimestralmente.
- Prevención de inyección SQL: nunca concatenar input de usuario en SQL; siempre `sp_executesql` con `@params`. Validar tipo y longitud de parámetros en el SP. Habilitar SQL Server Audit / Extended Events para accesos fallidos.
- Datos sensibles: cifrar PII/datos financieros con Always Encrypted o Column-Level Encryption. Nunca contraseñas en texto plano ni con hashes débiles (MD5, SHA1) — usar bcrypt o SHA-256 con salt ≥16 bytes. Row-Level Security (RLS) cuando distintos usuarios ven subconjuntos distintos de una misma tabla.
