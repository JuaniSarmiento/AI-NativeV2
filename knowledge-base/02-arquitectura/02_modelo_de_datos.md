# Modelo de Datos — Plataforma AI-Native

**Versión**: 1.0  
**Fecha**: 2026-04-10  
**Motor**: PostgreSQL 16  
**ORM**: SQLAlchemy 2.0 async  

---

## Tabla de Contenidos

1. [Principios del Modelo de Datos](#1-principios-del-modelo-de-datos)
2. [Schema: operational](#2-schema-operational)
3. [Schema: cognitive](#3-schema-cognitive)
4. [Schema: governance](#4-schema-governance)
5. [Schema: analytics](#5-schema-analytics)
6. [Estrategia de Índices](#6-estrategia-de-índices)
7. [Estrategia de Soft Delete](#7-estrategia-de-soft-delete)
8. [Estructuras JSONB](#8-estructuras-jsonb)
9. [Mecanismo de Hash Chain (CTR)](#9-mecanismo-de-hash-chain-ctr)

---

## 1. Principios del Modelo de Datos

### Inmutabilidad del CTR

Los eventos del Registro de Traza Cognitiva (CTR) son **inmutables por diseño**. Una vez registrado un `cognitive_event` o `reasoning_record`, **nunca se modifica ni se elimina**. La integridad se garantiza mediante:
- Sin columna `deleted_at` ni `is_active` en tablas CTR
- Permisos PostgreSQL: solo `INSERT`, nunca `UPDATE/DELETE` en esas tablas
- Hash chain SHA-256: cualquier alteración rompe la cadena

### UUID v4 como Primary Keys

Todas las tablas usan `UUID` como PK. Razones:
- Generación en cliente sin round-trip a DB
- Sin exposición de auto-increment secuencial (seguridad)
- Facilita la eventual distribución

### Timestamps en UTC

Todos los timestamps son `TIMESTAMP WITH TIME ZONE` almacenados en UTC. El frontend convierte a timezone del usuario.

### Convención de Naming en DB

- Tablas: `snake_case` plural → `cognitive_events`
- Columnas: `snake_case` → `created_at`, `student_id`
- PKs: `id` (UUID)
- FKs: `{tabla_referenciada_singular}_id` → `student_id`, `exercise_id`
- Índices: `ix_{tabla}_{columna}` → `ix_submissions_student_id`
- Constraints: `uq_{tabla}_{columnas}` → `uq_enrollments_student_commission`

---

## 2. Schema: operational

Este schema almacena toda la lógica operacional de la plataforma: usuarios, cursos, comisiones, ejercicios, entregas y la tabla pivot de interacciones con el tutor.

### Diagrama ER — Schema Operational

```
┌──────────────┐       ┌──────────────────┐       ┌─────────────────┐
│    users     │       │     courses       │       │  commissions    │
├──────────────┤       ├──────────────────┤       ├─────────────────┤
│ id (PK)      │       │ id (PK)          │       │ id (PK)         │
│ email        │       │ name             │       │ course_id (FK)  │─┐
│ password_hash│       │ description      │       │ name            │ │
│ full_name    │       │ topic_taxonomy   │       │ year            │ │
│ role         │       │ is_active        │       │ semester        │ │
│ is_active    │       │ created_at       │       │ teacher_id (FK) │─┼──┐
│ created_at   │       │ updated_at       │       │ is_active       │ │  │
│ updated_at   │       └──────────────────┘       │ created_at      │ │  │
└──────┬───────┘               │ 1                └────────┬────────┘ │  │
       │                       │                           │ 1        │  │
       │ 1                     │ N                         │ N        │  │
       │                 ┌─────▼────────┐           ┌──────▼─────┐   │  │
       │                 │  exercises   │           │enrollments │   │  │
       │                 ├─────────────┤           ├────────────┤   │  │
       │                 │ id (PK)     │           │id (PK)     │   │  │
       │                 │commission_id│(FK)────┐  │student_id  │(FK)┘  │
       │                 │title        │        │  │commission_id│(FK)   │
       │                 │description  │        │  │enrolled_at │       │
       │                 │test_cases   │        │  │is_active   │       │
       │                 │difficulty   │        │  └────────────┘       │
       │                 │topic_tags   │        │                       │
       │                 │order_index  │        │ (FK a commissions)    │
       │                 │is_active    │        └───────────────────────┘
       │                 │created_at   │
       │                 └──────┬──────┘
       │                        │ 1
       │                        │ N
       │                 ┌──────▼──────────┐
       │                 │   submissions   │
       │                 ├─────────────────┤
       └────────────────>│ student_id (FK) │
         1               │ exercise_id(FK) │
                         │ code            │
                         │ status          │
                         │ score           │
                         │ feedback        │
                         │ submitted_at    │
                         └──────┬──────────┘
                                │ 1
                                │ N
                         ┌──────▼──────────────┐
                         │   code_snapshots    │
                         ├─────────────────────┤
                         │ id (PK)             │
                         │ submission_id (FK)  │
                         │ code                │
                         │ snapshot_at         │
                         └─────────────────────┘

┌──────────────┐         ┌───────────────────────┐
│    users     │         │   tutor_interactions  │
│ (student)    │─────────├───────────────────────┤
└──────────────┘  1   N  │ id (PK)               │
                         │ student_id (FK)        │
┌──────────────┐         │ exercise_id (FK)       │
│  exercises   │─────────│ role (user/assistant)  │
└──────────────┘  1   N  │ content                │
                         │ n4_level               │
                         │ tokens_used            │
                         │ created_at             │
                         └───────────────────────┘
```

### Tabla: users

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | Identificador único |
| `email` | `VARCHAR(255)` | UNIQUE, NOT NULL | Email del usuario, usado para login |
| `password_hash` | `VARCHAR(255)` | NOT NULL | bcrypt hash, factor 12 |
| `full_name` | `VARCHAR(255)` | NOT NULL | Nombre completo para display |
| `role` | `ENUM('student','teacher','admin')` | NOT NULL, DEFAULT 'student' | Rol que determina permisos |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT TRUE | Soft delete: FALSE deshabilita el acceso |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | Timestamp de creación |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | Timestamp de última modificación |

**Índices**: `ix_users_email` (UNIQUE, para login rápido), `ix_users_role` (para listar por rol).

**Relaciones**:
- 1:N con `enrollments` (un usuario puede inscribirse en muchas comisiones)
- 1:N con `submissions` (un usuario puede hacer muchas entregas)
- 1:N con `tutor_interactions` (un usuario puede tener muchas interacciones)
- 1:N con `commissions` (un teacher puede dictar muchas comisiones)

---

### Tabla: courses

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| `id` | `UUID` | PK | Identificador único |
| `name` | `VARCHAR(255)` | NOT NULL | Nombre del curso (ej: "Algoritmos y Estructuras de Datos") |
| `description` | `TEXT` | NULLABLE | Descripción larga del contenido del curso |
| `topic_taxonomy` | `JSONB` | NULLABLE | Árbol de temas del curso (ver sección JSONB) |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT TRUE | Soft delete |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | Timestamp de creación |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | Timestamp de modificación |

**Índices**: `ix_courses_name` (para búsqueda por nombre).

---

### Tabla: commissions

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| `id` | `UUID` | PK | Identificador único |
| `course_id` | `UUID` | FK → courses.id, NOT NULL | Curso al que pertenece |
| `teacher_id` | `UUID` | FK → users.id, NOT NULL | Docente que dicta la comisión |
| `name` | `VARCHAR(100)` | NOT NULL | Nombre (ej: "Comisión A - 2025") |
| `year` | `SMALLINT` | NOT NULL | Año lectivo |
| `semester` | `SMALLINT` | NOT NULL, CHECK (1 or 2) | Semestre (1 o 2) |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT TRUE | Soft delete |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | Timestamp de creación |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | Timestamp de modificación |

**Índices**: `ix_commissions_course_id`, `ix_commissions_teacher_id`, `ix_commissions_year_semester` (compuesto, para filtrar por ciclo lectivo).

---

### Tabla: enrollments

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| `id` | `UUID` | PK | Identificador único |
| `student_id` | `UUID` | FK → users.id, NOT NULL | Estudiante inscripto |
| `commission_id` | `UUID` | FK → commissions.id, NOT NULL | Comisión en la que se inscribe |
| `enrolled_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | Fecha de inscripción |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT TRUE | FALSE si se da de baja |

**Constraints**: `uq_enrollments_student_commission` UNIQUE (student_id, commission_id).  
**Índices**: `ix_enrollments_student_id`, `ix_enrollments_commission_id`.

---

### Tabla: exercises

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| `id` | `UUID` | PK | Identificador único |
| `commission_id` | `UUID` | FK → commissions.id, NOT NULL | Comisión a la que pertenece |
| `title` | `VARCHAR(255)` | NOT NULL | Título del ejercicio |
| `description` | `TEXT` | NOT NULL | Enunciado completo del ejercicio |
| `test_cases` | `JSONB` | NOT NULL | Casos de prueba para auto-corrección |
| `difficulty` | `ENUM('easy','medium','hard')` | NOT NULL | Nivel de dificultad |
| `topic_tags` | `TEXT[]` | NOT NULL, DEFAULT '{}' | Tags de temas (ej: ['recursion', 'graphs']) |
| `order_index` | `SMALLINT` | NOT NULL, DEFAULT 0 | Orden dentro de la comisión |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT TRUE | Soft delete |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | Timestamp de creación |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | Timestamp de modificación |

**Índices**: `ix_exercises_commission_id` (para listar ejercicios de una comisión), `ix_exercises_topic_tags` (GIN index, para búsqueda por tags).

---

### Tabla: submissions

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| `id` | `UUID` | PK | Identificador único |
| `student_id` | `UUID` | FK → users.id, NOT NULL | Estudiante que envía |
| `exercise_id` | `UUID` | FK → exercises.id, NOT NULL | Ejercicio enviado |
| `code` | `TEXT` | NOT NULL | Código fuente final enviado |
| `status` | `ENUM('pending','running','passed','failed','error')` | NOT NULL, DEFAULT 'pending' | Estado del procesamiento |
| `score` | `NUMERIC(5,2)` | NULLABLE | Puntuación 0.00 a 100.00 |
| `feedback` | `TEXT` | NULLABLE | Feedback generado (puede ser por IA o manual) |
| `test_results` | `JSONB` | NULLABLE | Resultados caso a caso de los tests |
| `submitted_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | Timestamp de envío |
| `evaluated_at` | `TIMESTAMPTZ` | NULLABLE | Timestamp de evaluación completada |

**Índices**: `ix_submissions_student_id`, `ix_submissions_exercise_id`, `ix_submissions_student_exercise` (compuesto, para query "última entrega de X en Y").

---

### Tabla: code_snapshots

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| `id` | `UUID` | PK | Identificador único |
| `submission_id` | `UUID` | FK → submissions.id, NOT NULL | Entrega a la que pertenece este snapshot |
| `code` | `TEXT` | NOT NULL | Código en ese momento |
| `snapshot_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | Timestamp exacto del snapshot |

**Nota**: Los snapshots son inmutables por naturaleza (registran el histórico de edición). No tienen soft delete. Solo se insertan.

**Índices**: `ix_code_snapshots_submission_id` (para recuperar el historial de una entrega).

---

### Tabla: tutor_interactions

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| `id` | `UUID` | PK | Identificador único |
| `student_id` | `UUID` | FK → users.id, NOT NULL | Estudiante que interactuó |
| `exercise_id` | `UUID` | FK → exercises.id, NOT NULL | Ejercicio en contexto |
| `role` | `ENUM('user','assistant')` | NOT NULL | Quién envió el mensaje |
| `content` | `TEXT` | NOT NULL | Contenido del mensaje |
| `n4_level` | `SMALLINT` | NULLABLE, CHECK (1 to 4) | Nivel N1-N4 detectado para esta interacción |
| `tokens_used` | `INTEGER` | NULLABLE | Tokens consumidos en la llamada a la API LLM |
| `model_version` | `VARCHAR(100)` | NULLABLE | Versión del modelo LLM usado |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | Timestamp de la interacción |

**Índices**: `ix_tutor_interactions_student_id`, `ix_tutor_interactions_exercise_id`, `ix_tutor_interactions_student_exercise_created` (compuesto, para recuperar historial ordenado).

**Nota**: Esta tabla es append-only en la práctica. No se editan mensajes pasados.

---

## 3. Schema: cognitive

Este schema almacena toda la traza cognitiva del estudiante. Es el núcleo del sistema CTR. **Las tablas de eventos son estrictamente inmutables.**

### Diagrama ER — Schema Cognitive

```
┌─────────────────────────┐
│   cognitive_sessions    │
├─────────────────────────┤
│ id (PK)                 │─────────────────────────────────┐
│ student_id              │                                  │
│ exercise_id             │                                  │
│ started_at              │                                  │
│ closed_at               │                                  │
│ session_hash            │ (hash de toda la sesión)        │
│ n4_final_score          │                                  │
│ status                  │                                  │
└─────────┬───────────────┘                                  │
          │ 1                                                 │
          │ N                                                 │
┌─────────▼───────────────┐       ┌──────────────────────────▼──┐
│   cognitive_events      │       │    cognitive_metrics        │
├─────────────────────────┤       ├─────────────────────────────┤
│ id (PK)                 │       │ id (PK)                     │
│ session_id (FK)         │       │ session_id (FK, UNIQUE)     │
│ event_type              │       │ n1_comprehension_score      │
│ sequence_number         │       │ n2_strategy_score           │
│ payload                 │       │ n3_validation_score         │
│ previous_hash           │       │ n4_ai_interaction_score     │
│ current_hash            │       │ total_interactions          │
│ created_at              │       │ help_seeking_ratio          │
└─────────────────────────┘       │ autonomy_index              │
                                  │ risk_level                  │
┌─────────────────────────┐       │ computed_at                 │
│  reasoning_records      │       └─────────────────────────────┘
├─────────────────────────┤
│ id (PK)                 │
│ session_id (FK)         │
│ record_type             │
│ details                 │
│ previous_hash           │
│ current_hash            │
│ created_at              │
└─────────────────────────┘
```

### Tabla: cognitive_sessions

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| `id` | `UUID` | PK | Identificador único de sesión |
| `student_id` | `UUID` | NOT NULL | Referencia al user (sin FK cross-schema — se valida en service) |
| `exercise_id` | `UUID` | NOT NULL | Referencia al ejercicio |
| `started_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | Inicio de la sesión cognitiva |
| `closed_at` | `TIMESTAMPTZ` | NULLABLE | Fin de la sesión. NULL = sesión abierta |
| `session_hash` | `VARCHAR(64)` | NULLABLE | SHA-256 hash final de toda la sesión al cierre |
| `n4_final_score` | `JSONB` | NULLABLE | Puntuaciones N1-N4 al cierre (ver sección JSONB) |
| `status` | `ENUM('open','closed','invalidated')` | NOT NULL, DEFAULT 'open' | Estado |

**Índices**: `ix_cognitive_sessions_student_id`, `ix_cognitive_sessions_exercise_id`, `ix_cognitive_sessions_student_exercise_status` (compuesto).

**Nota sobre FKs**: Deliberadamente no hay FK cross-schema hacia `operational.users`. La integridad referencial se garantiza en la capa de servicio. Esto permite que cognitive sea independiente de operational.

---

### Tabla: cognitive_events

**TABLA INMUTABLE — Solo INSERT, nunca UPDATE ni DELETE.**

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| `id` | `UUID` | PK | Identificador único del evento |
| `session_id` | `UUID` | FK → cognitive_sessions.id, NOT NULL | Sesión a la que pertenece |
| `event_type` | `VARCHAR(100)` | NOT NULL | Tipo de evento (ver catálogo abajo) |
| `sequence_number` | `INTEGER` | NOT NULL | Número de secuencia dentro de la sesión (1, 2, 3...) |
| `payload` | `JSONB` | NOT NULL | Datos del evento, variado por tipo |
| `previous_hash` | `VARCHAR(64)` | NOT NULL | Hash del evento anterior (o hash inicial de sesión) |
| `current_hash` | `VARCHAR(64)` | NOT NULL | SHA-256(previous_hash + event_type + payload + timestamp) |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | Timestamp inmutable |

**Constraints**: `uq_cognitive_events_session_sequence` UNIQUE (session_id, sequence_number).

**Catálogo de event_type**:

| event_type | Descripción | Nivel N4 |
|------------|-------------|---------|
| `session.started` | Inicio de sesión con ejercicio | — |
| `code.snapshot` | El estudiante guardó un snapshot del código | N1 |
| `tutor.question_asked` | El estudiante preguntó al tutor | N4 |
| `tutor.response_received` | El tutor respondió | N4 |
| `code.run` | El estudiante ejecutó el código (sandbox) | N3 |
| `submission.created` | El estudiante envió el ejercicio | N2/N3 |
| `reflection.submitted` | El estudiante completó una reflexión guiada | N1/N2 |
| `session.closed` | Sesión cerrada (manual o timeout) | — |

**Índices**: `ix_cognitive_events_session_id`, `ix_cognitive_events_session_sequence` (compuesto, para leer la cadena en orden).

---

### Tabla: reasoning_records

**TABLA INMUTABLE — Solo INSERT.**

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| `id` | `UUID` | PK | Identificador único |
| `session_id` | `UUID` | FK → cognitive_sessions.id, NOT NULL | Sesión |
| `record_type` | `ENUM('hypothesis','strategy','validation','reflection')` | NOT NULL | Tipo de registro de razonamiento |
| `details` | `JSONB` | NOT NULL | Detalle del razonamiento (ver sección JSONB) |
| `previous_hash` | `VARCHAR(64)` | NOT NULL | Hash del registro anterior |
| `current_hash` | `VARCHAR(64)` | NOT NULL | SHA-256 de este registro |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | Timestamp |

**Índices**: `ix_reasoning_records_session_id`.

---

### Tabla: cognitive_metrics

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| `id` | `UUID` | PK | Identificador único |
| `session_id` | `UUID` | FK → cognitive_sessions.id, UNIQUE | Una métrica por sesión |
| `n1_comprehension_score` | `NUMERIC(5,2)` | NULLABLE | Score N1: comprensión del problema (0-100) |
| `n2_strategy_score` | `NUMERIC(5,2)` | NULLABLE | Score N2: calidad de la estrategia (0-100) |
| `n3_validation_score` | `NUMERIC(5,2)` | NULLABLE | Score N3: validación propia del trabajo (0-100) |
| `n4_ai_interaction_score` | `NUMERIC(5,2)` | NULLABLE | Score N4: calidad de interacción con IA (0-100) |
| `total_interactions` | `INTEGER` | NOT NULL, DEFAULT 0 | Total de interacciones con el tutor |
| `help_seeking_ratio` | `NUMERIC(4,3)` | NULLABLE | Ratio preguntas/acciones (0.0 a 1.0) |
| `autonomy_index` | `NUMERIC(4,3)` | NULLABLE | Índice de autonomía calculado (0.0 a 1.0) |
| `risk_level` | `ENUM('low','medium','high','critical')` | NULLABLE | Nivel de riesgo de dependencia en IA |
| `computed_at` | `TIMESTAMPTZ` | NULLABLE | Cuando se computaron las métricas |

**Índices**: `ix_cognitive_metrics_session_id` (UNIQUE), `ix_cognitive_metrics_risk_level` (para alertas).

---

## 4. Schema: governance

### Diagrama ER — Schema Governance

```
┌──────────────────────────┐       ┌───────────────────────────┐
│   tutor_system_prompts   │       │    governance_events      │
├──────────────────────────┤       ├───────────────────────────┤
│ id (PK)                  │       │ id (PK)                   │
│ name                     │       │ event_type                │
│ content                  │       │ actor_id                  │
│ version                  │       │ target_type               │
│ is_active                │       │ target_id                 │
│ guardrails_config        │       │ details                   │
│ created_by               │       │ created_at                │
│ created_at               │       └───────────────────────────┘
│ updated_at               │
└──────────────────────────┘
```

### Tabla: tutor_system_prompts

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| `id` | `UUID` | PK | Identificador único |
| `name` | `VARCHAR(255)` | NOT NULL | Nombre identificador del prompt |
| `content` | `TEXT` | NOT NULL | El texto completo del system prompt para el LLM |
| `version` | `VARCHAR(50)` | NOT NULL | Versión semántica (ej: "2.1.0") |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT FALSE | Solo un prompt puede estar activo a la vez |
| `guardrails_config` | `JSONB` | NOT NULL | Configuración de los guardrails asociados |
| `created_by` | `UUID` | NOT NULL | ID del admin que creó este prompt |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | Timestamp de creación |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | Timestamp de modificación |

**Constraints**: Solo un registro puede tener `is_active = TRUE`. Se implementa con un índice parcial único: `CREATE UNIQUE INDEX uq_active_prompt ON governance.tutor_system_prompts (is_active) WHERE is_active = TRUE`.

**Índices**: `ix_tutor_system_prompts_is_active`.

---

### Tabla: governance_events

**TABLA INMUTABLE — Auditoría del sistema.**

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| `id` | `UUID` | PK | Identificador único |
| `event_type` | `VARCHAR(100)` | NOT NULL | Tipo de evento de gobernanza |
| `actor_id` | `UUID` | NOT NULL | ID del usuario que realizó la acción |
| `target_type` | `VARCHAR(100)` | NULLABLE | Tipo de entidad afectada (ej: "tutor_prompt") |
| `target_id` | `UUID` | NULLABLE | ID de la entidad afectada |
| `details` | `JSONB` | NOT NULL | Detalle completo del evento |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | Timestamp inmutable |

**Catálogo de event_type**:

| event_type | Descripción |
|------------|-------------|
| `prompt.created` | Se creó un nuevo system prompt |
| `prompt.activated` | Se activó un prompt |
| `prompt.deactivated` | Se desactivó un prompt |
| `guardrail.triggered` | Un guardrail bloqueó una respuesta |
| `guardrail.overridden` | Un admin overrideó un guardrail |
| `course.created` | Se creó un curso |
| `enrollment.bulk_created` | Inscripción masiva de estudiantes |

**Índices**: `ix_governance_events_actor_id`, `ix_governance_events_event_type`, `ix_governance_events_created_at` (para auditoría por rango de fechas).

---

## 5. Schema: analytics

### Tabla: risk_assessments

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| `id` | `UUID` | PK | Identificador único |
| `student_id` | `UUID` | NOT NULL | Estudiante evaluado |
| `commission_id` | `UUID` | NOT NULL | Comisión en contexto |
| `risk_level` | `ENUM('low','medium','high','critical')` | NOT NULL | Nivel de riesgo actual |
| `risk_factors` | `JSONB` | NOT NULL | Factores que contribuyeron al riesgo |
| `recommendation` | `TEXT` | NULLABLE | Recomendación generada para el docente |
| `triggered_by` | `ENUM('automatic','manual','threshold')` | NOT NULL | Cómo se disparó esta evaluación |
| `assessed_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | Timestamp de la evaluación |
| `acknowledged_by` | `UUID` | NULLABLE | Docente que revisó la alerta |
| `acknowledged_at` | `TIMESTAMPTZ` | NULLABLE | Cuándo fue revisada |

**Índices**: `ix_risk_assessments_student_id`, `ix_risk_assessments_commission_id`, `ix_risk_assessments_risk_level`, `ix_risk_assessments_assessed_at` (para alertas recientes).

---

## 6. Estrategia de Índices

### Principios

1. **Indexar FKs**: Todas las FK tienen índice (PostgreSQL no los crea automáticamente).
2. **Índices compuestos**: Para queries con múltiples filtros frecuentes.
3. **GIN para arrays y JSONB**: Para búsquedas dentro de arrays y JSONB.
4. **Índices parciales**: Para filtros con condición fija (ej: `WHERE is_active = TRUE`).
5. **No sobre-indexar**: Los índices tienen costo en escritura. Solo índices justificados por queries reales.

### Índices Críticos por Query

| Query frecuente | Tabla | Índice |
|----------------|-------|--------|
| Login por email | `users` | `UNIQUE ix_users_email` |
| Ejercicios de una comisión | `exercises` | `ix_exercises_commission_id` |
| Última entrega de estudiante en ejercicio | `submissions` | `ix_submissions_student_exercise` (compuesto) |
| Eventos CTR de una sesión en orden | `cognitive_events` | `ix_cognitive_events_session_sequence` |
| Prompt activo del tutor | `tutor_system_prompts` | Índice parcial `WHERE is_active = TRUE` |
| Ejercicios por tag | `exercises` | `ix_exercises_topic_tags` (GIN) |
| Alertas de riesgo recientes | `risk_assessments` | `ix_risk_assessments_assessed_at` + `risk_level` |

### Definición de Índice GIN para topic_tags

```sql
CREATE INDEX ix_exercises_topic_tags 
ON operational.exercises USING GIN (topic_tags);

-- Query que lo usa:
SELECT * FROM operational.exercises 
WHERE topic_tags @> ARRAY['recursion', 'trees'];
```

### Índice Parcial para Prompt Activo

```sql
CREATE UNIQUE INDEX uq_active_tutor_prompt 
ON governance.tutor_system_prompts (is_active) 
WHERE is_active = TRUE;
-- Garantiza que solo existe 1 prompt activo en todo momento
```

---

## 7. Estrategia de Soft Delete

### Entidades con Soft Delete (is_active / deleted_at)

Las entidades de negocio que pueden ser "desactivadas" sin perder su historial usan soft delete:

| Tabla | Mecanismo | Razón |
|-------|-----------|-------|
| `users` | `is_active BOOLEAN` | Deshabilitar acceso sin perder historial |
| `courses` | `is_active BOOLEAN` | Cursos archivados pero referenciados |
| `commissions` | `is_active BOOLEAN` | Comisiones finalizadas |
| `exercises` | `is_active BOOLEAN` | Ejercicios retirados pero con entregas |
| `enrollments` | `is_active BOOLEAN` | Baja sin perder historial de entrega |

**Implementación en BaseRepository**:

```python
class BaseRepository:
    async def get_active(self, id: UUID) -> Model | None:
        stmt = select(self.model).where(
            self.model.id == id,
            self.model.is_active == True
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def soft_delete(self, id: UUID) -> None:
        stmt = update(self.model).where(
            self.model.id == id
        ).values(is_active=False)
        await self.session.execute(stmt)
```

### Entidades SIN Soft Delete (Inmutables)

Las siguientes tablas **nunca se eliminan ni modifican** por diseño:

| Tabla | Razón de Inmutabilidad |
|-------|----------------------|
| `code_snapshots` | Historial de edición — evidencia de proceso |
| `tutor_interactions` | Historial de conversación — auditable |
| `cognitive_events` | CTR — cadena hash, alteración invalida integridad |
| `reasoning_records` | CTR — igual que cognitive_events |
| `governance_events` | Auditoría — no se puede borrar |

**Implementación**: Permisos PostgreSQL en producción:
```sql
-- Solo INSERT en tablas inmutables
REVOKE UPDATE, DELETE ON cognitive.cognitive_events FROM app_user;
REVOKE UPDATE, DELETE ON cognitive.reasoning_records FROM app_user;
GRANT INSERT, SELECT ON cognitive.cognitive_events TO app_user;
```

---

## 8. Estructuras JSONB

### courses.topic_taxonomy

Árbol de temas del curso, usado para mapear ejercicios a unidades temáticas:

```json
{
  "version": "1.0",
  "topics": [
    {
      "id": "arrays",
      "label": "Arrays y Listas",
      "subtopics": [
        { "id": "arrays.basic", "label": "Operaciones básicas" },
        { "id": "arrays.sorting", "label": "Ordenamiento" },
        { "id": "arrays.searching", "label": "Búsqueda" }
      ]
    },
    {
      "id": "recursion",
      "label": "Recursión",
      "subtopics": [
        { "id": "recursion.basic", "label": "Casos base y recursivos" },
        { "id": "recursion.memoization", "label": "Memoización" }
      ]
    }
  ]
}
```

### exercises.test_cases

Casos de prueba para evaluación automática del ejercicio:

```json
{
  "language": "python",
  "timeout_ms": 5000,
  "memory_limit_mb": 128,
  "test_cases": [
    {
      "id": "tc_01",
      "description": "Lista vacía",
      "input": "[]",
      "expected_output": "0",
      "is_hidden": false,
      "weight": 0.2
    },
    {
      "id": "tc_02",
      "description": "Lista con un elemento",
      "input": "[42]",
      "expected_output": "42",
      "is_hidden": false,
      "weight": 0.3
    },
    {
      "id": "tc_03",
      "description": "Caso borde — valores negativos",
      "input": "[-1, -5, -3]",
      "expected_output": "-1",
      "is_hidden": true,
      "weight": 0.5
    }
  ]
}
```

### cognitive_events.payload

El payload varía según `event_type`:

```json
// event_type: "tutor.question_asked"
{
  "question": "¿Cómo puedo encontrar el máximo en una lista?",
  "code_context": "def find_max(lst):\n    pass",
  "session_context_length": 12,
  "inferred_n4_level": 4
}

// event_type: "code.run"
{
  "code_hash": "sha256:abc123...",
  "test_cases_passed": 2,
  "test_cases_total": 5,
  "execution_time_ms": 145,
  "stderr": ""
}

// event_type: "reflection.submitted"
{
  "prompt": "¿Qué estrategia usaste para resolver este problema?",
  "response": "Primero pensé en usar un loop...",
  "inferred_n1_score": 78.5
}
```

### reasoning_records.details

```json
// record_type: "hypothesis"
{
  "hypothesis": "Puedo resolver esto con un loop que recorra todos los elementos",
  "confidence": 0.7,
  "alternatives_considered": ["usar recursión", "usar sorted()"]
}

// record_type: "strategy"
{
  "chosen_approach": "iterativo con variable acumuladora",
  "rationale": "Más fácil de leer y sin overhead de stack",
  "pseudo_code": "max_val = lst[0]\nfor item in lst:\n    if item > max_val: max_val = item"
}
```

### governance_events.details

```json
// event_type: "guardrail.triggered"
{
  "guardrail": "AntiSolverGuard",
  "original_response_preview": "Para encontrar el máximo, podés usar max(lst)...",
  "reason": "La respuesta contiene solución directa al ejercicio",
  "action": "blocked",
  "student_id": "uuid-...",
  "exercise_id": "uuid-..."
}
```

### tutor_system_prompts.guardrails_config

```json
{
  "anti_solver": {
    "enabled": true,
    "forbidden_patterns": [
      "usar la función max()",
      "la respuesta es",
      "el resultado es"
    ],
    "sensitivity": "high"
  },
  "tone": {
    "style": "socratic",
    "max_response_tokens": 300,
    "language": "es"
  },
  "context_injection": {
    "include_exercise": true,
    "include_last_n_interactions": 10,
    "include_current_code": true
  }
}
```

---

## 9. Mecanismo de Hash Chain (CTR)

### Fundamento

El Registro de Traza Cognitiva (CTR) usa una cadena de hash SHA-256 para garantizar que ningún evento puede ser alterado retroactivamente sin detectarse. Es equivalente conceptualmente a un blockchain simplificado, sin distribución.

### Fórmula

```
hash(0) = SHA256("GENESIS_" + session_id + started_at.isoformat())
hash(n) = SHA256(hash(n-1) + event_type + serialize(payload) + created_at.isoformat())
```

Donde `serialize(payload)` es el payload JSONB serializado con claves ordenadas (para determinismo).

### Implementación en Python

```python
import hashlib
import json
from datetime import datetime
from uuid import UUID

class HashChainService:
    
    @staticmethod
    def compute_genesis_hash(session_id: UUID, started_at: datetime) -> str:
        """Calcula el hash inicial de la cadena para una nueva sesión."""
        data = f"GENESIS_{session_id}{started_at.isoformat()}"
        return hashlib.sha256(data.encode("utf-8")).hexdigest()
    
    @staticmethod
    def compute_event_hash(
        previous_hash: str,
        event_type: str,
        payload: dict,
        created_at: datetime
    ) -> str:
        """Calcula el hash del evento n dado el hash del evento n-1."""
        # Serialización determinista: claves ordenadas, sin espacios
        payload_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        data = f"{previous_hash}{event_type}{payload_str}{created_at.isoformat()}"
        return hashlib.sha256(data.encode("utf-8")).hexdigest()
    
    @staticmethod
    def verify_chain(events: list[dict]) -> tuple[bool, int | None]:
        """
        Verifica la integridad de una cadena de eventos.
        Retorna (True, None) si es válida o (False, sequence_number) del primer evento corrupto.
        """
        for i, event in enumerate(events):
            if i == 0:
                # El primer evento verifica su hash directamente
                recomputed = HashChainService.compute_event_hash(
                    event["previous_hash"],
                    event["event_type"],
                    event["payload"],
                    event["created_at"]
                )
            else:
                recomputed = HashChainService.compute_event_hash(
                    events[i-1]["current_hash"],
                    event["event_type"],
                    event["payload"],
                    event["created_at"]
                )
            
            if recomputed != event["current_hash"]:
                return False, event["sequence_number"]
        
        return True, None
```

### Flujo de Registro de un Evento CTR

```
1. Estudiante dispara una acción (ej: hace una pregunta al tutor)
        │
2. CognitiveService.record_event(session_id, event_type, payload)
        │
3. CognitiveRepository.get_last_hash(session_id)
   → Retorna el current_hash del último evento de esa sesión
   → Si no hay eventos: retorna genesis_hash de la sesión
        │
4. HashChainService.compute_event_hash(
       previous_hash=last_hash,
       event_type=event_type,
       payload=payload,
       created_at=now()
   ) → new_hash
        │
5. CognitiveRepository.save_event(
       session_id=session_id,
       event_type=event_type,
       sequence_number=last_sequence + 1,
       payload=payload,
       previous_hash=last_hash,
       current_hash=new_hash,
       created_at=now()
   )
        │
6. DB INSERT atómico → Si falla, el evento no se registra
```

### Verificación de Integridad

Un docente o auditor puede solicitar la verificación de la cadena de una sesión:

```
GET /teacher/sessions/{session_id}/trace?verify=true
        │
CognitiveService.get_trace(session_id, verify=True)
        │
→ CognitiveRepository.get_all_events(session_id, order_by=sequence_number ASC)
→ HashChainService.verify_chain(events)
→ Si válida: retorna la traza completa con { integrity: "verified" }
→ Si inválida: retorna { integrity: "compromised", first_broken_at: sequence_number }
```

### Por Qué No Usar Signed Tokens (JWT) para CTR

Alternativa evaluada: firmar cada evento con una clave privada del servidor.

**Rechazada porque**:
- El servidor podría re-firmar eventos alterados
- La cadena de hash hace que cada evento dependa de todos los anteriores: no se puede insertar ni eliminar un evento sin romper todos los hashes siguientes
- La verificación no requiere clave privada: es pública y determinista

---

*Documento generado: 2026-04-10 | Plataforma AI-Native v1.0*
