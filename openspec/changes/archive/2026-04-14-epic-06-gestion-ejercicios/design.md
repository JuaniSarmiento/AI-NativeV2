## Context

EPIC-05 dejó cursos, comisiones y enrollments funcionando con CRUD, RBAC, y frontend. El Event Bus está configurado (EPIC-01) con streams incluyendo `events:submissions`. Los modelos Course y Commission existen en `shared/models/`. BaseRepository, UoW, auth dependencies, y response schemas están disponibles.

## Goals / Non-Goals

**Goals:**
- Exercise model con test_cases JSONB validado y topic_tags con GIN index
- Repository con filtros avanzados eficientes
- CRUD completo con RBAC
- Emisión de `reads_problem` al abrir ejercicio (alumno)
- UI docente para crear/editar ejercicios con test cases
- UI alumno para listar y ver detalle

**Non-Goals:**
- No implementar sandbox/ejecución de código (EPIC-07)
- No implementar submissions (EPIC-08)
- No implementar Monaco editor integrado (EPIC futura de frontend)
- No implementar markdown rendering avanzado (solo texto plano del enunciado por ahora)

## Decisions

### D1: Exercise model en `shared/models/` 

Igual que Course/Commission — Exercise es referenciado por submissions, tutor, cognitive. Va en shared para evitar imports circulares.

### D2: test_cases como JSONB con validación Pydantic

El campo `test_cases` es JSONB libre en PostgreSQL pero se valida en el service layer con un schema Pydantic `TestCaseSet` antes de persistir. Esto permite flexibilidad de schema sin perder validación.

### D3: topic_tags como TEXT[] con GIN index

`TEXT[]` nativo de PostgreSQL con operador `@>` (contains) para filtros. GIN index hace estas queries O(log n) en vez de seq scan. Más eficiente que JSONB para tags planos.

### D4: reads_problem via Event Bus

Cuando un alumno hace `GET /exercises/{id}`, el service escribe un evento `reads_problem` en `event_outbox`. El outbox worker lo publica a `events:submissions`. No bloquea el response — fire-and-forget dentro de la misma transacción.

### D5: Feature module structure

```
backend/app/features/exercises/
├── __init__.py
├── repositories.py
├── services.py
├── schemas.py
└── router.py
```

### D6: Frontend con filtros inline

La lista de ejercicios del alumno usa filtros inline (chips de dificultad, dropdown de topic) — no una página de búsqueda separada. Sigue el patrón minimalist-skill: table con border separators para listas, Cards double-bezel para detalle.

## Risks / Trade-offs

- **[Risk] test_cases schema evoluciona** → Mitigation: validación en service layer (no DB constraint), fácil de actualizar.
- **[Risk] GIN index en TEXT[] tiene overhead en writes** → Mitigation: exercises se crean/editan raramente vs se leen constantemente. Worth it.
- **[Risk] reads_problem duplicado si alumno refresca** → Mitigation: aceptable — Fase 3 deduplica por session/timestamp. Un refresh genuino es información válida.
