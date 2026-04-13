# EPIC-05: Gestión de Cursos y Comisiones

> **Issue**: #5 | **Milestone**: Fase 1 — Core Académico | **Labels**: epic, fase-1, priority:critical

## Contexto

Módulo fundacional del dominio académico. Los cursos y comisiones son la estructura organizativa sobre la que se montan ejercicios, submissions, y todo el flujo del alumno. Sin esto, no hay contexto académico.

## Alcance

### Backend
- Modelos SQLAlchemy: `courses`, `commissions`, `enrollments`
- Repositories con selectinload para relaciones
- Domain services: `CourseService`, `CommissionService`, `EnrollmentService`
- Endpoints REST:
  - `GET/POST /api/v1/courses` (docente/admin)
  - `GET/PUT/DELETE /api/v1/courses/{id}` (docente/admin)
  - `GET/POST /api/v1/courses/{id}/commissions` (docente/admin)
  - `GET/PUT/DELETE /api/v1/commissions/{id}` (docente/admin)
  - `POST /api/v1/commissions/{id}/enroll` (alumno)
  - `GET /api/v1/student/courses` (alumno — mis cursos inscriptos)
- Paginación estándar con `page`/`per_page`
- Seed data: extiende los scripts de EPIC-02 agregando 1 curso, 2 comisiones, enrollments de prueba

### Frontend
- **Docente/Admin**: pantalla ABM de cursos y comisiones (listado + crear + editar + eliminar)
- **Alumno**: pantalla "Mis Cursos" (cursos inscriptos, botón de inscripción)
- MSW handlers para estos endpoints

## Contratos

### Produce
- Endpoints REST de cursos/comisiones/enrollments
- Modelos `courses`, `commissions`, `enrollments` en schema `operational`
- Evento: `enrollment.created` (para futuras integraciones)

### Consume
- Auth: `get_current_user`, `require_role()` (de EPIC-03)
- DB: session factory, UoW, BaseRepository (de EPIC-02)
- Frontend: Design System, MSW, auth store (de EPIC-04, EPIC-03)

### Modelos (owner — schema: operational)
- `courses`: id (UUID PK), name (VARCHAR 255), description (TEXT), topic_taxonomy (JSONB, nullable), is_active (BOOL), created_at, updated_at
- `commissions`: id (UUID PK), course_id (FK → courses), teacher_id (UUID FK → users.id, NOT NULL), name (VARCHAR 100), year (SMALLINT), semester (SMALLINT CHECK 1-2), is_active (BOOL), created_at, updated_at
- `enrollments`: id (UUID PK), student_id (FK → users), commission_id (FK → commissions), enrolled_at (TIMESTAMPTZ), is_active (BOOL, default TRUE). UNIQUE(student_id, commission_id)

## Dependencias
- **Blocked by**: EPIC-01, EPIC-02, EPIC-03, EPIC-04
- **Blocks**: EPIC-06 (ejercicios pertenecen a comisiones)

## Stories

- [ ] Modelos SQLAlchemy: courses, commissions, enrollments + migración Alembic
- [ ] Repositories: CourseRepository, CommissionRepository, EnrollmentRepository
- [ ] Domain services con validación de negocio
- [ ] Endpoints REST para cursos (CRUD completo, paginado)
- [ ] Endpoints REST para comisiones (CRUD + enroll)
- [ ] Endpoint alumno: mis cursos inscriptos
- [ ] Frontend docente: ABM cursos y comisiones
- [ ] Frontend alumno: pantalla "Mis Cursos" con inscripción
- [ ] MSW handlers para desarrollo paralelo
- [ ] Seed data: extiende EPIC-02 con 1 curso, 2 comisiones, enrollments
- [ ] Tests de integración: CRUD + RBAC + paginación

## Criterio de Done

- Docente puede crear/editar/eliminar cursos y comisiones desde la UI
- Alumno puede ver cursos disponibles e inscribirse
- Todos los endpoints protegidos con RBAC
- Paginación funcional
- Tests de integración pasan

## Referencia
- `knowledge-base/02-arquitectura/02_modelo_de_datos.md`
- `knowledge-base/02-arquitectura/03_api_y_endpoints.md`
- `knowledge-base/01-negocio/04_reglas_de_negocio.md`
