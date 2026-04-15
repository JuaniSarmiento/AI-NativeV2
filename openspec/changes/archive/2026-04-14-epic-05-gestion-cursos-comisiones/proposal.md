## Why

La Fase 0 dejó infra, auth, design system y app shell listos. Pero no hay dominio académico — sin cursos y comisiones no hay dónde montar ejercicios ni contexto para el tutor. Esta es la primera EPIC de Fase 1: el CRUD fundacional que estructura todo lo que viene.

## What Changes

### Backend
- Modelo `Enrollment` + migración Alembic 003
- Repositories concretos: CourseRepository, CommissionRepository, EnrollmentRepository
- Domain services: CourseService, CommissionService, EnrollmentService
- Endpoints REST: CRUD cursos, CRUD comisiones, enroll, mis cursos
- Evento outbox: `enrollment.created`
- Seed data extendido con enrollments

### Frontend
- Docente: pantalla ABM cursos (listado + crear/editar/eliminar)
- Docente: pantalla ABM comisiones dentro de un curso
- Alumno: pantalla "Mis Cursos" con inscripción
- MSW handlers para todos los endpoints

## Capabilities

### New Capabilities
- `enrollment-model`: Modelo Enrollment en schema operational con migración, unique constraint (student_id, commission_id)
- `courses-api`: Endpoints REST CRUD cursos + comisiones + enroll + mis-cursos con RBAC y paginación
- `courses-services`: Domain services para cursos, comisiones, enrollments con validación de negocio
- `courses-frontend`: Pantallas ABM docente + Mis Cursos alumno usando design system components

### Modified Capabilities
- `monorepo-structure`: Se agregan features/courses backend y frontend

## Impact

- **Backend**: `backend/app/features/courses/`, `backend/app/shared/models/enrollment.py`, `backend/alembic/versions/003_*`
- **Frontend**: `frontend/src/features/courses/`, `frontend/src/mocks/handlers/courses.ts`
- **Database**: Tabla `enrollments` nueva en schema operational
- **Downstream**: Desbloquea EPIC-06 (ejercicios pertenecen a cursos)
