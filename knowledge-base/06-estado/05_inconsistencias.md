# Log de Inconsistencias

**Plataforma AI-Native | UTN FRM**
Última actualización: 2026-04-10

---

## Propósito

Este documento registra inconsistencias detectadas entre artefactos del proyecto: cuando un archivo de especificación dice X y la implementación dice Y, o cuando dos especificaciones se contradicen entre sí.

El log se puebla principalmente por:
1. El script de validación de scaffold (`scripts/validate_scaffold.py`) al correr contra el codebase.
2. Desarrolladores que detectan inconsistencias manualmente durante code reviews.
3. Tests que fallan por discrepancias entre spec y código.

---

## Estado Actual

**El proyecto está en etapa de inicio.** No hay inconsistencias detectadas porque aún no existe código de implementación. Este log se activa a partir de la semana 3 cuando comienza el desarrollo de las fases.

> **Auditoría parcial 2026-04-12**: Revisión de 05-dx, 06-estado, 07-anexos contra decisiones canónicas. Corrigió timeout sandbox (5s→10s), JWT expire (30min→15min), estructura backend, modelo Anthropic, etc. **Sin embargo, esta auditoría no cubrió cross-folder ni las carpetas 01-04, dejando 50+ inconsistencias sin detectar.**
>
> **Auditoría completa 2026-04-13**: Lectura exhaustiva de los 34 archivos de las 7 carpetas + comparación cross-folder. Se encontraron y resolvieron 50+ inconsistencias incluyendo: exercises FK (commission→course), 3 catálogos de event_type incompatibles, campos de reflexión divergentes, DomainException→DomainError, hash_chain.py path, cognitive_metrics campos faltantes, Fase 4 naming, governance ownership, WS endpoint variants, env vars naming, healthcheck paths, y más. Detalle completo en `_resumen/00_cross_folder.md`.

---

## Formato de Entrada

Cada inconsistencia tiene el siguiente formato:

```
### INC-XXX: [Título descriptivo]

**Tipo**: Failure | Warning | Auto-fixed
**Severidad**: Crítico | Alto | Medio | Bajo
**Detectado**: YYYY-MM-DD [Manual | Script de validación | Test fallido]
**Estado**: Abierto | Resuelto | Descartado (con justificación)

**Archivo A**: [path relativo]
  Dice: [qué dice el archivo A]

**Archivo B**: [path relativo]  
  Dice: [qué dice el archivo B]

**Análisis**: Por qué son inconsistentes. Cuál de los dos es correcto.

**Resolución**: Cómo se resolvió. Qué archivo se actualizó.
**Fecha de resolución**: YYYY-MM-DD
**Resuelto por**: @username
```

---

## Tipos de Inconsistencia

### Failures (Fallos)

Inconsistencias que **rompen la funcionalidad** o crean comportamientos incorrectos. Deben resolverse antes del merge.

Ejemplos:
- La spec dice que el endpoint retorna `user_id` como string, pero el modelo Pydantic lo define como `UUID`.
- El schema de DB tiene una columna `difficulty` como `VARCHAR`, pero la spec dice que es `INTEGER`.
- El frontend espera `{ status: "ok", data: {...} }` pero el endpoint retorna `{ success: true, result: {...} }`.

### Warnings (Advertencias)

Inconsistencias que **no rompen funcionalidad** actualmente pero pueden causar problemas. Deben resolverse en el sprint siguiente.

Ejemplos:
- La documentación dice que el endpoint acepta `page` como query param, pero la implementación usa `offset`.
- El naming en la spec usa `exerciseId` (camelCase) pero la API retorna `exercise_id` (snake_case) sin conversión.
- Un test testea un comportamiento que difiere de lo documentado en el ADR correspondiente.

### Auto-fixed (Auto-corregidos)

Inconsistencias que el script de validación **corrigió automáticamente** sin intervención humana. Se registran para auditoría.

Ejemplos:
- Tabs vs spaces en un archivo de configuración.
- Orden de imports incorrecto (corregido por ruff --fix).
- Coma faltante en un archivo JSON de configuración.

---

## Registro de Inconsistencias

### Auditoría completa 2026-04-13

Se realizó una auditoría exhaustiva de las 7 carpetas del knowledge-base, leyendo cada archivo y comparando datos entre documentos. Se encontraron y resolvieron **40+ inconsistencias** agrupadas en:

- **01-negocio** (7 issues): FK exercises (commission→course), conteo backlog, cognitive_metrics incompleto, reflexión event_type, session_id en tutor_interactions, indicador cruzado post-MVP
- **02-arquitectura** (15 issues): exercises FK en modelo de datos y API, 3 catálogos de event_type incompatibles, reflexión campos divergentes, cognitive session lifecycle, DomainException→DomainError, event_hash vs current_hash, risk_assessments FK, cognitive_metrics campos faltantes
- **03-seguridad** (4 issues): rate limiting algoritmo (Token Bucket→Sliding Window), endpoint names en RBAC matrix, sandbox endpoint name/limits
- **04-infraestructura** (10 issues): schema analytics con tablas fantasma, exercises FK, tutor_interactions FK cross-schema, cognitive_events user_id extra, cognitive_metrics incompleto, governance_events y tutor_system_prompts simplificados, tablas faltantes (reflections, event_outbox, reasoning_records)
- **05-dx** (2 issues): hash_chain.py ubicación (core→features/cognitive)
- **07-anexos** (3 issues): hash_chain.py ubicación y campo hash→event_hash en glosario y estructura

