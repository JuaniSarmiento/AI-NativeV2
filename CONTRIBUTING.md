# Guía de Contribución — Plataforma AI-Native

**UTN FRM | Sistema Pedagógico para Enseñanza de Programación**
Última actualización: 2026-04-10

---

## Bienvenido al proyecto

La Plataforma AI-Native es la implementación de un modelo teórico pedagógico (N4) para una tesis doctoral en UTN FRM. Cada línea de código que escribís tiene impacto directo en cómo se evalúa el proceso cognitivo de los alumnos.

Esta guía describe todo lo que necesitás saber para contribuir de forma efectiva y coherente con el resto del equipo.

---

## Índice

1. [Empezar](#1-empezar)
2. [Código de Conducta](#2-código-de-conducta)
3. [Cómo Reportar Bugs](#3-cómo-reportar-bugs)
4. [Cómo Proponer Features](#4-cómo-proponer-features)
5. [Workflow de Desarrollo](#5-workflow-de-desarrollo)
6. [Convenciones de Commits](#6-convenciones-de-commits)
7. [Guía de Pull Requests](#7-guía-de-pull-requests)
8. [Estilo de Código](#8-estilo-de-código)
9. [Requisitos de Testing](#9-requisitos-de-testing)
10. [Documentación](#10-documentación)
11. [Propiedad de Fases y Schemas](#11-propiedad-de-fases-y-schemas)

---

## 1. Empezar

### Onboarding

Para configurar el entorno de desarrollo desde cero, seguir la guía completa en:

```
knowledge-base/05-dx/01_onboarding.md
```

El onboarding cubre: prerrequisitos de sistema, clonar el repo, configurar variables de entorno, levantar Docker Compose, correr seed data y verificar que todo funciona.

### Verificación de Setup

Una vez configurado el entorno, verificar que todo funciona:

```bash
# Levantar el entorno
docker compose up -d

# Verificar el backend
curl http://localhost:8000/api/v1/health
# Esperado: {"status": "ok", ...}

# Correr tests
cd backend && pytest tests/unit/ -v
cd frontend && npm run test:run

# Verificar el frontend
open http://localhost:5173
```

Si algo no funciona, consultar primero:
- `knowledge-base/05-dx/03_trampas_conocidas.md` — problemas comunes documentados
- Abrir una issue con label `question` si el problema no está documentado

### Estructura del Proyecto

```
/backend    → FastAPI + SQLAlchemy async (Python 3.12)
/frontend   → React 19 + Zustand 5 + TailwindCSS 4 (TypeScript)
/shared     → Contratos OpenAPI + tipos TypeScript compartidos
/infra      → Docker Compose + scripts de infra
```

---

## 2. Código de Conducta

Este es un proyecto académico de equipo. Las expectativas básicas:

- **Feedback honesto sobre el código, no sobre la persona.** "Esta query tiene un N+1 porque..." en lugar de "esto está mal".
- **Preguntar antes de asumir.** Si algo no está claro en el código de otro, preguntar en el PR o en el chat del equipo.
- **Respetar la propiedad de fases.** Cada dev es dueño de su dominio. No modificar código de otro dominio sin coordinación previa.
- **Documentar las decisiones.** Si tomás una decisión de diseño no obvia, documentarla en un comentario o en `knowledge-base/02-arquitectura/07_adrs.md`.
- **No mergear bajo presión.** Si el CI está rojo o falta un review, esperar. Un merge apurado puede romper el trabajo de otros.

---

## 3. Cómo Reportar Bugs

### Antes de abrir una issue

1. Buscar en las issues existentes si el bug ya fue reportado.
2. Verificar que estás en la versión actualizada de `main` (`git pull origin main`).
3. Revisar `knowledge-base/05-dx/03_trampas_conocidas.md` por si es un problema conocido.

### Abrir la issue

Usar el template de bug disponible en GitHub (`Issues → New Issue → Bug Report`). Incluir obligatoriamente:

- **Descripción clara** del problema.
- **Pasos exactos para reproducirlo** (no "a veces falla", sino los pasos precisos).
- **Comportamiento esperado vs comportamiento actual**.
- **Logs o screenshots** relevantes.
- **Contexto**: OS, browser (si es frontend), rama y commit donde se encontró el bug.

Asignar los labels: `bug` + la fase correspondiente (`fase-1`, `fase-2`, etc.) + prioridad sugerida (`P0` si el sistema no funciona, `P1` si una feature principal está bloqueada).

### Prioridades de bugs

| Prioridad | Cuándo | Expectativa de respuesta |
|-----------|--------|--------------------------|
| P0 | El sistema no funciona (DB caída, auth roto, datos corruptos) | Atención inmediata |
| P1 | Una feature principal está bloqueada | Mismo día |
| P2 | Feature degradada, hay workaround | Próximo sprint |
| P3 | Cosmético, edge case raro | Backlog |

---

## 4. Cómo Proponer Features

### Para features pequeñas (1-3 archivos, cambio puntual)

1. Abrir una issue con label `feature` + fase + prioridad.
2. Describir: qué se necesita, por qué, criterios de aceptación.
3. Referenciar la HU correspondiente si existe (ej: `Refs: HU-024`).
4. Esperar feedback del equipo antes de empezar a codear.

### Para features complejas (4+ archivos, decisión arquitectónica)

1. Abrir la issue igual que arriba.
2. Crear un change con artefactos OPSX para documentar el diseño:

```bash
/opsx:propose "nombre-del-feature"
```

Los artefactos en `openspec/changes/{nombre}/` deben responder:
- `proposal.md`: qué y por qué
- `design.md`: cómo (schemas, contratos de API, decisiones de diseño)
- `tasks.md`: lista de tareas con dependencias
- `specs/`: specs de cada componente

3. Compartir el change con el equipo para feedback antes de implementar.

### Regla importante

**Ninguna feature modifica el modelo N4, el vocabulario canónico de eventos cognitivos, o las reglas de negocio sin coordinación explícita del equipo.** Estos son artefactos de la tesis — cambiarlos tiene impacto en la coherencia teórica del sistema.

---

## 5. Workflow de Desarrollo

El proyecto usa **GitHub Flow**:

```
main ← única rama permanente, siempre deployable
  │
  ├── feat/{descripcion}  ← tu trabajo va aquí
  │         │
  │         └── PR → review → merge → branch borrada
  │
  └── fix/{descripcion}   ← igual para bugs
```

### Paso a Paso

**1. Crear la branch desde main actualizado:**

```bash
git checkout main
git pull origin main
git checkout -b feat/e3-cognitive-event-classifier
```

El nombre de la branch sigue el patrón `{tipo}/{descripcion-en-kebab}`. Ver `metodologia_github.md` para la lista completa de tipos y ejemplos.

**2. Trabajar en la branch:**

```bash
# Commits frecuentes y pequeños
git add backend/app/features/cognitive/classifier.py
git commit -m "feat(cognitive): add event type to N4 level mapping"

git add tests/unit/test_cognitive_classifier.py
git commit -m "test(cognitive): add unit tests for event classifier mapping"
```

**3. Mantener la branch actualizada con main:**

```bash
# Antes de hacer el PR y si hay cambios en main que afectan tu trabajo
git fetch origin
git rebase origin/main
```

**4. Verificar antes del PR:**

```bash
# Backend
cd backend
pytest tests/ -v
ruff check .
mypy app/

# Frontend
cd frontend
npm run test:run
npm run lint
npm run build
```

**5. Crear el PR:**
- Título: formato de Conventional Commits (`feat(cognitive): add event classifier with N4 mapping`)
- Descripción: completar el template (qué cambia, cómo testear, checklist)
- Asignar a un reviewer

**6. Iterar en la review:**
- Responder cada comentario del reviewer
- Pushear los cambios: `git push origin feat/e3-cognitive-event-classifier`
- Cuando el CI pasa y hay 1 aprobación: mergear con **Squash and Merge**

**7. Limpiar:**
La branch se borra automáticamente después del merge (configurado en GitHub).

---

## 6. Convenciones de Commits

El proyecto usa **Conventional Commits** de forma estricta. Un pre-commit hook rechaza commits que no cumplan el formato.

### Formato

```
<tipo>(<alcance>): <descripción en infinitivo, minúsculas>

[cuerpo opcional: qué y por qué — separado por línea en blanco]

[Refs: #issue-number]
```

### Tipos válidos

| Tipo | Cuándo |
|------|--------|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de bug |
| `refactor` | Refactoring sin cambio de comportamiento |
| `test` | Agregar o modificar tests |
| `docs` | Solo documentación |
| `chore` | Dependencias, configuración, CI |
| `perf` | Mejora de performance |
| `ci` | Cambios en GitHub Actions |

### Alcances válidos

```
auth, courses, exercises, sandbox, tutor, cognitive, evaluation,
governance, hash-chain, db, api, dashboard, editor, chat, store,
msw, infra, ci, deps
```

### Ejemplos correctos

```
feat(cognitive): add cognitive event classifier with N4 mapping

Implementa el mapeo canónico event_type → N4 level según el documento
maestro empate3. Incluye validación de payload mínimo por event_type.

Refs: #24

---

fix(hash-chain): use sorted JSON keys for deterministic hash computation

test(tutor): add 8 adversarial prompts for role-play bypass category

chore(deps): update anthropic SDK to v0.40.0
```

### Ejemplos incorrectos

```
Fixed bug          # sin tipo, sin scope, en pasado
feat: stuff        # descripción no informativa
FEAT(AUTH): Login  # tipo en mayúsculas
feat(auth): Added login.  # pasado y con punto
```

---

## 7. Guía de Pull Requests

### PRs pequeños y enfocados

- Un PR resuelve una issue (o una parte bien definida de una issue grande).
- Si el PR tiene más de 500 líneas de cambios: dividirlo en PRs más pequeños.
- Un PR no debería mezclar: nuevas features + refactoring + bugfixes. Separarlos.

### Título del PR

Mismo formato que un Conventional Commit (es el commit de squash que queda en `main`):

```
feat(cognitive): add event classifier with N4 level mapping (#24)
fix(hash-chain): prevent duplicate genesis hash on session reopen (#31)
```

### Descripción del PR

Completar el template con:
- **Descripción**: qué hace el PR en 2-3 oraciones.
- **Cambios principales**: lista de los cambios más importantes.
- **Cómo testear**: pasos específicos para verificar que funciona.
- **Screenshots**: para cambios visuales en el frontend.
- **Checklist**: tests pasan, linter sin errores, convenciones seguidas, etc.
- **Issues relacionados**: `Closes #24` o `Refs #24`.

### Antes de solicitar review

Verificar el checklist:

- [ ] Los tests pasan localmente
- [ ] El linter no reporta errores
- [ ] El código sigue las convenciones del proyecto
- [ ] No hay cambios en schemas de otros dominios sin coordinación
- [ ] La OpenAPI spec está actualizada si se agregaron endpoints
- [ ] La knowledge-base está actualizada si cambió la arquitectura
- [ ] No hay secretos hardcodeados (API keys, passwords)
- [ ] Los nuevos endpoints tienen los checks de auth correctos

### Qué pasa en el code review

El reviewer revisa: corrección funcional, calidad de código, tests, arquitectura y seguridad. Ver `metodologia_github.md § Proceso de Code Review` para los criterios completos.

Los comentarios del reviewer son: **bloqueante** (debe resolverse antes del merge), **sugerencia** (opcional) o **pregunta** (solo curiosidad). El autor debe responder todos los comentarios explícitamente.

### Merge

- Merge con **Squash and Merge** siempre.
- El CI (lint + unit tests + integration tests) debe pasar.
- Al menos 1 aprobación de otro miembro del equipo.
- El autor puede mergear después de recibir la aprobación.

---

## 8. Estilo de Código

### Python (Backend)

**Linter y formatter**: `ruff` maneja ambos. Configurado en `pyproject.toml`.

```bash
cd backend
ruff check .       # verificar errores de linting
ruff format .      # formatear el código
```

**Type checker**: `mypy` en modo strict.

```bash
mypy app/
```

**Reglas clave:**
- Type hints obligatorios en todas las firmas de función.
- Usar `X | None` en lugar de `Optional[X]` (sintaxis Python 3.10+).
- Usar `list[X]` en lugar de `List[X]` (sintaxis Python 3.9+).
- `snake_case` para variables, funciones y archivos.
- `PascalCase` para clases.
- `UPPER_SNAKE_CASE` para constantes de módulo.
- Docstrings en servicios y funciones públicas importantes.

Ver `knowledge-base/05-dx/04_convenciones_y_estandares.md` para la referencia completa.

### TypeScript (Frontend)

**Linter**: ESLint configurado en `frontend/eslint.config.ts`.
**Formatter**: Prettier configurado en `frontend/.prettierrc`.

```bash
cd frontend
npm run lint           # verificar errores de linting
npm run format         # formatear el código
npm run format:check   # verificar formato sin cambiar archivos (para CI)
```

**Reglas clave:**
- TypeScript en modo `strict: true`. NUNCA deshabilitar.
- No usar `any`. Usar `unknown` si el tipo es genuinamente desconocido.
- `camelCase` para variables y funciones.
- `PascalCase` para componentes y tipos/interfaces.
- `UPPER_SNAKE_CASE` para constantes de configuración.
- Preferir `interface` para objetos de dominio, `type` para unions/intersections.
- Usar `useShallow` de Zustand para selectors que desestructuran múltiples campos.

### Reglas transversales de estilo

- **Sin comentarios obvios**: `// incrementar el contador` → eliminar. El código debe ser legible.
- **Sí a comentarios de por qué**: `// usar sorted_keys para garantizar determinismo en el hash` → mantener.
- **Sin código comentado**: si algo está comentado y no se usa, borrarlo. El historial de git lo preserva.
- **Sin `TODO:` sin issue**: si hay un pendiente, abrir una issue y referenciarla: `# TODO: optimizar con índice compuesto — ver #45`.

---

## 9. Requisitos de Testing

### Regla base

**No hay PR sin tests.** Todo el código de producción nuevo debe tener tests que lo cubran.

### Cobertura mínima

- **Total**: 80% de cobertura de líneas.
- **Módulos críticos** (hash chain, guardrails del tutor, core de seguridad): 95%+.
- El CI falla si la cobertura cae respecto a `main`.

### Qué tipo de test escribir

| Caso | Tipo de test |
|------|-------------|
| Lógica de service con dependencias mockeadas | Unit test |
| Cálculo de hashes, transformaciones, validaciones | Unit test |
| Endpoint HTTP completo → DB real | Integration test |
| Store de Zustand (acciones, selectores) | Vitest unit test |
| Componente React con interacciones | Vitest + Testing Library |
| Flujo completo de usuario (login → feature → logout) | E2E con Playwright |
| Tutor ante prompts adversariales | Adversarial test (suite especial) |

### Estructura de tests del backend

```python
# Formato de nombre: test_{qué}_{condición}
def test_create_exercise_with_valid_data_returns_exercise(): ...
def test_create_exercise_with_invalid_difficulty_raises_error(): ...
def test_hash_chain_with_tampered_event_fails_verification(): ...

# Estructura AAA (Arrange, Act, Assert)
async def test_create_exercise_returns_created_exercise(session, test_user):
    # Arrange
    request = CreateExerciseRequest(title="Test", description="Test desc", difficulty=2, course_id=uuid4())
    service = ExerciseService(ExerciseRepository(session))

    # Act
    exercise = await service.create_exercise(request, test_user)

    # Assert
    assert exercise.id is not None
    assert exercise.title == "Test"
    assert exercise.is_active is True
```

### Estructura de tests del frontend

```typescript
// Resetear el store entre tests para aislamiento
beforeEach(() => { useExerciseStore.getState().reset() })

// Usar data-testid para seleccionar elementos en tests (no CSS classes)
// <button data-testid="run-button">Ejecutar</button>
// screen.getByTestId('run-button')
```

### Tests adversariales del tutor

Los tests adversariales (`tests/adversarial/`) verifican que el tutor nunca da soluciones directas ante inputs maliciosos. Son **obligatorios** antes de cualquier cambio en el system prompt o en los guardrails.

```bash
# Correr tests adversariales (requiere ANTHROPIC_API_KEY)
ANTHROPIC_API_KEY=xxx pytest tests/adversarial/ -v -m adversarial
```

Estos tests no corren en el CI normal (son costosos). Corren semanalmente en un job separado y antes de releases.

### Correr tests localmente

```bash
# Backend
cd backend
pytest tests/unit/ -v                            # tests unitarios
pytest tests/integration/ -v                     # tests integración
pytest tests/ -v --cov=app --cov-report=term     # con coverage

# Frontend
cd frontend
npm run test                                     # modo watch (desarrollo)
npm run test:run                                 # una sola vez (CI)
npm run test:coverage                            # con coverage
npx playwright test                              # E2E
npx playwright test --ui                         # E2E con UI de Playwright
```

---

## 10. Documentación

### Cuándo actualizar la knowledge-base

La documentación en `knowledge-base/` debe mantenerse sincronizada con el código. Actualizar cuando:

- **Se cambia la arquitectura** (`knowledge-base/02-arquitectura/`): se agrega un servicio, se cambia la forma de comunicación entre dominios, se toma una decisión de diseño significativa.
- **Se agrega un endpoint nuevo** (`knowledge-base/02-arquitectura/03_api_y_endpoints.md`): documentar el endpoint, sus parámetros, y el schema de respuesta.
- **Se agrega un tipo de evento cognitivo** (`knowledge-base/01-negocio/04_reglas_de_negocio.md`): el mapeo canónico `event_type → N4 level`.
- **Se modifica el system prompt** (`knowledge-base/02-arquitectura/`): versión, fecha, justificación.
- **Se encuentra una trampa conocida** (`knowledge-base/05-dx/03_trampas_conocidas.md`): para que otros devs no caigan en el mismo problema.
- **Se toma una decisión arquitectónica** (`knowledge-base/02-arquitectura/07_adrs.md`): ADR (Architecture Decision Record) con contexto, decisión y consecuencias.

### Qué no documentar en la knowledge-base

- Código que es autoexplicativo.
- Detalles de implementación que cambian frecuentemente (los tests son mejor documentación).
- Información duplicada que ya está en el código fuente.

### Documentación de endpoints

Los endpoints están auto-documentados via FastAPI + Pydantic. Asegurarse de que cada endpoint tiene:
- `summary`: descripción corta.
- `description`: descripción larga si es complejo.
- `response_model`: siempre tipado.
- `tags`: para agrupar en Swagger UI.
- Validaciones documentadas en los schemas Pydantic (`description=`, `ge=`, `le=`, etc.).

### ADRs (Architecture Decision Records)

Para decisiones arquitectónicas no triviales, crear un ADR en `knowledge-base/02-arquitectura/07_adrs.md`:

```markdown
## ADR-XXX: Título de la decisión

**Fecha**: 2026-04-10
**Estado**: Aceptado

**Contexto**:
Descripción del problema y por qué se necesita tomar una decisión.

**Decisión**:
La decisión tomada y el razonamiento.

**Consecuencias**:
Qué implica esta decisión: ventajas, desventajas, deuda técnica.

**Alternativas consideradas**:
Qué otras opciones se evaluaron y por qué se descartaron.
```

---

## 11. Propiedad de Fases y Schemas

Esta es la regla más importante del proyecto después de la calidad del código.

### Regla de Propiedad (RN-8)

**Solo la fase dueña de un schema puede INSERT/UPDATE/DELETE en sus tablas. Las otras fases leen vía endpoints REST.**

| Schema PostgreSQL | Fase dueña | Fases que leen |
|-------------------|------------|----------------|
| `operational` | Fase 0 + Fase 1 | Fase 2, Fase 3 (vía REST), Fase 4 |
| `governance` | Fase 2 | Fase 3 (vía REST) |
| `cognitive` | Fase 3 | Fase 4 (vía REST) |
| `analytics` | Fase 3 | Fase 4 (vía REST) |

### Qué significa en la práctica

**Bien:**
```python
# Fase 3 leyendo datos de Fase 1 vía REST (correcto)
exercise = await http_client.get(f"/api/v1/exercises/{exercise_id}")
```

**Mal:**
```python
# Fase 3 importando y usando directamente el repo de Fase 1 (PROHIBIDO)
from app.shared.repositories.exercise_repo import ExerciseRepository  # ← NO
exercise = await ExerciseRepository(session).find_by_id(exercise_id)
```

**Bien:**
```python
# Fase 4 (frontend) leyendo datos de Fase 3 vía API (correcto)
const metrics = await fetchCognitiveMetrics(sessionId)
```

**Mal:**
```python
# Fase 4 haciendo INSERT directo (PROHIBIDO — no debería ser posible técnicamente)
await db.execute("INSERT INTO cognitive.cognitive_events ...")  # ← NO
```

### Por qué esta regla es fundamental

1. **Evita acoplamiento oculto**: un cambio en el schema de Fase 1 no debería romper a Fase 3.
2. **Permite evolución independiente**: cada fase puede refactorizar su schema sin coordinar con otras.
3. **Preparación para extracción**: si en el futuro se necesita extraer cognitive a un microservicio, la separación ya existe.
4. **Tesis-aligned**: el documento maestro empate3 establece esta separación de dominios.

### Cómo verificar en el PR

El reviewer debe verificar que:
- [ ] No hay imports entre repositorios de distintos dominios.
- [ ] No hay queries SQL cross-schema (`SELECT * FROM operational.x JOIN cognitive.y`).
- [ ] Los datos de otros dominios se obtienen vía llamadas HTTP internas.

Si el PR viola esta regla: **comentario bloqueante en la review**.

---

## Preguntas Frecuentes

**¿Puedo hacer commit directo a `main`?**
No. Todo cambio va por PR. Las Branch Protection Rules lo bloquean técnicamente.

**¿Puedo modificar el model de datos de otro dominio si "solo es un campo"?**
No sin coordinación. Abrir una issue y coordinar con el dueño de esa fase.

**¿Qué pasa si el CI falla en mi PR?**
No se puede mergear. Diagnosticar el fallo, corregirlo, y volver a pushear.

**¿Puedo saltear los tests adversariales del tutor?**
Para trabajo normal de desarrollo, sí (son caros y lentos). Pero son obligatorios antes de cualquier cambio en el system prompt o los guardrails.

**¿Cuándo documento en la knowledge-base vs en el código?**
El código es la fuente de verdad de cómo funciona. La knowledge-base documenta por qué se tomaron decisiones arquitectónicas y cómo están interconectadas. En caso de conflicto entre el código y la knowledge-base, el código gana — actualizar la knowledge-base.

**¿Puedo agregar una dependencia nueva?**
Para el backend: sí, agregando a `pyproject.toml` y actualizando `uv.lock`. Para el frontend: sí, con `npm install`. En ambos casos, mencionarlo en la descripción del PR para que el reviewer lo evalúe.

---

*Documento generado: 2026-04-10 | Plataforma AI-Native v1.0 | UTN FRM*
