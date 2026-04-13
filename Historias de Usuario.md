# Historias de Usuario — Plataforma AI-Native

**UTN FRM | Sistema Pedagógico para Enseñanza de Programación**
Última actualización: 2026-04-10
Versión: 1.0

---

## Índice

- [EPIC 0 — Fundación Compartida](#epic-0--fundación-compartida-semanas-1-2)
- [EPIC 1 — Core Académico + Sandbox](#epic-1--core-académico--sandbox-semanas-3-12)
- [EPIC 2 — Tutor IA Socrático](#epic-2--tutor-ia-socrático-semanas-3-12)
- [EPIC 3 — Motor Cognitivo + Evaluación](#epic-3--motor-cognitivo--evaluación-semanas-3-12)
- [EPIC 4 — Frontend Completo](#epic-4--frontend-completo-semanas-3-14)

---

## Convenciones

- **Prioridad P0**: Bloqueante. Sin esto el sistema no funciona.
- **Prioridad P1**: Crítico. Necesario para la funcionalidad principal del EPIC.
- **Prioridad P2**: Importante. Agrega valor significativo, puede estar en el alcance inicial.
- **Prioridad P3**: Deseable. Puede diferirse a una segunda iteración.

**Referencia de Reglas de Negocio (RN)**: ver `knowledge-base/01-negocio/04_reglas_de_negocio.md`
**Referencia de Reglas Operativas (RO)**: ver mismo documento, sección "Reglas Operativas"

---

## EPIC 0 — Fundación Compartida (Semanas 1-2)

> **Objetivo**: Construir la base común para que los 4 devs trabajen en paralelo con confianza.
> Todo el equipo trabaja en simultáneo en este EPIC.

---

### HU-001 — Setup del Monorepo

**Título**: Estructura de monorepo con directorios separados por dominio

**Como** desarrollador del equipo,
**quiero** tener un monorepo correctamente estructurado con `/backend`, `/frontend`, `/shared`, `/infra`,
**para que** cada fase tenga un espacio de trabajo aislado y no haya colisiones de código ni de dependencias entre dominios.

#### Criterios de Aceptación

- [ ] El repositorio tiene la estructura `/backend`, `/frontend`, `/shared`, `/infra` en la raíz.
- [ ] Existe un `.gitignore` raíz que cubre Python (`.venv`, `__pycache__`, `.pytest_cache`) y Node (`node_modules`, `dist`, `.vite`).
- [ ] Existe un `README.md` raíz con instrucciones de inicio rápido.
- [ ] Existe un `pyproject.toml` en `/backend` con dependencias FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic 2, pytest, ruff, mypy.
- [ ] Existe un `package.json` en `/frontend` con React 19, Vite, TypeScript 5, Zustand 5, TailwindCSS 4, Vitest, Playwright.
- [ ] El directorio `/shared` tiene un `README.md` indicando qué va ahí (contratos OpenAPI, tipos compartidos).
- [ ] El directorio `/infra` contiene el `docker-compose.yml` inicial.
- [ ] Existe un pre-commit hook configurado con `commitlint` que rechaza commits que no siguen Conventional Commits.

#### Reglas de Negocio Referenciadas

- RN-8: Propiedad de datos por fase — la separación de directorios refleja la separación de ownership.

#### Prioridad

**P0** — Bloqueante para todo el resto del proyecto.

#### Dependencias

Ninguna. Es la primera historia.

---

### HU-002 — Docker Compose de Desarrollo

**Título**: Entorno de desarrollo completo en un solo comando

**Como** desarrollador,
**quiero** levantar todo el entorno de desarrollo (API + base de datos + Redis + frontend) con `docker compose up`,
**para que** cualquier desarrollador pueda empezar a trabajar en minutos sin configurar nada manualmente.

#### Criterios de Aceptación

- [ ] `docker compose up` levanta exitosamente los servicios: `api` (puerto 8000), `db` (PostgreSQL 16, puerto 5432), `redis` (Redis 7, puerto 6379), `frontend` (Vite, puerto 5173).
- [ ] El servicio `api` usa hot reload: al cambiar un archivo `.py` en `/backend`, el servidor se reinicia automáticamente sin reconstruir el contenedor.
- [ ] El servicio `frontend` usa HMR (Hot Module Replacement): al cambiar un archivo `.tsx`, el browser se actualiza sin recargar.
- [ ] Las variables de entorno se cargan desde un archivo `.env` local (no commiteado). Existe un `.env.example` con todas las variables necesarias y valores de ejemplo.
- [ ] Existe un `Makefile` o `justfile` con comandos `make up`, `make down`, `make logs`, `make shell-api`, `make shell-db`.
- [ ] `GET http://localhost:8000/api/v1/health` retorna `{"status": "ok"}`.
- [ ] `GET http://localhost:5173` carga la aplicación React.
- [ ] Los volúmenes de PostgreSQL persisten entre reinicios del contenedor (`docker compose down` + `docker compose up` no borra los datos).
- [ ] `docker compose down -v` borra los datos (para reset limpio en desarrollo).

#### Reglas de Negocio Referenciadas

Ninguna directamente. Es infraestructura.

#### Prioridad

**P0** — Bloqueante para el resto del equipo.

#### Dependencias

- HU-001 (estructura del monorepo debe existir)

---

### HU-003 — Schemas de Base de Datos y Modelos Iniciales

**Título**: PostgreSQL con 4 schemas separados y modelos base

**Como** desarrollador de cualquier fase,
**quiero** tener los 4 schemas de PostgreSQL creados (`operational`, `cognitive`, `governance`, `analytics`) con sus modelos base,
**para que** cada dominio tenga su espacio de datos aislado y pueda operar sin interferir con los demás.

#### Criterios de Aceptación

- [ ] Al correr las migraciones de Alembic (`alembic upgrade head`), se crean los 4 schemas en PostgreSQL.
- [ ] Schema `operational` contiene las tablas: `users`, `courses`, `commissions`, `exercises`, `submissions`, `code_snapshots`, `enrollments`, `tutor_interactions`.
- [ ] Schema `cognitive` contiene las tablas: `cognitive_sessions`, `cognitive_events`, `cognitive_metrics`, `reasoning_records`, `risk_assessments`.
- [ ] Schema `governance` contiene las tablas: `governance_events`, `tutor_system_prompts`.
- [ ] Schema `analytics` contiene las tablas: `student_metrics`, `exercise_attempts`, `course_stats`.
- [ ] Todos los modelos tienen `id` (UUID, server_default), `created_at`, `updated_at`.
- [ ] Las tablas que soportan soft delete tienen `is_active` (bool) y `deleted_at` (nullable datetime). Esto incluye: `users`, `courses`, `commissions`, `exercises`, `submissions`, `enrollments`.
- [ ] `cognitive_events` NO tiene soft delete (los eventos del CTR son inmutables por RN-7).
- [ ] Los modelos SQLAlchemy tienen `__table_args__ = {"schema": "xxx"}` correctamente especificado.
- [ ] El archivo `backend/app/shared/models/` está organizado por schema (`operational.py`, `cognitive.py`, `governance.py`, `analytics.py`).
- [ ] Las migraciones de Alembic están en `backend/alembic/versions/` con prefijo numérico secuencial.
- [ ] `alembic current` muestra el estado correcto de las migraciones.

#### Reglas de Negocio Referenciadas

- RN-7: El CTR es inmutable post-cierre — `cognitive_events` no tiene soft delete.
- RN-8: Propiedad de datos por fase — cada schema es propiedad de una sola fase.
- RO-6: Snapshots automáticos — `code_snapshots` debe existir con `edit_distance_from_previous`.

#### Prioridad

**P0** — Bloqueante para HU-004 a HU-007 y para el trabajo paralelo de las fases 1-4.

#### Dependencias

- HU-002 (Docker Compose debe estar levantado)

---

### HU-004 — Autenticación JWT con RBAC

**Título**: Sistema de autenticación JWT con roles alumno/docente/admin

**Como** usuario del sistema,
**quiero** poder registrarme, iniciar sesión y obtener tokens de acceso,
**para que** el sistema pueda identificarme y darme acceso solo a las funcionalidades correspondientes a mi rol.

#### Criterios de Aceptación

- [ ] `POST /api/v1/auth/register` crea un usuario nuevo con rol `alumno` por defecto. Retorna 201 con los datos del usuario (sin contraseña).
- [ ] `POST /api/v1/auth/login` retorna `access_token` (JWT, expira en 15 minutos) y `refresh_token` (JWT opaco, expira en 7 días).
- [ ] `POST /api/v1/auth/refresh` acepta un `refresh_token` válido y retorna un nuevo `access_token` + nuevo `refresh_token` (rotación).
- [ ] `POST /api/v1/auth/logout` invalida el `refresh_token` en Redis (blacklist).
- [ ] `GET /api/v1/auth/me` retorna el perfil del usuario autenticado.
- [ ] Los endpoints protegidos retornan 401 si el `Authorization: Bearer <token>` está ausente o el token expiró.
- [ ] Los endpoints con restricción de rol retornan 403 si el usuario tiene un rol insuficiente.
- [ ] Las contraseñas se almacenan con bcrypt (nunca en texto plano).
- [ ] Los passwords tienen validación: mínimo 8 caracteres.
- [ ] El payload del JWT incluye: `sub` (user_id), `role`, `email`, `exp`.
- [ ] La dependency `get_current_user` extrae el usuario del JWT y lo inyecta en los routers.
- [ ] La dependency `require_role("docente")` retorna 403 si el usuario no tiene el rol requerido.
- [ ] Existe un test de integración que verifica que el flujo completo login → access → refresh → logout funciona.

#### Reglas de Negocio Referenciadas

- RO-2: Rate limiting del tutor (la infrastructure de rate limiting se sienta sobre el sistema de auth).

#### Prioridad

**P0** — Bloqueante para cualquier endpoint protegido.

#### Dependencias

- HU-003 (tabla `users` en `operational` schema)

---

### HU-005 — OpenAPI Spec y Tipos TypeScript Autogenerados

**Título**: Contrato de API unificado con tipos TypeScript auto-generados

**Como** desarrollador de frontend (Fase 4),
**quiero** tener acceso a una OpenAPI spec completa y tipos TypeScript generados automáticamente a partir de ella,
**para que** pueda trabajar en el frontend con seguridad de tipos sin esperar que los endpoints de backend estén implementados.

#### Criterios de Aceptación

- [ ] `GET /api/v1/openapi.json` retorna la spec OpenAPI 3.0 completa de todos los endpoints de la API.
- [ ] La documentación interactiva está disponible en `/docs` (Swagger UI) y `/redoc`.
- [ ] Todos los endpoints tienen: `summary`, `description`, `response_model` correctamente tipado, `tags` por dominio (auth, courses, exercises, tutor, cognitive, governance).
- [ ] Todos los schemas de request y response tienen validaciones documentadas (min/max, regex, enum values).
- [ ] Existe un script `shared/generate-types.sh` (o NPM script) que llama a `openapi-typescript` y genera `shared/types/api.d.ts`.
- [ ] El archivo `shared/types/api.d.ts` se regenera automáticamente en el CI cuando cambia `openapi.json`.
- [ ] El frontend importa los tipos desde `@shared/types/api` en lugar de definirlos manualmente.
- [ ] El proceso de generación tarda menos de 30 segundos.
- [ ] Los tipos generados incluyen: todos los modelos de request/response de todas las fases, enums de dominio (UserRole, ExerciseDifficulty, N4Level, RiskLevel).

#### Reglas de Negocio Referenciadas

- RN-8: Propiedad de datos — los contratos de API son la interfaz entre dominios.

#### Prioridad

**P1** — Crítico para el desarrollo paralelo del frontend.

#### Dependencias

- HU-003 (schemas de DB → modelos SQLAlchemy → schemas Pydantic → OpenAPI)

---

### HU-006 — Pipeline de CI en GitHub Actions

**Título**: Pipeline de Integración Continua que valida cada PR

**Como** equipo de desarrollo,
**quiero** un pipeline de CI que corra automáticamente en cada push y PR,
**para que** los errores de lint, tipado y tests se detecten antes de llegar a `main`.

#### Criterios de Aceptación

- [ ] El pipeline corre en todo push a cualquier branch y en todo PR hacia `main`.
- [ ] Job `lint-backend`: corre `ruff check .` y `mypy app/`. Falla si hay errores.
- [ ] Job `lint-frontend`: corre `eslint` y `prettier --check`. Falla si hay errores.
- [ ] Job `test-unit`: corre `pytest tests/unit/ -v` con cobertura. Falla si coverage < 80% en módulos core.
- [ ] Job `test-integration`: corre `pytest tests/integration/ -v` con testcontainers (PostgreSQL real). Falla si algún test falla.
- [ ] Job `test-frontend`: corre `vitest run` con coverage. Falla si coverage < 80%.
- [ ] Job `build-check`: verifica que el frontend buildea (`vite build`) sin errores TypeScript.
- [ ] Los jobs de `test-integration` y `test-frontend` tienen caché de dependencias para acelerar la ejecución.
- [ ] El pipeline completo (sin E2E) no debe tardar más de 10 minutos.
- [ ] Se muestran los resultados de coverage como comentario en el PR (GitHub Actions comment).
- [ ] El merge a `main` está bloqueado si el CI no pasa (Branch Protection Rule).

#### Reglas de Negocio Referenciadas

Ninguna directamente. Es infraestructura de calidad.

#### Prioridad

**P1** — Crítico para mantener la calidad del código en un equipo de 4.

#### Dependencias

- HU-001 (estructura del repo)

---

### HU-007 — Seed Data de Desarrollo

**Título**: Datos de prueba iniciales para desarrollo local

**Como** desarrollador,
**quiero** tener datos de prueba cargados automáticamente al iniciar el entorno de desarrollo,
**para que** pueda probar el sistema con datos realistas sin tener que crear datos manualmente cada vez.

#### Criterios de Aceptación

- [ ] Existe un script `backend/scripts/seed.py` que es idempotente (puede correrse múltiples veces sin duplicar datos).
- [ ] El seed crea al menos: 1 usuario `admin`, 1 usuario `docente` (con email `docente@utn.edu.ar`, password `docente123dev`), 2 usuarios `alumno` (con emails `alumno1@utn.edu.ar` y `alumno2@utn.edu.ar`, password `alumno123dev`).
- [ ] El seed crea: 1 curso ("Algoritmos y Estructuras de Datos"), 1 comisión activa asignada al docente del seed.
- [ ] El seed crea al menos 3 ejercicios con distintos niveles de dificultad: dificultad 1 ("Hello World funcional"), dificultad 2 ("Fibonacci iterativo"), dificultad 3 ("Árbol binario de búsqueda").
- [ ] Los ejercicios tienen `test_cases` en formato JSONB con al menos 3 casos de prueba cada uno.
- [ ] Los 2 usuarios alumno están inscriptos (enrollment) en la comisión del seed.
- [ ] El seed crea 1 versión del system prompt del tutor socrático como "active = true" con semver `1.0.0`.
- [ ] El seed se puede correr con `make seed` o `python scripts/seed.py`.
- [ ] Al correr el seed por segunda vez, no se crean duplicados (verifica por email/nombre antes de insertar).
- [ ] El seed incluye comentarios explicativos del propósito de cada dato.

#### Reglas de Negocio Referenciadas

- RO-4: Versionado de prompts del tutor — el seed crea la versión inicial del system prompt.

#### Prioridad

**P1** — Importante para el desarrollo ágil y las demos.

#### Dependencias

- HU-003 (tablas deben existir)
- HU-004 (modelo de usuario con roles)

---

## EPIC 1 — Core Académico + Sandbox (Semanas 3-12)

> **Objetivo**: CRUD de cursos y ejercicios, flujo de submission, sandbox seguro.
> **Schema owner**: `operational`
> **Dev asignado**: Fase 1

---

### HU-008 — CRUD de Cursos y Comisiones

**Título**: Gestión de cursos y comisiones por docentes y admins

**Como** docente,
**quiero** poder crear, ver, editar y desactivar cursos y comisiones,
**para que** pueda organizar el contenido educativo y asignar alumnos a grupos de trabajo.

#### Criterios de Aceptación

- [ ] `POST /api/v1/courses` (requiere rol `docente` o `admin`) crea un nuevo curso. Retorna 201 con el curso creado.
- [ ] `GET /api/v1/courses` (requiere autenticación) lista los cursos activos con paginación (`?page=1&per_page=20`).
- [ ] `GET /api/v1/courses/{id}` retorna el detalle de un curso con sus comisiones.
- [ ] `PATCH /api/v1/courses/{id}` (requiere rol `docente` dueño o `admin`) actualiza campos del curso.
- [ ] `DELETE /api/v1/courses/{id}` (requiere rol `admin`) hace soft delete del curso.
- [ ] `POST /api/v1/courses/{course_id}/commissions` crea una comisión para el curso.
- [ ] `GET /api/v1/courses/{course_id}/commissions` lista las comisiones del curso.
- [ ] Un alumno solo puede ver cursos en los que está inscripto.
- [ ] Un docente puede ver todos los cursos que gestiona.
- [ ] Los cursos desactivados (soft delete) no aparecen en los listados normales.
- [ ] Existe al menos 1 test unitario por endpoint de happy path y 1 por edge case (ej: curso no encontrado → 404).

#### Reglas de Negocio Referenciadas

- RN-8: Propiedad de datos por fase — solo el endpoint de courses puede escribir en las tablas de courses.

#### Prioridad

**P1** — Base de toda la estructura académica.

#### Dependencias

- HU-004 (autenticación y RBAC)
- HU-003 (tablas en schema `operational`)

---

### HU-009 — CRUD de Ejercicios y Enrollments

**Título**: Gestión de ejercicios por docentes y inscripción de alumnos

**Como** docente,
**quiero** poder crear, editar y publicar ejercicios con test cases, y gestionar las inscripciones de alumnos en comisiones,
**para que** los alumnos tengan acceso a los ejercicios correspondientes a su comisión.

#### Criterios de Aceptación

- [ ] `POST /api/v1/exercises` (requiere rol `docente` o `admin`) crea un ejercicio con: `title`, `description` (markdown), `difficulty` (1-4), `topic_taxonomy` (JSONB), `starter_code` (Python), `test_cases` (JSONB array), `constraints` (texto libre).
- [ ] `GET /api/v1/exercises` lista ejercicios del docente (docente) o inscriptos (alumno), con filtros `?difficulty=N&topic=X`.
- [ ] `GET /api/v1/exercises/{id}` retorna el ejercicio completo. El alumno ve `description`, `starter_code`; el docente también ve `test_cases` y `constraints` completos.
- [ ] `PATCH /api/v1/exercises/{id}` (solo docente dueño o admin) permite actualizar todos los campos.
- [ ] `DELETE /api/v1/exercises/{id}` hace soft delete. Un ejercicio con submissions no puede borrarse (retorna 409).
- [ ] `POST /api/v1/commissions/{id}/enrollments` inscribe un alumno en una comisión (rol docente o admin).
- [ ] `GET /api/v1/commissions/{id}/enrollments` lista los alumnos inscriptos en la comisión.
- [ ] `DELETE /api/v1/commissions/{id}/enrollments/{student_id}` desincribe un alumno.
- [ ] Un alumno no puede ver ejercicios de cursos en los que no está inscripto.
- [ ] Los ejercicios tienen `topic_taxonomy` validado como JSONB con keys predefinidos (ej: `{area: "arrays", subtopic: "sorting"}`).

#### Reglas de Negocio Referenciadas

- RN-8: Solo Fase 1 puede escribir en tablas de `operational` (ejercicios, enrollments).

#### Prioridad

**P1** — Crítico para que los alumnos puedan trabajar.

#### Dependencias

- HU-008 (cursos y comisiones deben existir)

---

### HU-010 — Flujo de Submission

**Título**: Ciclo completo de entrega de ejercicio (draft → ejecutar → enviar)

**Como** alumno,
**quiero** poder escribir código, ejecutarlo en un sandbox, y enviar mi solución final como submission,
**para que** el docente pueda evaluar mi trabajo y el sistema registre mi proceso.

#### Criterios de Aceptación

- [ ] `POST /api/v1/exercises/{id}/submissions` (rol alumno) crea una submission en estado `draft`.
- [ ] `POST /api/v1/exercises/{id}/run` ejecuta el código actual del alumno en el sandbox y retorna stdout, stderr, runtime_ms, y los resultados de los test cases (pass/fail por caso).
- [ ] `POST /api/v1/submissions/{id}/submit` cambia el estado de `draft` a `submitted`. No se puede deshacer.
- [ ] Un alumno solo puede tener 1 submission en estado `draft` por ejercicio a la vez.
- [ ] Si el alumno intenta hacer submit sin haber ejecutado el código al menos una vez, el sistema lo permite (no es obligatorio ejecutar antes de enviar).
- [ ] `GET /api/v1/exercises/{id}/submissions/me` retorna el historial de submissions del alumno para ese ejercicio.
- [ ] `GET /api/v1/exercises/{id}/submissions` (rol docente) retorna todas las submissions de todos los alumnos para ese ejercicio.
- [ ] Una submission tiene: `student_id`, `exercise_id`, `code`, `runtime_ms`, `stdout`, `stderr`, `test_results` (JSONB), `score` (null hasta evaluación), `status`.
- [ ] Al hacer submit, se emite un evento `SubmissionCreated` al Event Bus (Redis Stream `events:submissions`) para que Fase 3 lo consuma.

#### Reglas de Negocio Referenciadas

- RO-5: Reflexión post-ejercicio — al enviar submission, el sistema debe disparar el flujo de reflexión.
- RO-6: Snapshots automáticos — los snapshots se crean en paralelo al flujo de submission.

#### Prioridad

**P1** — Flujo central del alumno.

#### Dependencias

- HU-009 (ejercicios deben existir)
- HU-011 (sandbox debe existir para ejecutar)

---

### HU-011 — Sandbox de Ejecución Seguro

**Título**: Ejecución aislada de código Python con límites de recursos

**Como** sistema,
**quiero** ejecutar el código del alumno en un entorno aislado con restricciones estrictas de recursos,
**para que** el código malicioso o con bucles infinitos no afecte al servidor ni a otros usuarios.

#### Criterios de Aceptación

- [ ] La ejecución de código Python tiene un timeout máximo de **10 segundos**. Si se supera, el proceso se termina y el resultado indica `"timeout": true`.
- [ ] La ejecución tiene un límite de memoria de **128 MB**. Si se supera, el proceso se termina con error de memoria.
- [ ] El proceso de sandbox NO tiene acceso a red (sin sockets, sin requests HTTP).
- [ ] El proceso de sandbox solo puede escribir en `/tmp`. No tiene acceso al filesystem del servidor.
- [ ] El sandbox captura `stdout` y `stderr` por separado.
- [ ] El sandbox ejecuta los test cases como assertions después del código del alumno y retorna un array con `{test_id, passed, expected, actual}` por cada caso.
- [ ] En entorno de desarrollo: el sandbox usa `subprocess` de Python con `resource.setrlimit`.
- [ ] En entorno de producción: el sandbox usa un contenedor Docker separado con seccomp profile restrictivo.
- [ ] El resultado de ejecución incluye: `stdout`, `stderr`, `runtime_ms`, `exit_code`, `test_results` (array), `timeout` (bool), `memory_exceeded` (bool).
- [ ] Existe una suite de tests que verifica: código normal funciona, bucle infinito se corta, código con imports maliciosos falla, código que intenta acceder a la red falla.

#### Reglas de Negocio Referenciadas

- RO-3: Sandbox de ejecución — timeout 10s, memory 128MB, sin red, sin filesystem fuera de /tmp.

#### Prioridad

**P1** — Sin esto no hay ejecución de código.

#### Dependencias

- HU-003 (estructura del proyecto)

---

### HU-012 — Code Snapshots Automáticos

**Título**: Guardado automático del código cada 30 segundos y ante eventos relevantes

**Como** sistema,
**quiero** guardar snapshots del código del alumno automáticamente,
**para que** el CTR pueda reconstruir la evolución del código como evidencia del proceso de razonamiento.

#### Criterios de Aceptación

- [ ] `POST /api/v1/submissions/{id}/snapshots` guarda un snapshot del código actual con: `code` (texto), `snapshot_number` (secuencial), `timestamp`, `triggered_by` (enum: `manual_save`, `auto`, `pre_submit`, `pre_execute`).
- [ ] El campo `edit_distance_from_previous` se calcula automáticamente en el backend (distancia de edición Levenshtein entre el snapshot actual y el anterior).
- [ ] El primer snapshot tiene `edit_distance_from_previous = null`.
- [ ] `GET /api/v1/submissions/{id}/snapshots` retorna todos los snapshots ordenados por `snapshot_number`, con el diff entre consecutivos calculado.
- [ ] El frontend envía snapshots automáticamente cada 30 segundos si el código cambió desde el último snapshot.
- [ ] El frontend envía un snapshot con `triggered_by: "pre_execute"` antes de cada ejecución en el sandbox.
- [ ] El frontend envía un snapshot con `triggered_by: "pre_submit"` antes de enviar la submission final.
- [ ] Los snapshots no tienen soft delete — una vez creados, son inmutables.
- [ ] Existe un test que verifica que el `edit_distance_from_previous` se calcula correctamente.

#### Reglas de Negocio Referenciadas

- RO-6: Snapshots automáticos de código — cada 30s y ante cada ejecución.
- RN-3: No hay dato sin contexto — cada snapshot tiene timestamp y contexto.

#### Prioridad

**P2** — Importante para la reconstrucción del CTR, pero el sistema funciona sin esto.

#### Dependencias

- HU-010 (submissions deben existir para crear snapshots asociados)

---

### HU-013 — Test Cases con Reporte Granular

**Título**: Ejecución de test cases individuales con reporte pass/fail por caso

**Como** alumno,
**quiero** saber exactamente qué test cases pasa y cuáles falla mi código,
**para que** pueda diagnosticar qué parte de mi solución está incorrecta.

#### Criterios de Aceptación

- [ ] Los ejercicios tienen `test_cases` almacenados como JSONB con estructura: `[{id, description, input, expected_output, is_visible}]`.
- [ ] Los test cases con `is_visible: true` son visibles para el alumno (descripción + input + expected output).
- [ ] Los test cases con `is_visible: false` son tests privados (el alumno ve si pasa/falla, pero no el input/output esperado).
- [ ] El resultado de ejecución incluye por cada test case: `{test_id, description, passed, actual_output, expected_output (solo si is_visible), runtime_ms}`.
- [ ] Si el código del alumno lanza una excepción no manejada, el test case correspondiente muestra la excepción en `actual_output`.
- [ ] El `score` de la submission se calcula como `(tests_passed / total_tests) * 100` y se almacena como campo en `submissions`.
- [ ] El docente puede ver todos los test cases (incluidos los privados) en el panel de gestión.
- [ ] El frontend muestra los resultados con íconos ✓/✗ por cada test case visible.

#### Reglas de Negocio Referenciadas

- RN-5: No hay evaluación binaria — el score basado en test cases es solo N1 (técnico), no la evaluación final.

#### Prioridad

**P2** — Mejora significativa la experiencia del alumno al depurar.

#### Dependencias

- HU-011 (sandbox ejecuta los test cases)
- HU-010 (submissions almacenan los resultados)

---

### HU-014 — Panel de Gestión de Submissions para Docente

**Título**: Vista del docente de todas las submissions de sus alumnos

**Como** docente,
**quiero** poder ver todas las submissions de mis alumnos para un ejercicio,
**para que** pueda tener una visión global del progreso y detectar alumnos que necesitan ayuda.

#### Criterios de Aceptación

- [ ] `GET /api/v1/courses/{id}/exercises/{ex_id}/submissions` (rol docente) retorna todas las submissions de todos los alumnos inscriptos.
- [ ] Cada submission en el listado muestra: `student_email`, `status`, `score`, `submitted_at`, `test_results` (resumen: `X/Y tests passed`).
- [ ] El endpoint soporta paginación y filtros: `?status=submitted`, `?student_id=uuid`.
- [ ] El docente puede ver el código de cualquier submission de sus alumnos.
- [ ] El endpoint verifica que el docente sea el dueño de la comisión. Un docente no puede ver submissions de comisiones ajenas.
- [ ] Existe un test de integración que verifica el control de acceso (docente no puede ver submissions de otro docente).

#### Reglas de Negocio Referenciadas

- RN-8: Propiedad de datos — el docente solo ve datos de sus comisiones.

#### Prioridad

**P2** — Importante para el flujo del docente.

#### Dependencias

- HU-010 (submissions deben existir)
- HU-009 (enrollments para verificar que el alumno está en la comisión del docente)

---

### HU-015 — Historial de Submissions del Alumno

**Título**: Vista del alumno de su historial de entregas

**Como** alumno,
**quiero** poder ver mi historial de submissions para cada ejercicio, incluyendo los resultados,
**para que** pueda revisar mi progreso y entender mi evolución.

#### Criterios de Aceptación

- [ ] `GET /api/v1/exercises/{id}/submissions/me` retorna todas las submissions del alumno autenticado para ese ejercicio.
- [ ] Cada submission en el historial muestra: `status`, `score`, `submitted_at`, `test_results` (resumen), enlace para ver el código.
- [ ] `GET /api/v1/submissions/{id}` retorna el detalle de una submission específica (código, test results completos, snapshots).
- [ ] Un alumno no puede ver submissions de otros alumnos (retorna 403).
- [ ] Si el alumno intenta acceder a una submission de un ejercicio en el que no está inscripto, retorna 403.

#### Reglas de Negocio Referenciadas

- RN-8: Propiedad de datos — alumno solo ve sus propios datos.

#### Prioridad

**P2**

#### Dependencias

- HU-010 (submissions deben existir)

---

## EPIC 2 — Tutor IA Socrático (Semanas 3-12)

> **Objetivo**: Tutor que guía mediante preguntas, nunca entrega soluciones, todo registrado.
> **Schema owner**: `operational` (tutor_interactions)
> **Dev asignado**: Fase 2

---

### HU-016 — Chat Streaming con Tutor via WebSocket

**Título**: Chat en tiempo real con el tutor IA mediante WebSocket con streaming

**Como** alumno,
**quiero** poder chatear con el tutor IA mientras resuelvo un ejercicio y ver la respuesta aparecer token por token,
**para que** la experiencia sea fluida y pueda leer la guía del tutor mientras la genera.

#### Criterios de Aceptación

- [ ] El endpoint WebSocket `ws://localhost:8000/ws/tutor/chat?token=<jwt>` acepta conexiones autenticadas (producción usa `wss://`).
- [ ] El token JWT se valida al momento de la conexión. Conexiones sin token o con token inválido se rechazan con código de cierre 4001.
- [ ] El alumno envía mensajes en formato JSON: `{type: "message", content: "...", exercise_id: "uuid", session_id: "uuid"}`.
- [ ] El backend responde con chunks de streaming: `{type: "token", payload: {text: "..."}}` mientras el LLM genera.
- [ ] Al finalizar, el backend envía `{type: "complete", payload: {session_id: "uuid"}}`.
- [ ] Si ocurre un error (LLM caído, rate limit), el backend envía `{type: "error", code: "TUTOR_ERROR", message: "..."}`.
- [ ] La conexión WebSocket se mantiene activa con heartbeat: el cliente envía `{type: "ping"}` cada 30s, el servidor responde `{type: "pong"}`.
- [ ] El sistema maneja reconexión automática en el cliente: si se pierde la conexión, reintenta con backoff exponencial (max 5 intentos).
- [ ] El rate limiting de 30 mensajes/hora por alumno por ejercicio se aplica a nivel WebSocket. Al exceder el límite, se envía `{type: "error", code: "TUTOR_RATE_LIMIT_EXCEEDED"}`.
- [ ] Existe un test de integración que verifica la conexión, envío de mensaje y recepción de chunks.

#### Reglas de Negocio Referenciadas

- RO-2: Rate limiting — 30 mensajes/hora por alumno por ejercicio.
- RN-4: No hay IA sin registro — cada interacción debe registrarse.

#### Prioridad

**P1** — Core del EPIC 2.

#### Dependencias

- HU-004 (autenticación JWT)
- HU-017 (system prompt debe existir)

---

### HU-017 — System Prompt Socrático Versionado

**Título**: Gestión versionada del system prompt del tutor con hash SHA-256

**Como** admin,
**quiero** poder gestionar versiones del system prompt del tutor con trazabilidad criptográfica,
**para que** cualquier cambio en el comportamiento del tutor quede auditado y sea reproducible.

#### Criterios de Aceptación

- [ ] `GET /api/v1/admin/tutor/system-prompts` (rol admin) lista todos los prompts con: id, version (semver), is_active, created_at, prompt_hash (SHA-256 del texto).
- [ ] `POST /api/v1/admin/tutor/system-prompts` (rol admin) crea un nuevo prompt con: `version`, `prompt_text`, `notes`. Calcula automáticamente el `prompt_hash = SHA-256(prompt_text)`.
- [ ] Solo puede haber 1 prompt con `is_active = true` a la vez. Al activar uno nuevo, el anterior se desactiva.
- [ ] `PATCH /api/v1/admin/tutor/system-prompts/{id}/activate` activa un prompt y registra un `governance_event` con `event_type: "prompt_update"`.
- [ ] El tutor siempre usa el prompt con `is_active = true`. Si no hay ninguno activo, el sistema retorna error 503.
- [ ] Cada interacción del tutor registra el `prompt_hash` del prompt vigente en `tutor_interactions.prompt_hash`.
- [ ] El system prompt tiene instrucciones explícitas para: no dar soluciones completas, hacer preguntas, mantener tono socrático, adaptar la guía al nivel del alumno.
- [ ] Existe el seed data del prompt inicial con versión `1.0.0` y hash calculado.

#### Reglas de Negocio Referenciadas

- RO-4: Versionado de prompts — cada versión tiene semver, texto completo, hash SHA-256, flag active, notas de cambio.
- RN-4: No hay IA sin registro — el hash del prompt se registra en cada interacción.

#### Prioridad

**P1** — El tutor no puede funcionar sin un system prompt.

#### Dependencias

- HU-007 (seed data crea la versión inicial)
- HU-004 (autenticación para el endpoint de admin)

---

### HU-018 — Constructor de Contexto del Tutor

**Título**: Construcción automática del contexto completo para cada mensaje al tutor

**Como** sistema,
**quiero** construir automáticamente el contexto del tutor (ejercicio + código actual + historial de chat) antes de cada llamada al LLM,
**para que** el tutor tenga toda la información relevante para dar una guía personalizada y pertinente.

#### Criterios de Aceptación

- [ ] Antes de llamar al LLM, el `TutorContextBuilder` arma un objeto de contexto con: system prompt activo, enunciado del ejercicio (description + constraints), starter_code del ejercicio, código actual del alumno (último snapshot), historial de chat (últimos N turnos, con límite de tokens), test results del último run (si existe).
- [ ] El historial de chat se trunca inteligentemente para respetar el límite de tokens del modelo: se priorizan los mensajes más recientes.
- [ ] El contexto incluye el `topic_taxonomy` del ejercicio para que el tutor pueda contextualizar la guía.
- [ ] El objeto de contexto se serializa a un prompt de usuario enriquecido que incluye marcadores claros: `[EJERCICIO]`, `[CÓDIGO ACTUAL]`, `[HISTORIAL]`.
- [ ] Existe un test unitario que verifica que el contexto se construye correctamente con datos mockeados.
- [ ] Existe un test que verifica que el truncado de historial no corta un mensaje a la mitad.

#### Reglas de Negocio Referenciadas

- RN-3: No hay dato sin contexto — el contexto incluye tiempo, contexto del problema, estado del estudiante.

#### Prioridad

**P1** — Sin contexto, el tutor no puede dar guía relevante.

#### Dependencias

- HU-017 (system prompt debe estar disponible)
- HU-012 (snapshots de código para el código actual)

---

### HU-019 — Guardrails Anti-Solver

**Título**: Post-procesador que detecta y reformula respuestas que dan soluciones directas

**Como** sistema pedagógico,
**quiero** inspeccionar cada respuesta del LLM antes de enviarla al alumno y detectar si contiene soluciones directas,
**para que** el tutor nunca viole el principio socrático de no dar respuestas directas.

#### Criterios de Aceptación

- [ ] El `GuardrailsPolicy` analiza la respuesta del LLM antes de transmitirla al frontend.
- [ ] El `AntiSolverGuard` detecta: bloques de código Python mayores a 5 líneas, soluciones completas a la función del ejercicio, frases imperativas tipo "el código correcto es", completar código cuando el alumno inicia un fragmento.
- [ ] Si se detecta una violación, el sistema reformula la respuesta usando el LLM con un prompt específico de reformulación (convierte la solución en una pregunta socrática).
- [ ] Cada respuesta tiene `policy_check_result` en `tutor_interactions`: `"ok"`, `"violation_detected"`, o `"reformulated"`.
- [ ] Si la violación se detecta, se registra un `governance_event` con `event_type: "policy_violation"` con detalle de la respuesta original (encriptada o hasheada).
- [ ] El `ToneGuard` verifica que la respuesta incluye al menos una pregunta (signo `?`). Si no la tiene, agrega una pregunta al final.
- [ ] El `LengthGuard` limita la respuesta a N tokens (configurable por env var). Si excede, trunca antes de una oración completa.
- [ ] Existe una suite de 20+ tests adversariales que verifica que el guardrail funciona (ver `tests/adversarial/`).
- [ ] Los tests adversariales cubren: solicitud directa de código, role-play para eludir restricciones, extracción incremental, urgencia, hipotético, autoridad falsa, jailbreak, completion attack.

#### Reglas de Negocio Referenciadas

- RN-6: El tutor nunca entrega soluciones completas — este componente enforcea esta regla.
- RN-4: No hay IA sin registro — las violaciones se registran.

#### Prioridad

**P1** — Sin guardrails, el sistema no cumple su propósito pedagógico.

#### Dependencias

- HU-016 (chat WebSocket donde se aplican los guardrails)
- HU-017 (system prompt socrático)

---

### HU-020 — Clasificación N4 de Interacciones del Tutor

**Título**: Clasificación automática de cada turno de chat según el modelo N4

**Como** sistema de evaluación cognitiva,
**quiero** clasificar cada interacción del tutor en una de las categorías del modelo N4,
**para que** el CTR tenga evidencia del tipo de interacción cognitiva que el alumno está teniendo con la IA.

#### Criterios de Aceptación

- [ ] Cada entrada en `tutor_interactions` tiene un campo `classification_n4` con valor enum: `exploratory` (alumno explora con preguntas genuinas), `dependent` (alumno pide soluciones directas), `critical` (alumno audita/cuestiona la respuesta del tutor).
- [ ] La clasificación se realiza automáticamente basándose en: el tipo de mensaje del alumno, si el guardrail detectó intento de extracción (→ `dependent`), si el alumno hace preguntas de comprensión (→ `exploratory`), si el alumno refuta o cuestiona al tutor (→ `critical`).
- [ ] La clasificación puede hacerse como post-proceso asíncrono (no bloquea el streaming).
- [ ] El clasificador usa heurísticas basadas en keywords + un llamado adicional al LLM para casos ambiguos.
- [ ] Existe un test unitario con 15+ casos de clasificación con labels esperadas.

#### Reglas de Negocio Referenciadas

- RN-4: No hay IA sin registro — la clasificación N4 es parte del registro obligatorio.
- RN-1: No hay evaluación sin trazabilidad — la clasificación alimenta el CTR.

#### Prioridad

**P2** — Importante para el Motor Cognitivo pero no bloquea el chat.

#### Dependencias

- HU-016 (interacciones deben registrarse)

---

### HU-021 — Reflexión Post-Ejercicio

**Título**: Formulario de reflexión guiada al finalizar un ejercicio

**Como** alumno,
**quiero** completar un formulario de reflexión guiada después de enviar mi submission,
**para que** mi metacognición quede registrada como evidencia en el CTR y el docente pueda ver cómo proceso mi propio aprendizaje.

#### Criterios de Aceptación

- [ ] `POST /api/v1/submissions/{id}/reflection` acepta un JSON con las respuestas al formulario de reflexión.
- [ ] El formulario tiene 4 preguntas fijas: "¿Qué fue lo más difícil de este ejercicio?", "¿Qué estrategia usaste para resolverlo?", "¿Cómo evaluás tu uso del tutor IA?", "¿Qué harías diferente la próxima vez?".
- [ ] Las respuestas se almacenan como parte de `tutor_interactions` con `classification_n4: "metacognition"` o como evento cognitivo de tipo `metacognition` en el CTR.
- [ ] La reflexión puede enviarse una sola vez por submission (retorna 409 si se intenta enviar dos veces).
- [ ] Si el alumno no completa la reflexión, la submission se acepta igual pero `reflection_score` en `cognitive_metrics` queda en 0.
- [ ] El docente puede ver las reflexiones de sus alumnos en el perfil del alumno.
- [ ] Existe un test que verifica que la reflexión se almacena y que el score de reflexión se calcula correctamente.

#### Reglas de Negocio Referenciadas

- RO-5: Reflexión post-ejercicio obligatoria — la UI la muestra automáticamente al hacer submit.

#### Prioridad

**P2** — Importante para la dimensión metacognitiva del CTR.

#### Dependencias

- HU-010 (submission debe existir)

---

### HU-022 — Registro de Governance Events

**Título**: Registro automático de eventos de gobernanza del tutor

**Como** admin,
**quiero** tener un registro auditado de todos los eventos relevantes de gobernanza del sistema del tutor,
**para que** pueda auditar el comportamiento del tutor, detectar violaciones sistémicas y justificar cambios en el sistema.

#### Criterios de Aceptación

- [ ] Se registra un `governance_event` automáticamente en los siguientes casos: violación de policy por el guardrail, cambio de prompt activo, cambio de modelo LLM, errores de conexión repetidos a la API de Anthropic.
- [ ] Cada `governance_event` tiene: `event_type` (enum), `details` (JSONB con contexto), `created_at`, `triggered_by` (user_id o "system").
- [ ] `GET /api/v1/admin/governance/events` (rol admin o docente) lista los eventos con paginación y filtros `?event_type=policy_violation&from=date&to=date`.
- [ ] Los eventos de `policy_violation` incluyen en `details`: el turno de interacción, la categoría de violación detectada (no el texto original de la respuesta del LLM por privacidad).
- [ ] `GET /api/v1/teacher/governance/events` (rol docente) muestra solo los eventos de violación de sus alumnos.
- [ ] Los governance events nunca se borran (no hay soft delete).

#### Reglas de Negocio Referenciadas

- RN-6: Violación detectada genera `governance_event` con `event_type: policy_violation`.
- RO-4: Cambios de prompt generan governance events.
- RG-5: Auditor de coherencia AI-Native — necesita estos eventos para auditar.

#### Prioridad

**P2**

#### Dependencias

- HU-019 (guardrails que generan los eventos)
- HU-017 (cambios de prompt que generan eventos)

---

### HU-023 — Tests Adversariales del Tutor

**Título**: Suite de tests adversariales que verifican que el tutor nunca da soluciones

**Como** equipo de desarrollo,
**quiero** tener una suite de 20+ tests adversariales automatizados,
**para que** podamos garantizar que el tutor socrático mantiene su comportamiento ante intentos de extracción de soluciones.

#### Criterios de Aceptación

- [ ] Existe un archivo `backend/tests/adversarial/prompts.json` con al menos 20 prompts adversariales categorizados.
- [ ] Las categorías cubren: `direct_solution_request`, `role_play_bypass`, `incremental_extraction`, `urgency_bypass`, `hypothetical_bypass`, `authority_bypass`, `jailbreak_attempt`, `completion_attack`.
- [ ] Los tests verifican que en ningún caso el tutor retorna un bloque de código Python de más de 5 líneas que resuelva directamente el ejercicio.
- [ ] Los tests están marcados con `@pytest.mark.adversarial` y se excluyen del CI normal.
- [ ] Existe un job de CI separado (`test-adversarial`) que corre semanalmente y requiere `ANTHROPIC_API_KEY`.
- [ ] Si algún test adversarial falla, se genera una issue automáticamente en GitHub con el prompt y la respuesta del tutor.

#### Reglas de Negocio Referenciadas

- RN-6: El tutor nunca entrega soluciones completas.

#### Prioridad

**P2**

#### Dependencias

- HU-019 (guardrails deben estar implementados)

---

## EPIC 3 — Motor Cognitivo + Evaluación (Semanas 3-12)

> **Objetivo**: Clasificar eventos cognitivos, construir CTR con hash chain, calcular métricas N4.
> **Schema owner**: `cognitive`, `analytics`
> **Dev asignado**: Fase 3

---

### HU-024 — Cognitive Event Classifier

**Título**: Clasificación automática de eventos cognitivos según el modelo N4

**Como** sistema,
**quiero** clasificar cada evento que genera el alumno (ejecución de código, mensaje al tutor, envío de submission) en una categoría del modelo N4,
**para que** el CTR tenga eventos semánticamente etiquetados que sustenten la evaluación multidimensional.

#### Criterios de Aceptación

- [ ] El `CognitiveEventClassifier` recibe eventos del Event Bus (Redis Stream `events:cognitive`) y los clasifica.
- [ ] El mapeo canónico `event_type → N4 level` es: `reads_problem → N1`, `asks_clarification → N1`, `reformulates_problem → N1`, `defines_strategy → N2`, `changes_strategy → N2`, `asks_hint → N2`, `runs_test → N3`, `interprets_error → N3`, `fixes_error → N3`, `asks_explanation → N4`, `audits_ai_suggestion → N4`.
- [ ] Cada `cognitive_event` se persiste con: `session_id`, `event_type`, `n4_level`, `payload` (JSONB con contexto), `sequence_number`, `timestamp`.
- [ ] El `sequence_number` es monotónico por sesión y nunca se reutiliza.
- [ ] El clasificador valida que el `payload` tenga los campos mínimos requeridos por `event_type` (según RN-3).
- [ ] Si el payload es inválido, el evento se persiste con flag `is_valid: false` pero NO se descarta (para auditoría).
- [ ] Existe un test unitario con el mapeo completo de `event_type → N4 level`.

#### Reglas de Negocio Referenciadas

- RN-1: No hay evaluación sin trazabilidad — los eventos son la evidencia.
- RN-2: No hay métrica sin interpretación — cada `event_type` tiene significado pedagógico documentado.
- RN-3: No hay dato sin contexto — el payload incluye contexto completo.

#### Prioridad

**P1** — Sin clasificación, no hay CTR y no hay evaluación.

#### Dependencias

- HU-003 (tabla `cognitive_events` en schema `cognitive`)
- HU-007 (seed data para tener sesiones de prueba)

---

### HU-025 — CTR Builder con Hash Chain

**Título**: Construcción del Cognitive Trace Record con integridad por hash chain SHA-256

**Como** sistema de evaluación,
**quiero** construir el CTR de cada sesión con una cadena de hashes encadenados,
**para que** la integridad del registro cognitivo sea verificable criptográficamente.

#### Criterios de Aceptación

- [ ] `POST /api/v1/cognitive/sessions` (triggered internamente al iniciar un ejercicio) crea una `cognitive_session` con estado `active`.
- [ ] Cada `cognitive_event` registrado en la sesión actualiza el hash chain: `hash(n) = SHA256(hash(n-1) + json(datos(n)))` con keys ordenadas.
- [ ] El primer evento tiene `previous_hash = SHA256("GENESIS:" + session_id + ":" + started_at.isoformat())` (hash inicial derivado de la identidad de la sesión).
- [ ] `POST /api/v1/cognitive/sessions/{id}/close` cierra la sesión, calcula el `ctr_hash_chain` final (hash del último evento), y evalúa `is_valid_ctr`.
- [ ] `is_valid_ctr = true` solo si hay al menos 1 evento clasificado en cada nivel N1, N2, N3, N4 (RO-1).
- [ ] `GET /api/v1/cognitive/sessions/{id}/integrity` permite verificar la integridad de la cadena: recalcula todos los hashes y compara.
- [ ] Una vez cerrada la sesión (`status = "completed"`), no se pueden agregar más eventos (retorna 409).
- [ ] El hash chain es determinístico: el mismo conjunto de eventos con el mismo orden siempre produce el mismo hash final.
- [ ] Existe un test de integración que verifica que: la cadena es válida con eventos normales, la cadena falla si se modifica un evento intermedio.

#### Reglas de Negocio Referenciadas

- RN-7: El CTR es inmutable post-cierre — hash encadenado garantiza esto.
- RO-1: CTR mínimo viable — al menos 1 evento por nivel N1-N4.

#### Prioridad

**P1** — El CTR es el artefacto central del sistema.

#### Dependencias

- HU-024 (eventos deben clasificarse antes de encadenarse)

---

### HU-026 — Validación del CTR Mínimo Viable

**Título**: Validación automática de que el CTR contiene evidencia de todos los niveles N4

**Como** sistema de evaluación,
**quiero** validar automáticamente si un CTR cumple el mínimo viable al momento del cierre de sesión,
**para que** las evaluaciones solo se emitan cuando hay evidencia suficiente de todos los niveles cognitivos.

#### Criterios de Aceptación

- [ ] Al cerrar una sesión (`POST /api/v1/cognitive/sessions/{id}/close`), el sistema verifica si hay al menos 1 evento por cada nivel N1, N2, N3, N4.
- [ ] Si el CTR no es válido, `is_valid_ctr = false` y se incluye en la respuesta: `{is_valid_ctr: false, missing_levels: ["N2", "N4"]}`.
- [ ] Si `is_valid_ctr = false`, el Evaluation Engine puede procesar la sesión pero debe marcar la evaluación como `partial` (no formal).
- [ ] `GET /api/v1/cognitive/sessions/{id}/validation` retorna el estado de validación con detalle por nivel.
- [ ] El sistema notifica al docente si la mayoría de sus alumnos en un ejercicio tienen CTRs no válidos (posible problema con el diseño del ejercicio).

#### Reglas de Negocio Referenciadas

- RO-1: CTR mínimo viable — al menos 1 evento por N1-N4 por episodio.
- RN-1: No hay evaluación sin trazabilidad.

#### Prioridad

**P1**

#### Dependencias

- HU-025 (CTR Builder debe estar implementado)

---

### HU-027 — Cognitive Worker: Métricas N1-N4, Qe y Dependency

**Título**: Cálculo de métricas cognitivas multidimensionales por sesión

**Como** sistema de evaluación,
**quiero** calcular automáticamente las métricas cognitivas (N1-N4 scores, Qe, dependency_score) al cierre de cada sesión,
**para que** el docente tenga datos cuantificados del proceso cognitivo de cada alumno.

#### Criterios de Aceptación

- [ ] Al cerrar una sesión, el `CognitiveWorker` calcula y persiste en `cognitive_metrics`: `n1_score`, `n2_score`, `n3_score`, `n4_score` (0-100 cada uno), `epistemic_quality_score` (Qe, constructo jerárquico sobre N1-N4), `dependency_score` (ratio de interacciones `dependent` vs total), `strategy_shift_count` (cantidad de cambios de estrategia), `reflection_score` (0-100 basado en la calidad de la reflexión post-ejercicio), `success_efficiency` (ratio de intentos exitosos vs total de ejecuciones).
- [ ] El `Qe` (Calidad Epistémica) se calcula como función ponderada de N1-N4 con mayor peso en N3 y N4.
- [ ] El `dependency_score` se normaliza: 0 = totalmente autónomo, 100 = totalmente dependiente.
- [ ] Cada métrica tiene documentación de su significado pedagógico en el código (docstring referenciando el constructo N4).
- [ ] `GET /api/v1/cognitive/sessions/{id}/metrics` retorna las métricas calculadas.
- [ ] El cálculo es asíncrono: se dispara como tarea de background al cerrar la sesión, no bloquea la respuesta HTTP.

#### Reglas de Negocio Referenciadas

- RN-2: No hay métrica sin interpretación — cada métrica tiene significado pedagógico documentado.
- RN-5: No hay evaluación binaria — el sistema produce 4 scores + Qe + dependency.

#### Prioridad

**P1**

#### Dependencias

- HU-025 (CTR Builder que provee los eventos clasificados)
- HU-026 (validación del CTR)

---

### HU-028 — Risk Worker: Detección de Alumnos en Riesgo

**Título**: Detección automática de patrones de riesgo cognitivo en alumnos

**Como** docente,
**quiero** recibir alertas automáticas cuando un alumno muestra patrones de riesgo (dependencia excesiva, desenganche, estancamiento),
**para que** pueda intervenir tempranamente antes de que el alumno quede muy rezagado.

#### Criterios de Aceptación

- [ ] El `RiskWorker` analiza los datos de un alumno a nivel de curso y detecta los patrones: `dependency` (dependency_score > 70% en más de 2 ejercicios consecutivos), `disengagement` (sin actividad en la plataforma por más de 7 días con ejercicios pendientes), `stagnation` (más de 3 intentos en el mismo ejercicio sin mejoría en n3_score).
- [ ] Cada patrón detectado crea o actualiza un `risk_assessment` con: `student_id`, `course_id`, `assessment_type`, `risk_level` (low/medium/high/critical), `details` (JSONB con evidencia).
- [ ] `GET /api/v1/teacher/courses/{id}/risk` (rol docente) retorna todos los alumnos con riesgo ≥ medium, ordenados por `risk_level`.
- [ ] El Risk Worker se ejecuta: al cerrar cada sesión (evaluación individual) y en un job nightly (evaluación de desenganche).
- [ ] El docente puede desestimar una alerta de riesgo con una justificación.
- [ ] Los umbrales son configurables por variable de entorno.

#### Reglas de Negocio Referenciadas

- RN-5: No hay evaluación binaria — el riesgo se evalúa en múltiples dimensiones.

#### Prioridad

**P2** — Importante pero no bloquea el flujo principal.

#### Dependencias

- HU-027 (métricas cognitivas deben estar calculadas)

---

### HU-029 — Evaluation Engine: E = f(N1, N2, N3, N4, Qe)

**Título**: Motor de evaluación multidimensional basado en el modelo N4

**Como** docente,
**quiero** obtener una evaluación formal del alumno que integre las 4 dimensiones del modelo N4 más la calidad epistémica,
**para que** la calificación refleje el proceso cognitivo real y no solo el output del código.

#### Criterios de Aceptación

- [ ] El `EvaluationEngine` calcula: `E = w1*N1 + w2*N2 + w3*N3 + w4*N4 + w5*Qe` con pesos configurables (default: w1=0.15, w2=0.20, w3=0.25, w4=0.25, w5=0.15).
- [ ] La función solo puede ejecutarse si `is_valid_ctr = true`. Si el CTR no es válido, retorna error `CTR_INVALID_FOR_EVALUATION`.
- [ ] `POST /api/v1/teacher/exercises/{id}/evaluate/{student_id}` (rol docente) dispara la evaluación y retorna el resultado con desglose completo.
- [ ] El resultado incluye: score total E, desglose por dimensión (N1-N4 scores, Qe), `evaluation_basis` (resumen en texto del razonamiento), flag `is_formal` (true si CTR válido).
- [ ] El Evaluation Engine NO usa solo `submissions.score` (eso violaría RN-5). El score de test cases es solo el insumo de N1.
- [ ] Los pesos son configurables por docente por ejercicio (permite priorizar distintas dimensiones según el objetivo pedagógico).
- [ ] Existe un test que verifica que el engine rechaza evaluar con CTR no válido.
- [ ] Existe un test que verifica que el engine no produce score basado solo en el output del código.

#### Reglas de Negocio Referenciadas

- RN-1: No hay evaluación sin trazabilidad — el engine valida existencia de CTR primero.
- RN-5: No hay evaluación binaria — siempre produce 4 scores + Qe.
- RG-3: Principio de coherencia evaluativa.

#### Prioridad

**P2**

#### Dependencias

- HU-027 (métricas cognitivas como insumo)
- HU-026 (validación del CTR)

---

### HU-030 — API de Consulta del Perfil Cognitivo del Alumno

**Título**: Endpoints para consultar el perfil cognitivo completo de un alumno

**Como** docente,
**quiero** acceder al perfil cognitivo completo de un alumno (historial de sesiones, métricas por ejercicio, trazas),
**para que** pueda entender el patrón de razonamiento del alumno a lo largo del tiempo.

#### Criterios de Aceptación

- [ ] `GET /api/v1/teacher/students/{id}/profile` retorna: datos del alumno, listado de sesiones con métricas, risk_assessments activos, dependency_score promedio del curso, distribución de N4 levels en interacciones con el tutor.
- [ ] `GET /api/v1/teacher/students/{id}/sessions/{session_id}/trace` retorna la traza cognitiva completa: todos los eventos ordenados por timestamp, snapshots de código, interacciones con el tutor, métricas calculadas.
- [ ] `GET /api/v1/student/me/profile` retorna el perfil cognitivo del alumno autenticado (solo sus propios datos, sin datos de otros alumnos).
- [ ] El docente solo puede acceder a perfiles de alumnos inscriptos en sus comisiones.
- [ ] Los endpoints tienen paginación para sesiones y eventos.

#### Reglas de Negocio Referenciadas

- RN-8: Propiedad de datos — docente ve solo sus alumnos, alumno ve solo sus propios datos.

#### Prioridad

**P2**

#### Dependencias

- HU-027 (métricas calculadas)
- HU-025 (CTR con hash chain)

---

### HU-031 — Verificación de Integridad del Hash Chain

**Título**: Endpoint de auditoría para verificar la integridad del CTR

**Como** auditor o administrador,
**quiero** poder verificar en cualquier momento que el CTR de una sesión no ha sido manipulado,
**para que** la plataforma garantice la autenticidad de las trazas cognitivas usadas en evaluaciones formales.

#### Criterios de Aceptación

- [ ] `GET /api/v1/admin/cognitive/sessions/{id}/integrity` recalcula la cadena de hashes desde el primer evento y compara con los hashes almacenados.
- [ ] Si la cadena es íntegra: `{is_valid: true, events_verified: N, hash_chain_matches: true}`.
- [ ] Si la cadena está rota: `{is_valid: false, broken_at_event: {sequence_number, event_id}, expected_hash, actual_hash}`.
- [ ] La verificación es de solo lectura: no modifica ningún dato.
- [ ] El endpoint está disponible para `admin` y opcionalmente para el docente del curso (para auditar evaluaciones contestadas).

#### Reglas de Negocio Referenciadas

- RN-7: El CTR es inmutable post-cierre — este endpoint verifica que la inmutabilidad se mantiene.

#### Prioridad

**P3** — Deseable para auditoría formal pero no bloquea el flujo principal.

#### Dependencias

- HU-025 (CTR Builder)

---

## EPIC 4 — Frontend Completo (Semanas 3-14)

> **Objetivo**: Todas las pantallas de alumno y docente, integración con APIs reales.
> **Schema owner**: Ninguno (solo consume APIs)
> **Dev asignado**: Fase 4

---

### HU-032 — Dashboard del Alumno

**Título**: Página principal del alumno con cursos y progreso

**Como** alumno,
**quiero** ver al iniciar sesión un dashboard con mis cursos, ejercicios pendientes y mi progreso,
**para que** pueda orientarme rápidamente sobre qué tengo que hacer.

#### Criterios de Aceptación

- [ ] La ruta `/dashboard` (protegida por auth) muestra el dashboard del alumno.
- [ ] Se muestran todos los cursos en los que está inscripto con: nombre del curso, nombre de la comisión, cantidad de ejercicios pendientes/completados.
- [ ] Se muestra una sección "Continuar trabajando" con el último ejercicio en el que el alumno estuvo activo.
- [ ] Se muestra un indicador de progreso general: `X / Y ejercicios completados`.
- [ ] La página usa el MSW mock de `GET /api/v1/courses/me` durante el desarrollo.
- [ ] La página funciona con datos reales post-integración.
- [ ] La vista está diseñada con TailwindCSS 4 y es responsive para tablet (768px+ sin scroll horizontal).
- [ ] Existe un test de componente con Vitest que verifica que se renderiza correctamente con datos mock.

#### Reglas de Negocio Referenciadas

- RN-8: Alumno solo ve sus propios datos.

#### Prioridad

**P1**

#### Dependencias

- HU-005 (tipos TypeScript autogenerados)
- HU-004 (autenticación)

---

### HU-033 — Vista de Ejercicio (Monaco + Chat + Output)

**Título**: Layout de 3 paneles para resolver ejercicios: enunciado, editor, chat+output

**Como** alumno,
**quiero** tener en una sola pantalla el enunciado del ejercicio, un editor de código y el chat con el tutor,
**para que** pueda resolver el ejercicio y pedir ayuda sin cambiar de ventana.

#### Criterios de Aceptación

- [ ] La ruta `/exercises/{id}` muestra el layout de 3 paneles: izquierda (enunciado en markdown renderizado), centro (Monaco Editor configurado para Python), derecha (chat tutor + panel de output).
- [ ] El Monaco Editor tiene: syntax highlighting de Python, autocompletado básico, atajos de teclado estándar, cargado con el `starter_code` del ejercicio.
- [ ] El panel derecho alterna entre "Chat Tutor" y "Output" con tabs.
- [ ] El botón "Ejecutar" envía el código al sandbox (`POST /api/v1/exercises/{id}/run`) y muestra el output en el panel.
- [ ] El output muestra: stdout, stderr (en rojo), resultados de test cases (✓/✗ por caso), runtime en ms.
- [ ] El botón "Enviar" hace submit de la submission y lanza el panel de reflexión.
- [ ] El botón "Guardar" guarda un snapshot manual.
- [ ] Los paneles son redimensionables con un divisor drag-and-drop.
- [ ] El layout se adapta a tablet (paneles apilados verticalmente en pantallas < 900px).
- [ ] El estado del código se persiste en el store de Zustand (no se pierde al navegar).
- [ ] El snapshot automático cada 30s está implementado (timer que compara el código actual con el último snapshot enviado).

#### Reglas de Negocio Referenciadas

- RO-6: Snapshots automáticos — el frontend envía cada 30s.

#### Prioridad

**P1** — Pantalla central del producto.

#### Dependencias

- HU-032 (desde el dashboard se navega a los ejercicios)
- HU-010 (submissions API)
- HU-011 (sandbox API)

---

### HU-034 — Panel de Chat con el Tutor

**Título**: Componente de chat streaming con el tutor socrático integrado en la vista de ejercicio

**Como** alumno,
**quiero** poder chatear con el tutor IA y ver las respuestas aparecer en tiempo real con streaming,
**para que** la experiencia de consulta sea fluida y natural.

#### Criterios de Aceptación

- [ ] El componente `TutorChat` gestiona la conexión WebSocket con reconexión automática.
- [ ] Los mensajes del tutor aparecen token por token (streaming) en la interfaz.
- [ ] Durante el streaming, se muestra un indicador de "el tutor está pensando..." con animación.
- [ ] El historial de chat persiste en el store de Zustand para la sesión actual.
- [ ] Si el rate limit (30 msg/hora) se alcanza, se muestra un aviso con el tiempo de espera.
- [ ] Si la conexión WebSocket se pierde, se muestra un banner "Reconectando..." y se reintenta automáticamente.
- [ ] Cada mensaje del alumno muestra: avatar, texto, timestamp.
- [ ] Cada mensaje del tutor muestra: avatar diferenciado, texto (markdown renderizado), timestamp.
- [ ] El campo de texto tiene: botón de envío, atajo Ctrl+Enter para enviar, límite de caracteres visible.

#### Reglas de Negocio Referenciadas

- RO-2: Rate limiting — la UI lo muestra amigablemente.
- RN-4: No hay IA sin registro — cada mensaje enviado se registra en el backend.

#### Prioridad

**P1**

#### Dependencias

- HU-016 (backend WebSocket)
- HU-033 (vista de ejercicio donde vive el chat)

---

### HU-035 — Panel de Reflexión Post-Ejercicio

**Título**: Formulario de reflexión guiada que aparece automáticamente al enviar una submission

**Como** alumno,
**quiero** que al enviar mi ejercicio aparezca automáticamente el formulario de reflexión,
**para que** no me olvide de completarlo y mi metacognición quede registrada en el CTR.

#### Criterios de Aceptación

- [ ] Al hacer click en "Enviar" y confirmar, aparece un modal o pantalla completa con el formulario de reflexión.
- [ ] El formulario tiene las 4 preguntas con áreas de texto libres (min 50 caracteres por respuesta).
- [ ] Hay un botón "Saltar reflexión" visible pero con texto disuasivo ("Esta información ayuda a mejorar tu evaluación").
- [ ] Al completar y enviar, se llama a `POST /api/v1/submissions/{id}/reflection`.
- [ ] Al completar exitosamente, el alumno ve una confirmación y es redirigido al dashboard.
- [ ] Si el alumno salta la reflexión, también es redirigido pero se muestra un aviso de que el reflection_score será 0.
- [ ] El formulario no permite enviar si alguna respuesta tiene menos de 50 caracteres (validación frontend).
- [ ] Existe un test E2E con Playwright que verifica el flujo completo: submit → reflexión → confirmación.

#### Reglas de Negocio Referenciadas

- RO-5: Reflexión post-ejercicio obligatoria (se muestra automáticamente, aunque puede saltarse).

#### Prioridad

**P2**

#### Dependencias

- HU-033 (vista de ejercicio)
- HU-021 (endpoint de reflexión)

---

### HU-036 — Dashboard del Docente

**Título**: Dashboard del docente con indicadores agregados de la comisión

**Como** docente,
**quiero** ver en mi dashboard los indicadores cognitivos agregados de mi comisión con alertas de riesgo,
**para que** pueda tener una visión rápida del estado de mis alumnos sin revisar uno por uno.

#### Criterios de Aceptación

- [ ] La ruta `/teacher/dashboard` muestra los datos de las comisiones del docente.
- [ ] Por cada comisión, se muestran: número de alumnos activos, distribución de N4 levels (gráfico de barras), promedio de Qe, lista de alumnos en riesgo color-coded (low=verde, medium=amarillo, high=naranja, critical=rojo).
- [ ] La lista de alumnos en riesgo muestra: nombre, tipo de riesgo, nivel de riesgo, último acceso.
- [ ] Al hacer click en un alumno en riesgo, navega al perfil cognitivo del alumno.
- [ ] Hay un filtro por ejercicio para ver los indicadores solo de un ejercicio específico.
- [ ] El radar chart N1-N4 muestra el promedio de la comisión (ver HU-037).
- [ ] La página usa datos del MSW mock durante el desarrollo y funciona con datos reales post-integración.

#### Reglas de Negocio Referenciadas

- RN-8: Docente solo ve sus propios alumnos.
- RN-5: La UI refleja evaluación multidimensional (no un solo número).

#### Prioridad

**P1**

#### Dependencias

- HU-032 (login y routing de roles)
- HU-028 (Risk Worker)
- HU-027 (métricas cognitivas)

---

### HU-037 — Radar Chart N1-N4

**Título**: Visualización del perfil cognitivo N4 en formato radar chart

**Como** docente,
**quiero** ver el perfil cognitivo de un alumno o de la comisión en un radar chart de 4 ejes (N1, N2, N3, N4),
**para que** pueda identificar visualmente en qué dimensiones el alumno es fuerte o necesita refuerzo.

#### Criterios de Aceptación

- [ ] El componente `N4RadarChart` recibe `{n1_score, n2_score, n3_score, n4_score}` y renderiza un radar chart.
- [ ] Los 4 ejes están etiquetados: N1 (Comprensión del problema), N2 (Estrategia y planificación), N3 (Validación técnica), N4 (Interacción con IA).
- [ ] El chart muestra el score del alumno individual vs el promedio de la comisión (dos polígonos superpuestos).
- [ ] Los scores se muestran en una escala 0-100.
- [ ] El chart es interactivo: al hover muestra el valor exacto.
- [ ] La librería usada es Recharts o Chart.js (no inventar un chart desde cero).
- [ ] El componente es responsive y no pierde legibilidad en tablet.
- [ ] Existe un test de componente que verifica que el chart renderiza con datos válidos.

#### Prioridad

**P2**

#### Dependencias

- HU-036 (dashboard docente donde vive el chart)

---

### HU-038 — Traza Cognitiva Visual

**Título**: Timeline visual de la traza cognitiva de un alumno en un ejercicio

**Como** docente,
**quiero** ver la traza cognitiva completa de un alumno para un ejercicio como un timeline visual con eventos color-coded,
**para que** pueda entender el proceso de razonamiento del alumno y proveer feedback personalizado.

#### Criterios de Aceptación

- [ ] La ruta `/teacher/students/{id}/exercises/{ex_id}/trace` muestra la traza cognitiva completa.
- [ ] El timeline muestra cada evento cognitivo con: icono por nivel N4 (N1=azul, N2=verde, N3=naranja, N4=violeta), descripción del evento, timestamp, duración desde el evento anterior.
- [ ] Al hacer click en un evento de tipo "snapshot", se muestra el código en ese momento con diff respecto al snapshot anterior (usando Monaco Editor en modo diff).
- [ ] Al hacer click en un evento de tipo "tutor_interaction", se muestra el turno del chat completo.
- [ ] El timeline tiene filtros: mostrar solo N1/N2/N3/N4, mostrar solo snapshots, mostrar solo interacciones con el tutor.
- [ ] La página muestra en el header: `is_valid_ctr`, métricas calculadas (N1-N4 scores, Qe, dependency_score).
- [ ] La traza se carga con paginación: primeros 50 eventos, botón "Cargar más".

#### Prioridad

**P2**

#### Dependencias

- HU-030 (API de traza cognitiva)
- HU-037 (radar chart del perfil)

---

### HU-039 — Vista de Patrones de Ejercicio

**Título**: Vista agregada de cómo la comisión resolvió un ejercicio

**Como** docente,
**quiero** ver una vista agregada de las estrategias usadas por toda la comisión para resolver un ejercicio específico,
**para que** pueda detectar si el ejercicio tiene un diseño problemático o si hay estrategias comunes que debería abordar en clase.

#### Criterios de Aceptación

- [ ] La ruta `/teacher/exercises/{id}/patterns` muestra la vista de patrones.
- [ ] Se muestra: distribución de `strategy_shift_count` (histograma), distribution de `dependency_score` (histograma), porcentaje de alumnos que completaron el CTR mínimo válido, top 3 preguntas más frecuentes al tutor (clustering por similitud), distribución de N4 levels en interacciones con el tutor.
- [ ] El docente puede ver quién está en cada percentil del histograma y navegar a su traza.
- [ ] La vista tiene un botón "Exportar CSV" con los datos agregados (sin PII).

#### Prioridad

**P3** — Deseable pero no urgente.

#### Dependencias

- HU-038 (datos de trazas)

---

### HU-040 — Reportes de Gobernanza

**Título**: Vista de reportes de gobernanza para docentes y admins

**Como** docente o admin,
**quiero** ver los reportes de gobernanza del tutor (violaciones de política, cambios de prompt, alertas),
**para que** pueda auditar el comportamiento del sistema y detectar problemas pedagógicos.

#### Criterios de Aceptación

- [ ] La ruta `/teacher/governance` muestra la lista de governance events de las comisiones del docente.
- [ ] La ruta `/admin/governance` muestra todos los governance events del sistema.
- [ ] Los eventos se muestran con: tipo (icono diferenciado), fecha, descripción, severidad.
- [ ] Los eventos de `policy_violation` muestran el contexto del ejercicio y el alumno (sin mostrar el texto de la respuesta del LLM).
- [ ] Los eventos de `prompt_update` muestran qué versión se activó, quién lo hizo, y las notas del cambio.
- [ ] Hay filtros por tipo de evento y por rango de fechas.
- [ ] Los eventos están paginados (20 por página).

#### Prioridad

**P3**

#### Dependencias

- HU-022 (governance events en el backend)

---

### HU-041 — MSW Mocks para Desarrollo Paralelo

**Título**: Mock Service Worker configurado para que el frontend funcione sin el backend real

**Como** desarrollador de frontend,
**quiero** tener todos los endpoints de la API mockeados con MSW durante el desarrollo,
**para que** pueda trabajar en el frontend en paralelo con el backend sin necesitar los endpoints reales.

#### Criterios de Aceptación

- [ ] MSW está configurado en `frontend/src/mocks/` con handlers para todos los endpoints documentados en la OpenAPI spec.
- [ ] Los handlers devuelven datos que respetan los mismos schemas Pydantic (usando los tipos TypeScript autogenerados).
- [ ] El MSW se activa solo en modo desarrollo (`import.meta.env.DEV`). En producción no se incluye.
- [ ] Existe un switch en `.env.local`: `VITE_MSW_ENABLED=true/false` para activar/desactivar fácilmente.
- [ ] Los mocks incluyen delays simulados (200-800ms) para que el desarrollo refleje la latencia real.
- [ ] Los mocks incluyen casos de error simulados para testear los estados de error del UI.
- [ ] Al remover MSW (cuando los endpoints reales estén listos), no requiere ningún cambio de código en los componentes.
- [ ] El MSW WebSocket mock simula el streaming del tutor token por token con un delay de 50ms entre tokens.

#### Prioridad

**P1** — Crítico para que el frontend avance en paralelo.

#### Dependencias

- HU-005 (tipos TypeScript autogenerados que los mocks deben respetar)

---

### HU-042 — Diseño Responsive para Tablet

**Título**: Adaptación de las vistas principales para uso en tablet en el aula

**Como** alumno usando una tablet en clase,
**quiero** que las vistas principales funcionen sin scroll horizontal y sean fáciles de usar,
**para que** pueda trabajar cómodamente en el aula sin necesitar una laptop.

#### Criterios de Aceptación

- [ ] Las vistas están diseñadas mobile-first con breakpoints: sm (640px), md (768px), lg (1024px), xl (1280px).
- [ ] En tablet (768-1024px), la vista de ejercicio colapsa los 3 paneles a 2 tabs: "Editor" y "Tutor/Output".
- [ ] En tablet, el Monaco Editor usa font-size 14px y el teclado virtual no cubre el editor.
- [ ] En tablet, el dashboard del alumno muestra las tarjetas de cursos apiladas (1 columna, no 3).
- [ ] En tablet, el dashboard del docente muestra el radar chart redimensionado pero legible.
- [ ] No hay scroll horizontal en ninguna de las vistas principales en pantallas de 768px+.
- [ ] Se realizan pruebas manuales en: iPad Mini (768px), iPad (820px), Android tablet típica (800px).

#### Prioridad

**P2**

#### Dependencias

- HU-033 (vista de ejercicio)
- HU-036 (dashboard docente)

---

*Total de Historias: 42 | EPIC 0: 7 | EPIC 1: 8 | EPIC 2: 8 | EPIC 3: 8 | EPIC 4: 11*

---

## Resumen de Prioridades

| Prioridad | Cantidad | EPICs |
|-----------|----------|-------|
| P0 (Bloqueante) | 2 | HU-001, HU-002 |
| P1 (Crítico) | 20 | Distribuido en todos los EPICs |
| P2 (Importante) | 17 | Distribuido en todos los EPICs |
| P3 (Deseable) | 3 | HU-031, HU-039, HU-040 |

---

*Documento generado: 2026-04-10 | Plataforma AI-Native v1.0 | UTN FRM*
