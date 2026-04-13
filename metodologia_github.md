# Metodología GitHub — Plataforma AI-Native

**UTN FRM | Sistema Pedagógico para Enseñanza de Programación**
Última actualización: 2026-04-10
Versión: 1.0

---

## Índice

1. [Modelo de Branching](#1-modelo-de-branching-github-flow)
2. [Convenciones de Nombres de Branches](#2-convenciones-de-nombres-de-branches)
3. [Conventional Commits](#3-conventional-commits)
4. [Template de Pull Request](#4-template-de-pull-request)
5. [Proceso de Code Review](#5-proceso-de-code-review)
6. [Estrategia de Merge](#6-estrategia-de-merge)
7. [GitHub Issues: Labels y Organización](#7-github-issues-labels-y-organización)
8. [Branch Protection Rules](#8-branch-protection-rules)
9. [Versionado y Release Tagging](#9-versionado-y-release-tagging)
10. [Cheatsheet Rápido](#10-cheatsheet-rápido)

---

## 1. Modelo de Branching: GitHub Flow

El proyecto usa **GitHub Flow**, el modelo más simple y adecuado para un equipo de 4 personas con entregas frecuentes.

### Reglas Fundamentales

- `main` es la rama de producción/staging. **Siempre debe estar en estado deployable.**
- **No existe** rama `develop`, `staging`, `release`, ni `hotfix`. Solo `main` y feature branches.
- Todo el trabajo se hace en branches que parten desde `main`.
- Cuando una feature está lista: PR hacia `main`, requiere 1 review + CI verde → merge.
- Las branches **se borran inmediatamente después del merge** (GitHub lo hace automáticamente con la configuración correcta).

### Flujo Visual

```
main ─────────────────────────────────────────────────────────> producción
  │
  ├── feat/e0-monorepo-setup ─────────────────────────────── PR ──> merge
  │
  ├── feat/e1-exercise-crud ──────────────────────────────── PR ──> merge
  │
  ├── feat/e2-tutor-websocket ──────────────────────── PR ──────── merge
  │
  └── fix/42-hash-chain-genesis ────────────────────── PR ──────── merge
```

### Por Qué GitHub Flow (No GitFlow)

- **Equipo pequeño**: GitFlow tiene overhead de gestión de ramas que no se justifica con 4 devs.
- **Entregas frecuentes**: GitHub Flow permite mergear a `main` en cualquier momento sin coordinar releases.
- **Semanas de desarrollo paralelo**: Las 4 fases trabajan independientemente con mínima coordinación entre branches.
- **CI/CD simple**: Un solo target de merge simplifica el pipeline de GitHub Actions.

---

## 2. Convenciones de Nombres de Branches

### Formato

```
{tipo}/{descripcion-en-kebab-case}
```

El `tipo` sigue los mismos valores que los Conventional Commits para consistencia.

### Tipos y Ejemplos

| Tipo | Cuándo usarlo | Ejemplo |
|------|---------------|---------|
| `feat` | Nueva funcionalidad | `feat/e1-sandbox-execution` |
| `fix` | Corrección de bug | `fix/42-rate-limit-not-applied` |
| `refactor` | Refactoring sin cambio de comportamiento | `refactor/tutor-service-extract-guardrails` |
| `test` | Solo agregar tests | `test/adversarial-tutor-prompts` |
| `chore` | Dependencias, configs, CI | `chore/update-anthropic-sdk-0-40` |
| `docs` | Solo documentación | `docs/onboarding-wsl2-setup` |
| `perf` | Mejora de performance | `perf/cognitive-events-batch-insert` |
| `ci` | Cambios en el pipeline CI | `ci/add-adversarial-tests-weekly-job` |

### Convenciones Adicionales

- **Siempre kebab-case**: `feat/exercise-difficulty-filter`, NO `feat/exerciseDifficultyFilter`.
- **Prefijo con ID de issue cuando existe**: `feat/42-exercise-crud` (ayuda a rastrear la issue).
- **Prefijo con ID de EPIC para features grandes**: `feat/e2-tutor-websocket` (E2 = EPIC 2).
- **Descripción concisa**: máximo 5 palabras. Si necesitás más, el nombre es demasiado amplio → dividir en issues más pequeñas.
- **Sin tildes ni caracteres especiales** en el nombre de la branch.

### Ejemplos Completos por EPIC

```
# EPIC 0 — Fundación
feat/e0-monorepo-setup
feat/e0-docker-compose
feat/e0-postgres-schemas
feat/e0-jwt-auth-rbac
feat/e0-openapi-typescript-gen
feat/e0-github-actions-ci
feat/e0-seed-data

# EPIC 1 — Core Académico
feat/e1-course-commission-crud
feat/e1-exercise-crud
feat/e1-submission-flow
feat/e1-sandbox-execution
feat/e1-code-snapshots

# EPIC 2 — Tutor IA
feat/e2-tutor-websocket
feat/e2-system-prompt-versioning
feat/e2-context-builder
feat/e2-guardrails-anti-solver
feat/e2-n4-classification
feat/e2-reflection-form
feat/e2-governance-events

# EPIC 3 — Motor Cognitivo
feat/e3-cognitive-event-classifier
feat/e3-ctr-hash-chain
feat/e3-cognitive-worker-metrics
feat/e3-risk-worker
feat/e3-evaluation-engine

# EPIC 4 — Frontend
feat/e4-student-dashboard
feat/e4-exercise-view-monaco
feat/e4-tutor-chat-component
feat/e4-reflection-panel
feat/e4-teacher-dashboard
feat/e4-n4-radar-chart
feat/e4-cognitive-trace-view
feat/e4-msw-mocks
```

---

## 3. Conventional Commits

El proyecto usa **Conventional Commits** de forma estricta. Un pre-commit hook con `commitlint` rechaza commits que no cumplan el formato.

### Formato

```
<tipo>(<alcance>): <descripción en infinitivo, minúsculas>

[cuerpo opcional: qué y por qué, no cómo — separado por línea en blanco]

[footer opcional]
[Refs: #issue-number]
[BREAKING CHANGE: descripción del cambio que rompe compatibilidad]
```

### Tipos Válidos

| Tipo | Cuándo | Impacta versión (semver) |
|------|--------|--------------------------|
| `feat` | Nueva funcionalidad visible para el usuario | Minor (X.Y.0) |
| `fix` | Corrección de bug | Patch (X.Y.Z) |
| `refactor` | Refactoring sin cambio de comportamiento | No |
| `test` | Agregar o modificar tests | No |
| `docs` | Solo documentación | No |
| `chore` | Dependencias, configuración, CI | No |
| `perf` | Mejora de performance | Patch |
| `ci` | Cambios en GitHub Actions | No |
| `build` | Cambios en el sistema de build (Vite, pyproject) | No |
| `revert` | Revertir un commit anterior | Depende |

### Alcances (Scopes) Válidos

Los scopes ayudan a identificar qué módulo fue modificado:

```
# Backend
auth          → features/auth/
courses       → features/courses/
exercises     → features/exercises/
sandbox       → features/sandbox/
tutor         → features/tutor/
cognitive     → features/cognitive/
evaluation    → features/evaluation/
governance    → features/governance/
hash-chain    → shared/hash_chain.py
db            → shared/db/ o alembic/
api           → múltiples endpoints o router principal

# Frontend
dashboard     → features/student/ o features/teacher/
editor        → Monaco Editor o features/exercises/
chat          → features/exercise/
store         → cualquier store de Zustand
msw           → mocks/

# Transversales
infra         → infra/ o docker-compose
ci            → .github/workflows/
deps          → pyproject.toml o package.json
```

### Reglas

1. **Infinitivo, no pasado**: `add difficulty filter`, NO `added difficulty filter`.
2. **Minúsculas**: `feat(auth): add jwt refresh rotation`, NO `Feat(Auth): Add JWT Refresh`.
3. **Sin punto al final** de la descripción corta.
4. **Descripción en inglés** para facilitar búsqueda y consistencia técnica.
5. **Máximo 72 caracteres** en la primera línea.
6. **Cuerpo en español** si el contexto lo amerita para mayor claridad.

### Ejemplos Correctos

```
feat(tutor): add websocket streaming endpoint

Implementa el canal bidireccional alumno-tutor con streaming de respuestas
del LLM token por token. Incluye heartbeat y manejo de reconexión.

Refs: #16

---

feat(hash-chain): implement SHA-256 chain for CTR immutability

fix(auth): prevent refresh token reuse after logout

Agrega el token blacklist en Redis para que tokens ya usados en el
endpoint /refresh no puedan reutilizarse. Previene replay attacks.

Refs: #4

---

refactor(tutor): extract guardrails into separate module

test(hash-chain): add adversarial tests for chain integrity

Agrega 5 tests que verifican que la cadena se rompe si se tamper con
eventos intermedios o se reordena la secuencia.

---

chore(deps): update anthropic SDK to v0.40.0

Refs: CVE-2024-XXXX (no aplica, actualización preventiva)

---

ci: add weekly adversarial tutor tests job

BREAKING CHANGE: el endpoint /api/v1/auth/refresh ahora requiere
el refresh_token en el body (no en cookie). Ver #migration-guide.
```

### Ejemplos Incorrectos

```
Fixed bug                    # Sin tipo, sin scope, pasado
feat: stuff                  # Descripción no informativa
FEAT(AUTH): Add login        # Tipo en mayúsculas
feat(auth): Added login.     # Pasado y con punto
feat: add a very very long description that goes beyond 72 characters limit which is wrong
```

### Configuración de commitlint

El archivo `.commitlintrc.json` en la raíz del repo:

```json
{
  "extends": ["@commitlint/config-conventional"],
  "rules": {
    "scope-enum": [2, "always", [
      "auth", "courses", "exercises", "sandbox", "tutor",
      "cognitive", "evaluation", "governance", "hash-chain",
      "db", "api", "dashboard", "editor", "chat", "store",
      "msw", "infra", "ci", "deps"
    ]],
    "subject-case": [2, "always", "lower-case"],
    "header-max-length": [2, "always", 72]
  }
}
```

---

## 4. Template de Pull Request

El archivo `.github/pull_request_template.md` define el template que aparece automáticamente al abrir un PR:

```markdown
## Descripción

<!-- Qué hace este PR en 2-3 oraciones. Referencia la HU o issue. -->

## Cambios principales

<!-- Lista de cambios más importantes. Sé específico. -->

- [ ] 
- [ ] 
- [ ] 

## Tipo de cambio

- [ ] Nueva funcionalidad (`feat`)
- [ ] Corrección de bug (`fix`)
- [ ] Refactoring sin cambio de comportamiento (`refactor`)
- [ ] Tests únicamente (`test`)
- [ ] Documentación (`docs`)
- [ ] Configuración / CI / deps (`chore`)

## EPIC relacionado

- [ ] EPIC 0 — Fundación
- [ ] EPIC 1 — Core Académico
- [ ] EPIC 2 — Tutor IA
- [ ] EPIC 3 — Motor Cognitivo
- [ ] EPIC 4 — Frontend

## Cómo testear

<!-- Pasos específicos para verificar que el PR funciona. -->

1. 
2. 
3. 

## Screenshots (si aplica)

<!-- Para cambios visuales en el frontend, incluir antes/después. -->

## Checklist

- [ ] Los tests pasan localmente (`pytest tests/` o `npm run test:run`)
- [ ] El linter no reporta errores (`ruff check . && mypy app/` o `npm run lint`)
- [ ] El código sigue las convenciones del proyecto (ver `knowledge-base/05-dx/04_convenciones_y_estandares.md`)
- [ ] La documentación fue actualizada si aplica (endpoints en OpenAPI, knowledge-base si cambió arquitectura)
- [ ] No hay cambios en schemas de otros dominios sin coordinación (ver RN-8)

## Issues relacionados

Closes #<!-- número -->
Refs #<!-- número -->
```

### Título del PR

El título debe seguir exactamente el formato de Conventional Commits (es el commit de squash en `main`):

```
feat(tutor): add websocket streaming with guardrails (#23)
fix(hash-chain): fix genesis hash constant (#31)
refactor(cognitive): extract event classifier to separate service (#45)
```

---

## 5. Proceso de Code Review

### Reglas

- **Mínimo 1 aprobación** de otro miembro del equipo antes de mergear.
- **CI debe pasar** (todos los jobs excepto los adversariales que son semanales).
- **Nadie aprueba su propio PR**. Si sos el único disponible por urgencia, documentalo en el PR.
- El autor puede mergear después de la aprobación (no necesita esperar al reviewer).

### Responsabilidades del Reviewer

El reviewer verifica:

**Corrección**
- [ ] La implementación cumple los criterios de aceptación de la issue/HU.
- [ ] Los edge cases están cubiertos (inputs inválidos, errores de DB, etc.).
- [ ] No hay casos obvios de error que el PR no maneje.

**Calidad de código**
- [ ] La implementación sigue las convenciones del proyecto (ver `04_convenciones_y_estandares.md`).
- [ ] No hay anti-patterns conocidos (N+1 queries, imports circulares, lógica en el router, etc.).
- [ ] Las funciones son razonablemente cortas y tienen nombres descriptivos.
- [ ] Los type hints están completos en el código Python.

**Tests**
- [ ] Hay tests para el happy path y al menos 1-2 edge cases relevantes.
- [ ] Los tests no son frágiles (no testean implementación interna sino comportamiento).
- [ ] El coverage no bajó respecto a `main`.

**Arquitectura y dominio**
- [ ] El PR no viola RN-8 (escritura en schemas de otros dominios).
- [ ] Las capas de arquitectura están respetadas (no hay lógica de negocio en el router, no hay SQL en el service, etc.).
- [ ] Si hay cambios en la API pública, están documentados en la OpenAPI spec.

**Seguridad**
- [ ] No hay secrets hardcodeados.
- [ ] Los endpoints nuevos tienen los checks de autenticación/autorización correctos.
- [ ] Los inputs del usuario están validados antes de usarse en queries SQL.

### Proceso de Feedback

- Los comentarios de review deben ser **específicos y accionables**.
- Distinguir entre: **bloqueante** (must fix antes de mergear), **sugerencia** (nice to have, puede quedar como issue), **pregunta** (solo curiosidad, no requiere cambio).
- El autor **responde cada comentario** antes de solicitar re-review.
- Si un comentario abre un debate de más de 3 mensajes, resolver en la issue o en un call, no en la review.

### Tiempo Esperado de Review

- PRs pequeños (< 200 líneas): review en el mismo día.
- PRs medianos (200-500 líneas): review en 1 día hábil.
- PRs grandes (> 500 líneas): dividir el PR. Si no es posible, coordinar review.

**No dejar PRs abiertos por más de 2 días sin feedback.** Si el reviewer está bloqueado, pedir a otro miembro del equipo.

---

## 6. Estrategia de Merge

### Squash and Merge — Siempre

Todos los merges a `main` usan **Squash and Merge**. Esto:

- Mantiene el historial de `main` limpio: 1 commit por feature.
- El commit de squash tiene el título del PR (que sigue Conventional Commits).
- Los commits intermedios de desarrollo quedan en el historial de la branch (que se borra post-merge).

### Configuración en GitHub

En `Settings → General → Pull Requests`:
- ✅ `Allow squash merging`
- ❌ `Allow merge commits` (desactivado)
- ❌ `Allow rebase merging` (desactivado)
- ✅ `Automatically delete head branches`

### Antes de Hacer Merge

```bash
# El autor rebasa su branch sobre main actualizado
git fetch origin
git rebase origin/main

# Correr tests localmente una vez más para estar seguro
cd backend && pytest tests/ -v
cd frontend && npm run test:run

# Correr linters
cd backend && ruff check . && mypy app/
cd frontend && npm run lint

# Pushear (con force si fue necesario el rebase)
git push origin feat/mi-feature --force-with-lease
```

### Resolución de Conflictos

Si hay conflictos durante el rebase:

```bash
# Al hacer rebase y encontrar conflictos
git rebase origin/main

# Para cada conflicto: editar el archivo, marcar como resuelto
git add archivo_con_conflicto.py
git rebase --continue

# Si el conflicto es muy complejo, abortar y coordinar con el equipo
git rebase --abort
```

**Regla**: Si un conflicto involucra código de otro dominio (ej: cambios en modelos del schema `cognitive` vs cambios en el schema `operational`), coordinar con el dev de esa fase antes de resolver.

---

## 7. GitHub Issues: Labels y Organización

### Sistema de Labels

Los issues usan un sistema de labels en 3 dimensiones: fase, tipo y prioridad.

#### Por Fase (color azul, tono diferente por fase)

| Label | Color | Descripción |
|-------|-------|-------------|
| `fase-0` | `#0052CC` | EPIC 0 — Fundación |
| `fase-1` | `#006644` | EPIC 1 — Core Académico |
| `fase-2` | `#403294` | EPIC 2 — Tutor IA |
| `fase-3` | `#0B5394` | EPIC 3 — Motor Cognitivo |
| `fase-4` | `#4A86C8` | EPIC 4 — Frontend |

#### Por Tipo (color variable)

| Label | Color | Descripción |
|-------|-------|-------------|
| `feature` | `#0075CA` | Nueva funcionalidad |
| `bug` | `#D73A4A` | Algo no funciona como debería |
| `chore` | `#E4E669` | Mantenimiento, deps, config |
| `docs` | `#0075CA` | Solo documentación |
| `test` | `#008672` | Tests adicionales |
| `refactor` | `#5319E7` | Refactoring sin cambio de comportamiento |
| `question` | `#D876E3` | Pregunta o investigación |
| `blocked` | `#B60205` | Bloqueado por dependencia externa |

#### Por Prioridad (rojo para P0/P1, amarillo para P2, verde para P3)

| Label | Color | Descripción |
|-------|-------|-------------|
| `P0 - bloqueante` | `#B60205` | Sin esto el sistema no funciona. Prioridad máxima. |
| `P1 - crítico` | `#E05D44` | Necesario para el sprint. |
| `P2 - importante` | `#F9D0C4` | Puede ir al sprint siguiente si hay tiempo. |
| `P3 - deseable` | `#C2E0C6` | Backlog. |

### Creación de Issues

Cada issue debe tener:

1. **Título**: descriptivo y en imperativo. Ej: "Implementar clasificador de eventos cognitivos N4".
2. **Labels**: al menos 1 de fase + 1 de tipo + 1 de prioridad.
3. **Asignee**: el dev responsable.
4. **Milestone**: el sprint o semana objetivo (ej: "Semana 3-4").
5. **Descripción** con:
   - Qué se necesita hacer
   - Criterios de aceptación claros (checkboxes)
   - Referencias a HUs del backlog (`Refs: HU-024`)
   - Scope claro: qué archivos/módulos están involucrados

### Template de Issue para Feature

El archivo `.github/ISSUE_TEMPLATE/feature.md`:

```markdown
---
name: Feature / Historia de Usuario
about: Nueva funcionalidad para implementar
labels: feature
---

## Historia de Usuario de Referencia

HU-XXX: [nombre]

## Descripción

<!-- Qué se necesita implementar y por qué -->

## Criterios de Aceptación

- [ ] 
- [ ] 
- [ ] 

## Scope técnico

**Backend:**
- Archivos: 
- Endpoints nuevos/modificados:

**Frontend:**
- Archivos:
- Componentes:

**Base de datos:**
- Migraciones necesarias: Sí / No

## Dependencias

<!-- Issues que deben estar completadas antes de empezar esta -->
Depende de: #

## Notas adicionales

<!-- Consideraciones técnicas, restricciones, referencias -->
```

### Template de Issue para Bug

El archivo `.github/ISSUE_TEMPLATE/bug.md`:

```markdown
---
name: Bug Report
about: Algo no funciona como debería
labels: bug
---

## Descripción del Bug

<!-- Descripción clara y concisa del error -->

## Pasos para Reproducirlo

1. 
2. 
3. 

## Comportamiento Esperado

<!-- Qué debería pasar -->

## Comportamiento Actual

<!-- Qué pasa en realidad -->

## Logs / Screenshots

```
# Pegar logs relevantes aquí
```

## Contexto

- OS / Plataforma: 
- Branch:
- Commit:

## Prioridad sugerida

- [ ] P0 — Sistema no funciona / datos en riesgo
- [ ] P1 — Feature principal bloqueada
- [ ] P2 — Feature degradada, hay workaround
- [ ] P3 — Cosmético o edge case raro
```

### Uso de Milestones

| Milestone | Issues |
|-----------|--------|
| `Semanas 1-2: Fundación` | Todas las issues de EPIC 0 |
| `Semanas 3-6: Sprint 1` | Issues P1 de EPIC 1-4 iniciales |
| `Semanas 7-10: Sprint 2` | Issues P1 restantes + P2 prioridad |
| `Semanas 11-12: Sprint 3` | Issues P2 + P3 si tiempo |
| `Semanas 13-14: Integración` | Issues de integración E2E |
| `Backlog` | Issues P3 y futuras |

---

## 8. Branch Protection Rules

Configurar en `Settings → Branches → Add rule → Branch name pattern: main`:

### Reglas Obligatorias

```
✅ Require a pull request before merging
  ✅ Require approvals: 1
  ✅ Dismiss stale pull request approvals when new commits are pushed
  ✅ Require review from Code Owners (si se configura CODEOWNERS)

✅ Require status checks to pass before merging
  ✅ Require branches to be up to date before merging
  Status checks requeridos:
    - lint-backend
    - lint-frontend
    - test-unit
    - test-integration
    - test-frontend
    - build-check

✅ Require conversation resolution before merging

✅ Do not allow bypassing the above settings
  (ni siquiera los admins pueden saltear las reglas — evita mergeos de emergencia sucios)
```

### Reglas Opcionales Recomendadas

```
✅ Require linear history (evita merge commits — refuerza squash)
✅ Lock branch (solo si queremos congelar main temporalmente durante integración)
```

### CODEOWNERS (opcional pero útil)

El archivo `.github/CODEOWNERS` asigna reviewers automáticos por área:

```
# Cada dev es codeowner de su fase
/backend/app/features/courses/     @dev-fase-1
/backend/app/features/exercises/   @dev-fase-1
/backend/app/features/sandbox/     @dev-fase-1

/backend/app/features/tutor/       @dev-fase-2
/backend/app/features/governance/  @dev-fase-3

/backend/app/features/cognitive/   @dev-fase-3
/backend/app/features/evaluation/  @dev-fase-3

/frontend/                         @dev-fase-4

# Shared: cualquier change requiere 2 reviews
/backend/app/shared/               @dev-fase-1 @dev-fase-3
/shared/                           @dev-fase-1 @dev-fase-4
```

---

## 9. Versionado y Release Tagging

El proyecto usa **Semantic Versioning (SemVer)** para los tags de release:

```
v{MAJOR}.{MINOR}.{PATCH}

MAJOR: cambio que rompe compatibilidad (raro en este proyecto)
MINOR: nueva funcionalidad (feat) completada
PATCH: bug fix o pequeña mejora
```

### Cuándo Crear un Tag

Los tags se crean al completar **milestones de integración**, no en cada merge:

| Momento | Tag | Descripción |
|---------|-----|-------------|
| Al completar EPIC 0 | `v0.1.0` | Fundación funcional |
| Al completar Sprint 1 (semanas 3-6) | `v0.2.0` | Core académico inicial |
| Al completar Sprint 2 (semanas 7-10) | `v0.3.0` | Tutor + Motor básico |
| Al completar integración (semana 13-14) | `v0.9.0` | Release candidate |
| QA final aprobado (semana 15-16) | `v1.0.0` | Release de tesis |

### Crear un Tag

```bash
# Asegurarse de estar en main actualizado
git checkout main
git pull origin main

# Crear el tag con anotación
git tag -a v0.2.0 -m "EPIC 1 completado: Core Académico + Sandbox

- CRUD cursos, comisiones, ejercicios, enrollments
- Submission flow completo
- Sandbox Python con timeout y memory limit
- Code snapshots automáticos
- Test cases con reporte granular

Issues cerradas: #8, #9, #10, #11, #12, #13, #14, #15"

# Pushear el tag
git push origin v0.2.0
```

### GitHub Releases

Para cada tag importante (`v0.X.0`), crear un GitHub Release:

1. Ir a `Releases → Create a new release`.
2. Seleccionar el tag.
3. Título: `v0.2.0 — Core Académico + Sandbox`.
4. Descripción: changelog con las features completadas, issues cerradas, breaking changes si las hay.
5. Si es pre-release (antes de `v1.0.0`), marcar como "Pre-release".

---

## 10. Cheatsheet Rápido

### Empezar una feature

```bash
git checkout main
git pull origin main
git checkout -b feat/e2-tutor-websocket
# ... trabajar ...
git add backend/app/features/tutor/
git commit -m "feat(tutor): add websocket streaming endpoint"
git push origin feat/e2-tutor-websocket
# Abrir PR en GitHub
```

### Durante el desarrollo (commits frecuentes)

```bash
git add <archivos específicos>
git commit -m "feat(tutor): add heartbeat mechanism to ws connection"

git add <archivos de tests>
git commit -m "test(tutor): add integration test for ws connection lifecycle"
```

### Actualizar branch con cambios de main

```bash
git fetch origin
git rebase origin/main
# resolver conflictos si los hay
git push origin feat/e2-tutor-websocket --force-with-lease
```

### Antes de abrir el PR

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
npm run build  # verificar que buildea sin errores TS
```

### Labels de una issue desde CLI

```bash
gh issue create \
  --title "Implementar clasificador de eventos cognitivos N4" \
  --label "fase-3,feature,P1 - crítico" \
  --assignee "@me" \
  --milestone "Semanas 3-6: Sprint 1" \
  --body "$(cat issue_body.md)"
```

### Crear un PR desde CLI

```bash
gh pr create \
  --title "feat(cognitive): add event classifier with N4 mapping" \
  --body "$(cat pr_body.md)" \
  --base main \
  --draft  # si todavía está en progreso
```

---

*Documento generado: 2026-04-10 | Plataforma AI-Native v1.0 | UTN FRM*
