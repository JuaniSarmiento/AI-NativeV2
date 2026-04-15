## Context

EPIC-02 creó modelos Course y Commission en `shared/models/`. EPIC-03 creó auth con `get_current_user` y `require_role()`. EPIC-04 creó el App Shell con sidebar, design system components (Button, Input, Card, Modal), MSW, y response schemas (`StandardResponse[T]`, `PaginatedResponse[T]`). El BaseRepository genérico existe en `shared/repositories/base.py`.

No existen: modelo Enrollment, repos concretos, services, router de courses, ni UI de cursos.

## Goals / Non-Goals

**Goals:**
- Enrollment model + migración
- Repos concretos que hereden BaseRepository
- Services con validación de negocio (no lógica en routers)
- CRUD completo con RBAC (docente/admin crean, alumno lee e inscribe)
- UI docente para ABM cursos/comisiones
- UI alumno para ver cursos e inscribirse
- MSW handlers para desarrollo paralelo

**Non-Goals:**
- No implementar ejercicios (EPIC-06)
- No implementar submissions ni sandbox
- No implementar dashboard de métricas
- No implementar búsqueda full-text de cursos

## Decisions

### D1: Feature module completo en `features/courses/`

```
backend/app/features/courses/
├── __init__.py
├── models.py          # Enrollment model (Course/Commission ya en shared/)
├── repositories.py    # CourseRepo, CommissionRepo, EnrollmentRepo
├── services.py        # CourseService, CommissionService, EnrollmentService
├── schemas.py         # Pydantic v2 request/response
└── router.py          # Thin router with RBAC dependencies
```

Course y Commission models quedan en `shared/models/` porque los usan múltiples features. Enrollment va en `features/courses/models.py` porque es específico del dominio académico.

### D2: Router thin — toda la lógica en services

El router solo: valida input (Pydantic), extrae user (dependency), llama service, retorna StandardResponse. Zero lógica de negocio. Los services validan ownership, enrollment duplicado, etc.

### D3: Enrollment con evento outbox

Al crear un enrollment, el service escribe un evento `enrollment.created` en la tabla `event_outbox` dentro de la misma transacción (UoW). El outbox worker lo publicará a Redis Streams. Esto prepara la integración con Fase 3 (motor cognitivo).

### D4: Frontend con Card + Table pattern

La UI de docente usa Card (double-bezel) para el form de crear/editar y una tabla simple con border-bottom separators (per minimalist-skill — no cards para datos tabulares). La UI de alumno usa Cards para cada curso con botón de inscripción.

### D5: Paginación estándar

Todos los list endpoints usan `page`/`per_page` query params. El repo `list()` ya soporta esto. El response usa `PaginatedResponse[T]` con meta.

## Risks / Trade-offs

- **[Risk] Enrollment duplicado** → Mitigation: UNIQUE constraint (student_id, commission_id) + service check antes de insertar.
- **[Risk] Docente editando curso ajeno** → Mitigation: Service valida que el teacher_id de la comisión matchee el current_user. Admin bypasea.
- **[Risk] Alumno inscribiéndose a comisión inactiva** → Mitigation: Service valida `commission.is_active` y `course.is_active`.