Todos los fixes fueron aplicados directamente en los archivos afectados. Los resúmenes consolidados están en `knowledge-base/_resumen/`.

### Failures Abiertos

*Ninguno tras auditoría 2026-04-13.*

---

### Warnings Abiertos

*Ninguno tras auditoría 2026-04-13.*

---

### Resueltos / Cerrados

Ver auditoría 2026-04-13 arriba — 40+ items resueltos.

---

## Script de Validación de Scaffold

El script `scripts/validate_scaffold.py` verifica automáticamente consistencia entre:

1. **OpenAPI spec vs implementación FastAPI**
   - Todos los endpoints documentados en la spec existen en los routers
   - Los schemas de request/response coinciden entre spec e implementación
   - Los status codes declarados coinciden con los retornados

2. **Tipos TypeScript vs API responses**
   - Las interfaces TypeScript del frontend coinciden con los schemas de Pydantic del backend
   - No hay campos en el tipo TS que no existan en el schema de Pydantic
   - No hay campos obligatorios en Pydantic que sean opcionales en TS

3. **Modelos SQLAlchemy vs migraciones de Alembic**
   - Todas las columnas del modelo existen en las migraciones
   - Los tipos de datos coinciden
   - Los schemas de las tablas coinciden

4. **Convenciones de naming**
   - Archivos Python en snake_case
   - Archivos TypeScript en camelCase o PascalCase según corresponda
   - Nombres de tablas en plural
   - Nombres de modelos en singular PascalCase

### Cómo correr el script

```bash
# Desde la raíz del repositorio
python scripts/validate_scaffold.py

# Con output detallado
python scripts/validate_scaffold.py --verbose

# Solo verificar un módulo específico
python scripts/validate_scaffold.py --module exercises

# Auto-fix los problemas que pueden corregirse automáticamente
python scripts/validate_scaffold.py --fix
```

El script retorna:
- Exit code 0: sin failures (puede haber warnings)
- Exit code 1: hay uno o más failures que deben resolverse manualmente

En CI, el script corre en cada PR y bloquea el merge si hay failures.

---

## Inconsistencias Frecuentes en Este Stack

Lista de inconsistencias comunes en proyectos FastAPI + React que vale la pena revisar periódicamente:

### Desincronización de tipos UUID/string

FastAPI serializa UUIDs como strings en el JSON response. El frontend TypeScript define estos como `string`. Si alguien en el backend cambia un campo a UUID y lo tipea como UUID (en lugar de `str`) en el schema Pydantic, el output puede cambiar de formato.

**Validación**: El script verifica que todos los campos UUID en los schemas Pydantic tengan `json_schema_extra={"format": "uuid"}` o sean tipados como `str` en los schemas de response.

### snake_case vs camelCase en JSON

Por convención, la API retorna JSON en snake_case (por defecto en Pydantic). El frontend trabaja en camelCase. Hay dos opciones para manejar la conversión:
1. El cliente HTTP del frontend convierte automáticamente (usando `axios-case-converter` o un interceptor manual).
2. Pydantic usa `model_config = ConfigDict(alias_generator=to_camel)` para generar aliases camelCase.

**El proyecto usa la opción 1**: el cliente HTTP convierte snake_case a camelCase en los responses y camelCase a snake_case en los requests.

Si alguien configura Pydantic para generar camelCase directamente, hay una inconsistencia doble (doble conversión).

### Timestamps: ISO 8601 vs Unix timestamp

La convención del proyecto es ISO 8601 UTC para todos los timestamps (`"2026-04-10T15:30:00Z"`). Si algún endpoint retorna Unix timestamp (número), hay una inconsistencia con el frontend que espera string ISO.

**Validación**: El script verifica que todos los campos `datetime` en los schemas Pydantic no tengan `json_encoders` que los conviertan a timestamp numérico.

### Paginación: `page`/`per_page` vs `offset`/`limit`

La API usa `?page=1&per_page=20` (ver convenciones). Si alguien implementa un endpoint nuevo con `?offset=0&limit=20`, hay inconsistencia con el frontend que solo maneja el patrón `page`/`per_page`.

---

## Historial de Ejecuciones del Script de Validación

*Tabla para actualizar cada vez que se corre el script en CI.*

| Fecha | Failures | Warnings | Auto-fixed | Acción tomada |
|---|---|---|---|---|
| 2026-04-10 | N/A | N/A | N/A | Proyecto no iniciado |
