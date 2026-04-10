# API y Endpoints — Plataforma AI-Native

**Versión**: 1.0  
**Fecha**: 2026-04-10  
**Base URL**: `https://api.ainative.edu.ar/api/v1`  
**Protocolo WebSocket**: `wss://api.ainative.edu.ar/ws`  

---

## Tabla de Contenidos

1. [Convenciones Generales](#1-convenciones-generales)
2. [Autenticación y Autorización](#2-autenticación-y-autorización)
3. [Fase 0 — Auth](#3-fase-0--auth)
4. [Fase 1 — Core (Cursos, Ejercicios, Entregas)](#4-fase-1--core-cursos-ejercicios-entregas)
5. [Fase 2 — Tutor Socrático](#5-fase-2--tutor-socrático)
6. [Fase 3 — Cognitive y Evaluación](#6-fase-3--cognitive-y-evaluación)
7. [Códigos de Error Estándar](#7-códigos-de-error-estándar)
8. [Rate Limiting](#8-rate-limiting)

---

## 1. Convenciones Generales

### Prefijo de API

Todos los endpoints REST tienen el prefijo:
```
/api/v1/
```

### Wrapper de Respuesta Estándar

**Toda** respuesta de la API usa el mismo wrapper JSON:

```json
{
  "status": "ok",
  "data": { },
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "total_pages": 8
  },
  "errors": []
}
```

Para respuestas de error:
```json
{
  "status": "error",
  "data": null,
  "meta": null,
  "errors": [
    {
      "code": "EXERCISE_NOT_FOUND",
      "message": "El ejercicio con id 'uuid-...' no existe o no está disponible.",
      "field": null
    }
  ]
}
```

Para errores de validación Pydantic (múltiples campos):
```json
{
  "status": "error",
  "data": null,
  "meta": null,
  "errors": [
    {
      "code": "VALIDATION_ERROR",
      "message": "El campo es requerido.",
      "field": "email"
    },
    {
      "code": "VALIDATION_ERROR",
      "message": "La contraseña debe tener al menos 8 caracteres.",
      "field": "password"
    }
  ]
}
```

### Implementación del Wrapper (Pydantic)

```python
# shared/schemas/responses.py
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T")

class ErrorDetail(BaseModel):
    code: str
    message: str
    field: Optional[str] = None

class MetaInfo(BaseModel):
    page: int = 1
    per_page: int = 20
    total: int = 0
    total_pages: int = 0

class StandardResponse(BaseModel, Generic[T]):
    status: str = "ok"
    data: Optional[T] = None
    meta: Optional[MetaInfo] = None
    errors: list[ErrorDetail] = []

    @classmethod
    def ok(cls, data: T, meta: MetaInfo | None = None):
        return cls(status="ok", data=data, meta=meta)

    @classmethod
    def error(cls, errors: list[ErrorDetail]):
        return cls(status="error", data=None, errors=errors)
```

### Paginación

Los endpoints que retornan listas aceptan:

| Query Param | Tipo | Default | Descripción |
|-------------|------|---------|-------------|
| `page` | integer | 1 | Número de página |
| `per_page` | integer | 20 | Items por página (máx. 100) |
| `sort_by` | string | `created_at` | Campo de ordenamiento |
| `sort_dir` | `asc\|desc` | `desc` | Dirección de ordenamiento |

---

## 2. Autenticación y Autorización

### JWT Bearer Token

```
Authorization: Bearer <access_token>
```

- **Access token**: JWT con TTL de 15 minutos
- **Refresh token**: JWT con TTL de 7 días, almacenado en cookie HttpOnly

### Payload del JWT

```json
{
  "sub": "uuid-usuario",
  "email": "alumno@universidad.edu.ar",
  "role": "student",
  "iat": 1712345678,
  "exp": 1712346578,
  "jti": "uuid-token-id"
}
```

### Roles y Permisos

| Rol | Descripción | Acceso |
|-----|-------------|--------|
| `student` | Alumno inscripto | Sus propios datos, ejercicios de sus comisiones |
| `teacher` | Docente | Sus comisiones, datos de sus estudiantes |
| `admin` | Administrador | Todo |

### WebSocket — Autenticación

El token JWT se pasa como query param (no hay headers en WS):

```
wss://api.ainative.edu.ar/ws/tutor/chat?token=<access_token>
```

El servidor valida el token en el handshake inicial. Si el token es inválido o expiró, la conexión se rechaza con código 4001.

---

## 3. Fase 0 — Auth

### POST /api/v1/auth/register

Registro de nuevo usuario.

**Auth requerida**: No  
**Rate limit**: 5 req/min por IP

**Request Body**:
```json
{
  "email": "juan@universidad.edu.ar",
  "password": "securePassword123!",
  "full_name": "Juan Pérez",
  "role": "student"
}
```

| Campo | Tipo | Requerido | Validación |
|-------|------|-----------|------------|
| `email` | string | Sí | Formato email válido, dominio universitario |
| `password` | string | Sí | Min 8 chars, al menos 1 número y 1 mayúscula |
| `full_name` | string | Sí | Min 2 chars, max 255 chars |
| `role` | enum | No | `student` (default) o `teacher` |

**Response 201**:
```json
{
  "status": "ok",
  "data": {
    "user": {
      "id": "uuid-...",
      "email": "juan@universidad.edu.ar",
      "full_name": "Juan Pérez",
      "role": "student",
      "created_at": "2026-04-10T12:00:00Z"
    },
    "access_token": "eyJhbGc...",
    "token_type": "Bearer",
    "expires_in": 900
  }
}
```

**Errores posibles**:
- `409 CONFLICT` → `EMAIL_ALREADY_EXISTS`
- `422 UNPROCESSABLE` → `VALIDATION_ERROR` (campos inválidos)

---

### POST /api/v1/auth/login

Login con credenciales.

**Auth requerida**: No  
**Rate limit**: 10 req/min por IP, 5 intentos fallidos → bloqueo 15min

**Request Body**:
```json
{
  "email": "juan@universidad.edu.ar",
  "password": "securePassword123!"
}
```

**Response 200**:
```json
{
  "status": "ok",
  "data": {
    "user": {
      "id": "uuid-...",
      "email": "juan@universidad.edu.ar",
      "full_name": "Juan Pérez",
      "role": "student"
    },
    "access_token": "eyJhbGc...",
    "token_type": "Bearer",
    "expires_in": 900
  }
}
```

El `refresh_token` se establece como cookie HttpOnly:
```
Set-Cookie: refresh_token=eyJhbGc...; HttpOnly; Secure; SameSite=Strict; Max-Age=604800; Path=/api/v1/auth/refresh
```

**Errores posibles**:
- `401 UNAUTHORIZED` → `INVALID_CREDENTIALS`
- `403 FORBIDDEN` → `ACCOUNT_DISABLED`
- `429 TOO_MANY_REQUESTS` → `RATE_LIMIT_EXCEEDED`

---

### POST /api/v1/auth/refresh

Rotación del access token usando el refresh token.

**Auth requerida**: No (usa cookie HttpOnly)  
**Rate limit**: 30 req/min por usuario

**Request**: No body. El refresh token se lee de la cookie HttpOnly.

**Response 200**:
```json
{
  "status": "ok",
  "data": {
    "access_token": "eyJhbGc...",
    "token_type": "Bearer",
    "expires_in": 900
  }
}
```

**Errores posibles**:
- `401 UNAUTHORIZED` → `REFRESH_TOKEN_INVALID` o `REFRESH_TOKEN_EXPIRED`

---

### POST /api/v1/auth/logout

Invalida el refresh token actual.

**Auth requerida**: Bearer token  
**Rate limit**: No

**Request**: No body.

**Response 200**:
```json
{
  "status": "ok",
  "data": { "message": "Sesión cerrada correctamente." }
}
```

La cookie `refresh_token` se elimina con `Max-Age=0`.

---

## 4. Fase 1 — Core (Cursos, Ejercicios, Entregas)

### Cursos

---

#### GET /api/v1/courses

Lista todos los cursos activos.

**Auth requerida**: Bearer token (cualquier rol)  
**Rate limit**: 60 req/min

**Query Params**: `page`, `per_page`, `sort_by`, `sort_dir`

**Response 200**:
```json
{
  "status": "ok",
  "data": [
    {
      "id": "uuid-...",
      "name": "Algoritmos y Estructuras de Datos",
      "description": "Curso de AED...",
      "is_active": true,
      "created_at": "2026-03-01T00:00:00Z"
    }
  ],
  "meta": { "page": 1, "per_page": 20, "total": 5, "total_pages": 1 }
}
```

---

#### POST /api/v1/courses

Crea un nuevo curso.

**Auth requerida**: Bearer token (rol `admin`)

**Request Body**:
```json
{
  "name": "Algoritmos y Estructuras de Datos",
  "description": "Introducción a algoritmos...",
  "topic_taxonomy": { "version": "1.0", "topics": [] }
}
```

**Response 201**: Mismo formato que GET individual.

---

#### GET /api/v1/courses/{course_id}

Obtiene un curso por ID.

**Auth requerida**: Bearer token

**Response 200**: CourseResponse con campo `topic_taxonomy` incluido.

---

#### PUT /api/v1/courses/{course_id}

Actualiza un curso.

**Auth requerida**: Bearer token (rol `admin`)

**Request Body**: Mismos campos que POST, todos opcionales.

**Response 200**: CourseResponse actualizado.

---

#### DELETE /api/v1/courses/{course_id}

Soft delete de un curso (marca `is_active = false`).

**Auth requerida**: Bearer token (rol `admin`)

**Response 200**: `{ "message": "Curso desactivado." }`

---

### Comisiones

---

#### GET /api/v1/courses/{course_id}/commissions

Lista comisiones de un curso.

**Auth requerida**: Bearer token  
**Query Params**: `year`, `semester`, `is_active`

**Response 200**: Lista de CommissionResponse.

---

#### POST /api/v1/courses/{course_id}/commissions

Crea una comisión para el curso.

**Auth requerida**: Bearer token (rol `admin` o `teacher`)

**Request Body**:
```json
{
  "name": "Comisión A",
  "teacher_id": "uuid-...",
  "year": 2026,
  "semester": 1
}
```

**Response 201**: CommissionResponse.

---

#### GET /api/v1/commissions/{commission_id}

Obtiene detalle de una comisión.

**Auth requerida**: Bearer token

**Response 200**:
```json
{
  "status": "ok",
  "data": {
    "id": "uuid-...",
    "course_id": "uuid-...",
    "name": "Comisión A",
    "teacher": { "id": "uuid-...", "full_name": "Prof. García" },
    "year": 2026,
    "semester": 1,
    "is_active": true,
    "enrolled_students_count": 45
  }
}
```

---

#### PUT /api/v1/commissions/{commission_id}

Actualiza una comisión.

**Auth requerida**: Bearer token (rol `admin` o teacher owner)

**Response 200**: CommissionResponse actualizado.

---

### Inscripciones

---

#### POST /api/v1/commissions/{commission_id}/enrollments

Inscribe al usuario autenticado en una comisión.

**Auth requerida**: Bearer token (rol `student`)

**Request Body**: No body (el estudiante se inscribe a sí mismo).

**Response 201**:
```json
{
  "status": "ok",
  "data": {
    "id": "uuid-...",
    "student_id": "uuid-...",
    "commission_id": "uuid-...",
    "enrolled_at": "2026-04-10T12:00:00Z"
  }
}
```

**Errores posibles**:
- `409 CONFLICT` → `ALREADY_ENROLLED`
- `404 NOT_FOUND` → `COMMISSION_NOT_FOUND`

---

#### GET /api/v1/teacher/commissions/{commission_id}/enrollments

Lista los estudiantes inscriptos en una comisión.

**Auth requerida**: Bearer token (rol `teacher` o `admin`)  
**Rate limit**: 30 req/min

**Response 200**: Lista de EnrollmentResponse con datos del estudiante.

---

#### DELETE /api/v1/commissions/{commission_id}/enrollments/{enrollment_id}

Baja de un estudiante (soft delete, `is_active = false`).

**Auth requerida**: Bearer token (rol `admin` o teacher owner)

**Response 200**: `{ "message": "Inscripción cancelada." }`

---

### Ejercicios

---

#### GET /api/v1/commissions/{commission_id}/exercises

Lista ejercicios de una comisión.

**Auth requerida**: Bearer token (estudiante debe estar inscripto)  
**Query Params**: `difficulty`, `topic_tags`, `is_active`

**Response 200**: Lista de ExerciseResponse (sin `test_cases` hidden para estudiantes).

---

#### POST /api/v1/commissions/{commission_id}/exercises

Crea un ejercicio para la comisión.

**Auth requerida**: Bearer token (teacher owner o admin)

**Request Body**:
```json
{
  "title": "Máximo de una lista",
  "description": "Implementar una función que retorne el máximo...",
  "test_cases": {
    "language": "python",
    "timeout_ms": 5000,
    "test_cases": [
      { "id": "tc_01", "input": "[]", "expected_output": "None", "is_hidden": false, "weight": 0.5 }
    ]
  },
  "difficulty": "easy",
  "topic_tags": ["arrays", "iteration"],
  "order_index": 1
}
```

**Response 201**: ExerciseResponse completo.

---

#### GET /api/v1/exercises/{exercise_id}

Obtiene el detalle de un ejercicio.

**Auth requerida**: Bearer token

**Response 200**: ExerciseResponse. Los `test_cases` hidden solo se muestran a teachers/admins.

---

#### PUT /api/v1/exercises/{exercise_id}

Actualiza un ejercicio.

**Auth requerida**: Bearer token (teacher owner o admin)

**Response 200**: ExerciseResponse actualizado.

---

#### DELETE /api/v1/exercises/{exercise_id}

Soft delete de un ejercicio.

**Auth requerida**: Bearer token (admin)

**Response 200**: `{ "message": "Ejercicio desactivado." }`

---

### Sandbox y Entregas

---

#### POST /api/v1/student/exercises/{exercise_id}/run

Ejecuta código en el sandbox sin persistir como entrega. Para que el estudiante pruebe su código.

**Auth requerida**: Bearer token (rol `student`, debe estar inscripto)  
**Rate limit**: 30 req/min por usuario  
**Timeout de ejecución**: 5 segundos

**Request Body**:
```json
{
  "code": "def find_max(lst):\n    if not lst:\n        return None\n    return max(lst)",
  "language": "python"
}
```

**Response 200**:
```json
{
  "status": "ok",
  "data": {
    "execution_id": "uuid-...",
    "status": "passed",
    "test_results": [
      {
        "test_case_id": "tc_01",
        "passed": true,
        "actual_output": "None",
        "expected_output": "None",
        "execution_time_ms": 23
      },
      {
        "test_case_id": "tc_02",
        "passed": true,
        "actual_output": "42",
        "expected_output": "42",
        "execution_time_ms": 18
      }
    ],
    "tests_passed": 2,
    "tests_total": 3,
    "stderr": "",
    "execution_time_ms": 145
  }
}
```

**Errores posibles**:
- `408 TIMEOUT` → `EXECUTION_TIMEOUT`
- `429 TOO_MANY_REQUESTS` → `RATE_LIMIT_EXCEEDED`

---

#### POST /api/v1/student/exercises/{exercise_id}/submit

Envía una solución como entrega formal.

**Auth requerida**: Bearer token (rol `student`, inscripto)  
**Rate limit**: 10 req/min por usuario por ejercicio

**Request Body**:
```json
{
  "code": "def find_max(lst):\n    ...",
  "language": "python"
}
```

**Response 201**:
```json
{
  "status": "ok",
  "data": {
    "submission_id": "uuid-...",
    "status": "running",
    "submitted_at": "2026-04-10T12:30:00Z",
    "message": "Tu entrega está siendo evaluada."
  }
}
```

La evaluación es asíncrona. El status final se puede consultar via GET.

---

#### GET /api/v1/student/exercises/{exercise_id}/submissions

Lista las entregas del estudiante autenticado para un ejercicio.

**Auth requerida**: Bearer token (rol `student`)

**Response 200**: Lista de SubmissionSummaryResponse.

---

#### GET /api/v1/student/submissions/{submission_id}

Obtiene el detalle de una entrega.

**Auth requerida**: Bearer token (student owner, teacher, o admin)

**Response 200**:
```json
{
  "status": "ok",
  "data": {
    "id": "uuid-...",
    "exercise_id": "uuid-...",
    "student_id": "uuid-...",
    "code": "def find_max...",
    "status": "passed",
    "score": 95.0,
    "feedback": "Excelente implementación. Podría mejorarse...",
    "test_results": { },
    "submitted_at": "2026-04-10T12:30:00Z",
    "evaluated_at": "2026-04-10T12:30:05Z"
  }
}
```

---

#### POST /api/v1/student/submissions/{submission_id}/snapshots

Guarda un snapshot del código en proceso (autosave del editor).

**Auth requerida**: Bearer token (student owner)  
**Rate limit**: 1 req/30seg por submission (throttled en frontend)

**Request Body**:
```json
{
  "code": "def find_max(lst):\n    # work in progress\n    pass"
}
```

**Response 201**:
```json
{
  "status": "ok",
  "data": {
    "snapshot_id": "uuid-...",
    "snapshot_at": "2026-04-10T12:25:00Z"
  }
}
```

---

## 5. Fase 2 — Tutor Socrático

### WebSocket — Chat con el Tutor

---

#### WS /ws/tutor/chat

Conexión WebSocket para chat en streaming con el tutor socrático.

**Auth requerida**: `?token=<access_token>` en query param  
**Rate limit**: 1 sesión WS activa por usuario a la vez

**Handshake (cliente → servidor)**:

Al conectarse, el cliente envía el contexto inicial:
```json
{
  "type": "init",
  "payload": {
    "exercise_id": "uuid-...",
    "current_code": "def find_max(lst):\n    pass"
  }
}
```

**Enviar mensaje (cliente → servidor)**:
```json
{
  "type": "message",
  "payload": {
    "content": "No entiendo cómo encontrar el máximo sin usar la función max()"
  }
}
```

**Respuesta en streaming (servidor → cliente)**:

El servidor envía múltiples mensajes de tipo `chunk` seguidos de `done`:

```json
{ "type": "chunk", "payload": { "content": "Interesante pregunta. " } }
{ "type": "chunk", "payload": { "content": "¿Qué pasa si comparás " } }
{ "type": "chunk", "payload": { "content": "dos elementos a la vez?" } }
{ "type": "done", "payload": { "interaction_id": "uuid-...", "tokens_used": 87 } }
```

Si el guardrail bloquea la respuesta:
```json
{
  "type": "guardrail_blocked",
  "payload": {
    "reason": "La respuesta contenía una solución directa al ejercicio.",
    "alternative": "Pensá en qué comparación necesitás hacer entre dos elementos."
  }
}
```

**Cierre de conexión**:
```json
{ "type": "close", "payload": {} }
```

**Códigos de cierre WS**:

| Código | Descripción |
|--------|-------------|
| 1000 | Cierre normal |
| 4001 | Token inválido o expirado |
| 4002 | Ejercicio no encontrado o no disponible |
| 4003 | El estudiante no está inscripto en la comisión |
| 4004 | Rate limit excedido |
| 4005 | Sesión WS duplicada (ya hay una sesión activa) |

---

### Reflexiones

---

#### POST /api/v1/student/exercises/{exercise_id}/reflection

El estudiante completa una reflexión guiada sobre el problema.

**Auth requerida**: Bearer token (rol `student`)  
**Rate limit**: 5 req/hora por ejercicio

**Request Body**:
```json
{
  "reflection_type": "pre_solving",
  "responses": {
    "what_do_you_understand": "El problema pide encontrar el elemento más grande...",
    "what_is_your_strategy": "Voy a recorrer la lista comparando cada elemento...",
    "what_difficulties_do_you_anticipate": "No sé cómo manejar la lista vacía..."
  }
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `reflection_type` | enum | Sí | `pre_solving`, `mid_solving`, `post_solving` |
| `responses` | object | Sí | Respuestas del estudiante (keys varían por tipo) |

**Response 201**:
```json
{
  "status": "ok",
  "data": {
    "reflection_id": "uuid-...",
    "n1_score_preview": 72.5,
    "feedback": "Tu comprensión inicial del problema es buena. Te sugiero que...",
    "created_at": "2026-04-10T12:00:00Z"
  }
}
```

---

### Endpoints de Docente para Tutor

---

#### GET /api/v1/teacher/tutor/interactions

Lista las interacciones con el tutor, filtradas.

**Auth requerida**: Bearer token (rol `teacher` o `admin`)  
**Rate limit**: 30 req/min

**Query Params**:

| Param | Tipo | Descripción |
|-------|------|-------------|
| `student_id` | UUID | Filtrar por estudiante |
| `exercise_id` | UUID | Filtrar por ejercicio |
| `commission_id` | UUID | Filtrar por comisión |
| `date_from` | date | Desde fecha (YYYY-MM-DD) |
| `date_to` | date | Hasta fecha |
| `n4_level` | integer (1-4) | Filtrar por nivel N4 detectado |

**Response 200**:
```json
{
  "status": "ok",
  "data": [
    {
      "id": "uuid-...",
      "student": { "id": "uuid-...", "full_name": "Ana García" },
      "exercise": { "id": "uuid-...", "title": "Máximo de una lista" },
      "role": "user",
      "content": "¿Cómo puedo comparar dos elementos?",
      "n4_level": 4,
      "created_at": "2026-04-10T12:00:00Z"
    }
  ],
  "meta": { "page": 1, "per_page": 20, "total": 87, "total_pages": 5 }
}
```

---

### Gestión de System Prompts (Admin)

---

#### GET /api/v1/admin/tutor/system-prompts

Lista todos los system prompts del tutor.

**Auth requerida**: Bearer token (rol `admin`)

**Response 200**: Lista de TutorSystemPromptResponse.

---

#### POST /api/v1/admin/tutor/system-prompts

Crea un nuevo system prompt.

**Auth requerida**: Bearer token (rol `admin`)

**Request Body**:
```json
{
  "name": "Socratic v2.1 — Strict",
  "version": "2.1.0",
  "content": "Sos un tutor socrático experto en programación...",
  "guardrails_config": {
    "anti_solver": { "enabled": true, "sensitivity": "high" },
    "tone": { "style": "socratic", "max_response_tokens": 300 }
  }
}
```

**Response 201**: TutorSystemPromptResponse.

---

#### PUT /api/v1/admin/tutor/system-prompts/{prompt_id}

Actualiza un system prompt existente.

**Auth requerida**: Bearer token (rol `admin`)

**Response 200**: TutorSystemPromptResponse actualizado.

---

#### POST /api/v1/admin/tutor/system-prompts/{prompt_id}/activate

Activa este prompt y desactiva el anterior.

**Auth requerida**: Bearer token (rol `admin`)

**Response 200**:
```json
{
  "status": "ok",
  "data": {
    "activated": { "id": "uuid-nuevo", "version": "2.1.0" },
    "deactivated": { "id": "uuid-anterior", "version": "2.0.0" }
  }
}
```

---

#### DELETE /api/v1/admin/tutor/system-prompts/{prompt_id}

Elimina un system prompt (solo si no está activo).

**Auth requerida**: Bearer token (rol `admin`)

**Errores posibles**:
- `409 CONFLICT` → `CANNOT_DELETE_ACTIVE_PROMPT`

---

## 6. Fase 3 — Cognitive y Evaluación

### Sesiones Cognitivas

---

#### POST /api/v1/cognitive/sessions/start

Inicia una sesión cognitiva para un ejercicio.

**Auth requerida**: Bearer token (rol `student`)  
**Rate limit**: 10 req/hora por usuario

**Request Body**:
```json
{
  "exercise_id": "uuid-..."
}
```

**Response 201**:
```json
{
  "status": "ok",
  "data": {
    "session_id": "uuid-...",
    "exercise_id": "uuid-...",
    "genesis_hash": "sha256:abc123...",
    "started_at": "2026-04-10T12:00:00Z",
    "status": "open"
  }
}
```

**Errores posibles**:
- `409 CONFLICT` → `SESSION_ALREADY_OPEN` (ya hay una sesión abierta para ese ejercicio)

---

#### POST /api/v1/cognitive/sessions/{session_id}/close

Cierra una sesión cognitiva y calcula las métricas finales.

**Auth requerida**: Bearer token (student owner)

**Request Body**: No body.

**Response 200**:
```json
{
  "status": "ok",
  "data": {
    "session_id": "uuid-...",
    "session_hash": "sha256:xyz...",
    "n4_final_score": {
      "n1_comprehension": 78.5,
      "n2_strategy": 65.0,
      "n3_validation": 82.0,
      "n4_ai_interaction": 55.0,
      "composite": 70.1
    },
    "total_events": 24,
    "duration_minutes": 47,
    "closed_at": "2026-04-10T12:47:00Z"
  }
}
```

---

### Eventos Cognitivos

---

#### POST /api/v1/cognitive/events

Registra un evento cognitivo en la cadena CTR.

**Auth requerida**: Bearer token (rol `student`)  
**Rate limit**: 60 req/min (alta frecuencia — autosave y snapshots son eventos)

**Request Body**:
```json
{
  "session_id": "uuid-...",
  "event_type": "code.snapshot",
  "payload": {
    "code_hash": "sha256:def456...",
    "test_cases_passed": 1,
    "test_cases_total": 3
  }
}
```

**Response 201**:
```json
{
  "status": "ok",
  "data": {
    "event_id": "uuid-...",
    "sequence_number": 8,
    "current_hash": "sha256:ghi789...",
    "created_at": "2026-04-10T12:15:00Z"
  }
}
```

**Errores posibles**:
- `404 NOT_FOUND` → `SESSION_NOT_FOUND`
- `409 CONFLICT` → `SESSION_CLOSED` (la sesión ya fue cerrada)
- `400 BAD_REQUEST` → `INVALID_EVENT_TYPE`

---

### Dashboard del Docente

---

#### GET /api/v1/teacher/courses/{course_id}/dashboard

Dashboard general del curso con métricas agregadas.

**Auth requerida**: Bearer token (teacher owner o admin)  
**Rate limit**: 10 req/min (query intensiva)

**Query Params**: `commission_id`, `date_from`, `date_to`

**Response 200**:
```json
{
  "status": "ok",
  "data": {
    "course_id": "uuid-...",
    "commission_id": "uuid-...",
    "period": { "from": "2026-03-01", "to": "2026-04-10" },
    "summary": {
      "total_students": 45,
      "active_students_last_7_days": 38,
      "total_submissions": 180,
      "avg_score": 72.3,
      "at_risk_students": 6
    },
    "n4_distribution": {
      "avg_n1": 75.2,
      "avg_n2": 68.4,
      "avg_n3": 71.1,
      "avg_n4": 52.8
    },
    "risk_breakdown": {
      "low": 32,
      "medium": 7,
      "high": 5,
      "critical": 1
    },
    "exercise_completion_rates": [
      { "exercise_id": "uuid-...", "title": "Máximo de lista", "completion_rate": 0.87 }
    ]
  }
}
```

---

#### GET /api/v1/teacher/students/{student_id}/profile

Perfil cognitivo detallado de un estudiante.

**Auth requerida**: Bearer token (teacher del curso o admin)  
**Rate limit**: 30 req/min

**Query Params**: `commission_id`

**Response 200**:
```json
{
  "status": "ok",
  "data": {
    "student": {
      "id": "uuid-...",
      "full_name": "Ana García",
      "email": "ana@universidad.edu.ar"
    },
    "cognitive_profile": {
      "overall_n4_score": {
        "n1_comprehension": 78.5,
        "n2_strategy": 65.0,
        "n3_validation": 82.0,
        "n4_ai_interaction": 55.0
      },
      "autonomy_trend": "improving",
      "help_seeking_ratio": 0.35,
      "risk_level": "medium",
      "total_sessions": 12,
      "total_exercises_attempted": 8,
      "avg_session_duration_minutes": 42
    },
    "recent_sessions": [
      {
        "session_id": "uuid-...",
        "exercise_title": "Máximo de lista",
        "status": "closed",
        "n4_composite": 70.1,
        "started_at": "2026-04-08T10:00:00Z"
      }
    ],
    "alerts": [
      {
        "type": "high_help_seeking",
        "description": "El estudiante consultó al tutor en el 80% de los pasos.",
        "severity": "medium"
      }
    ]
  }
}
```

---

#### GET /api/v1/teacher/sessions/{session_id}/trace

Obtiene la traza completa CTR de una sesión cognitiva.

**Auth requerida**: Bearer token (teacher del curso o admin)  
**Rate limit**: 20 req/min

**Query Params**: `verify_integrity` (boolean, default false)

**Response 200**:
```json
{
  "status": "ok",
  "data": {
    "session_id": "uuid-...",
    "student": { "id": "uuid-...", "full_name": "Ana García" },
    "exercise": { "id": "uuid-...", "title": "Máximo de lista" },
    "integrity": "verified",
    "genesis_hash": "sha256:abc...",
    "session_hash": "sha256:xyz...",
    "events": [
      {
        "sequence_number": 1,
        "event_type": "session.started",
        "payload": {},
        "current_hash": "sha256:111...",
        "created_at": "2026-04-10T12:00:00Z"
      },
      {
        "sequence_number": 2,
        "event_type": "tutor.question_asked",
        "payload": { "question": "¿Cómo empiezo?", "inferred_n4_level": 4 },
        "current_hash": "sha256:222...",
        "created_at": "2026-04-10T12:02:30Z"
      }
    ],
    "total_events": 24
  }
}
```

Si `verify_integrity=true` y la cadena está comprometida:
```json
{
  "integrity": "compromised",
  "first_broken_at_sequence": 7
}
```

---

#### GET /api/v1/teacher/exercises/{exercise_id}/patterns

Analiza los patrones cognitivos de todos los estudiantes en un ejercicio.

**Auth requerida**: Bearer token (teacher o admin)  
**Rate limit**: 5 req/min (query muy intensiva)

**Query Params**: `commission_id`

**Response 200**:
```json
{
  "status": "ok",
  "data": {
    "exercise_id": "uuid-...",
    "total_sessions_analyzed": 45,
    "common_patterns": [
      {
        "pattern": "early_tutor_dependency",
        "description": "43% de los estudiantes consultaron al tutor antes del primer intento de código",
        "affected_students": 19,
        "recommendation": "Considerar una actividad de comprensión previa obligatoria"
      }
    ],
    "difficulty_heatmap": {
      "n1_avg": 72.0,
      "n2_avg": 58.3,
      "n3_avg": 68.0,
      "n4_avg": 61.2
    },
    "common_misconceptions": [
      {
        "description": "Confusión entre índice y valor al iterar la lista",
        "frequency": 0.31
      }
    ]
  }
}
```

---

## 7. Códigos de Error Estándar

| Código HTTP | Error Code | Descripción |
|-------------|-----------|-------------|
| 400 | `VALIDATION_ERROR` | Datos de entrada inválidos |
| 400 | `INVALID_EVENT_TYPE` | Tipo de evento cognitivo desconocido |
| 401 | `UNAUTHORIZED` | No hay token o token inválido |
| 401 | `INVALID_CREDENTIALS` | Email o contraseña incorrectos |
| 401 | `REFRESH_TOKEN_EXPIRED` | El refresh token expiró |
| 401 | `REFRESH_TOKEN_INVALID` | El refresh token fue invalidado |
| 403 | `FORBIDDEN` | Token válido pero sin permisos |
| 403 | `ACCOUNT_DISABLED` | La cuenta está deshabilitada |
| 403 | `NOT_ENROLLED` | El estudiante no está inscripto |
| 404 | `NOT_FOUND` | Recurso no encontrado |
| 404 | `EXERCISE_NOT_FOUND` | El ejercicio no existe |
| 404 | `SESSION_NOT_FOUND` | La sesión cognitiva no existe |
| 408 | `EXECUTION_TIMEOUT` | El código excedió el tiempo límite |
| 409 | `ALREADY_ENROLLED` | El estudiante ya está inscripto |
| 409 | `EMAIL_ALREADY_EXISTS` | El email ya está registrado |
| 409 | `SESSION_ALREADY_OPEN` | Ya hay una sesión abierta |
| 409 | `SESSION_CLOSED` | La sesión ya fue cerrada |
| 409 | `CANNOT_DELETE_ACTIVE_PROMPT` | No se puede borrar el prompt activo |
| 429 | `RATE_LIMIT_EXCEEDED` | Demasiadas peticiones |
| 500 | `INTERNAL_ERROR` | Error interno del servidor |
| 503 | `LLM_UNAVAILABLE` | La API del LLM no está disponible |

---

## 8. Rate Limiting

### Estrategia

Rate limiting implementado con Redis usando el algoritmo **Token Bucket** por usuario o por IP.

### Límites por Endpoint

| Endpoint | Límite | Ventana | Scope |
|----------|--------|---------|-------|
| `POST /auth/register` | 5 req | 1 min | Por IP |
| `POST /auth/login` | 10 req | 1 min | Por IP |
| `POST /auth/login` (fallidos) | 5 intentos | 15 min | Por IP + email |
| `POST /student/exercises/{id}/run` | 30 req | 1 min | Por usuario |
| `POST /student/exercises/{id}/submit` | 10 req | 1 min | Por usuario + ejercicio |
| `WS /ws/tutor/chat` | 1 conexión activa | — | Por usuario |
| `POST /cognitive/events` | 60 req | 1 min | Por usuario |
| `GET /teacher/exercises/{id}/patterns` | 5 req | 1 min | Por usuario |

### Headers de Rate Limit en Respuesta

```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 27
X-RateLimit-Reset: 1712345700
Retry-After: 43  (solo cuando se excede el límite)
```

### Respuesta 429

```json
{
  "status": "error",
  "data": null,
  "errors": [
    {
      "code": "RATE_LIMIT_EXCEEDED",
      "message": "Demasiadas peticiones. Intentá de nuevo en 43 segundos.",
      "field": null
    }
  ]
}
```

---

*Documento generado: 2026-04-10 | Plataforma AI-Native v1.0*
