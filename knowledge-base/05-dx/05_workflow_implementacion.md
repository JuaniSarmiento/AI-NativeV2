# Workflow de Implementación — Cómo Agregar una Nueva Feature

**Plataforma AI-Native | UTN FRM**
Última actualización: 2026-04-10

---

Este documento describe el proceso completo para implementar una nueva funcionalidad en la plataforma, desde la issue de GitHub hasta el merge a `main`. Seguir este proceso garantiza código revisable, testeable, y consistente con el resto del sistema.

---

## Indice

1. [Resumen del Proceso](#1-resumen-del-proceso)
2. [Paso 1 — Crear la GitHub Issue](#2-paso-1--crear-la-github-issue)
3. [Paso 2 — Crear la Feature Branch](#3-paso-2--crear-la-feature-branch)
4. [Paso 3 — Definir Artefactos si es Complejo](#4-paso-3--definir-artefactos-si-es-complejo)
5. [Paso 4 — Implementar el Backend](#5-paso-4--implementar-el-backend)
6. [Paso 5 — Implementar el Frontend](#6-paso-5--implementar-el-frontend)
7. [Paso 6 — Tests](#7-paso-6--tests)
8. [Paso 7 — Pull Request](#8-paso-7--pull-request)
9. [Paso 8 — Code Review y Merge](#9-paso-8--code-review-y-merge)
10. [Ejemplo Completo — Filtro de Dificultad en Ejercicios](#10-ejemplo-completo--filtro-de-dificultad-en-ejercicios)

---

## 1. Resumen del Proceso

```
Issue GitHub
    ↓
Feature branch desde main
    ↓
(Si complejo) → /opsx:propose → artefactos de diseño
    ↓
Backend: model → migration → repository → service → router → tests
    ↓
Frontend: types → api.ts → store → components → integration tests
    ↓
Tests: unit + integration + adversarial (si es tutor-related)
    ↓
PR con conventional commit title
    ↓
CI verde → 1 review aprobado → merge a main
    ↓
Branch borrada
```

---

## 2. Paso 1 — Crear la GitHub Issue

Antes de tocar código, debe existir una issue de GitHub que justifique el trabajo.

### Template de issue para nueva feature

```markdown
## Descripción
Agregar filtro por dificultad (1-4) al endpoint GET /api/v1/courses/{course_id}/exercises y al componente ExerciseList del frontend.

## Motivación
Los alumnos de los primeros años solo deben ver ejercicios de dificultad 1-2. Actualmente ven todos los ejercicios y se desorientan.

## Criterios de Aceptación
- [ ] El endpoint acepta `?difficulty=N` (1-4)
- [ ] Si `difficulty` no se provee, retorna todos los ejercicios activos
- [ ] El frontend muestra un selector de dificultad
- [ ] Al cambiar la dificultad, la lista se actualiza sin recargar la página
- [ ] Tests unitarios y de integración para el nuevo parámetro

## Scope
- Backend: `exercise_router.py`, `exercise_service.py`, `exercise_repository.py`
- Frontend: `ExerciseList.tsx`, `exerciseStore.ts`, `exerciseApi.ts`

## No incluye
- Filtro por múltiples dificultades a la vez (será una issue separada)
- Cambio en la lógica de asignación de dificultad

Refs: #issue_padre_si_aplica
```

Asignar la issue al sprint actual y al desarrollador responsable antes de empezar.

---

## 3. Paso 2 — Crear la Feature Branch

```bash
# Asegurarse de estar en main actualizado
git checkout main
git pull origin main

# Crear la branch
git checkout -b feat/exercise-difficulty-filter

# Verificar que estamos en la branch correcta
git branch
# * feat/exercise-difficulty-filter
#   main
```

Convenciones de nombres de branches:

```
feat/{descripcion-en-kebab}          # nueva funcionalidad
fix/{descripcion-en-kebab}           # corrección de bug
refactor/{descripcion-en-kebab}      # refactoring
test/{descripcion-en-kebab}          # solo tests
chore/{descripcion-en-kebab}         # mantenimiento
docs/{descripcion-en-kebab}          # documentación
```

---

## 4. Paso 3 — Definir Artefactos si es Complejo

Para features que involucran cambios en múltiples capas, diseño de APIs, o decisiones arquitectónicas no triviales, crear artefactos de diseño antes de codear.

**Regla de dedo**: si la feature toca 4+ archivos o requiere una decisión de diseño que afecta a otros devs → crear artefactos.

```bash
# Crear change con todos los artefactos (proposal, design, tasks, specs)
/opsx:propose "exercise-difficulty-filter"
```

Los artefactos en `openspec/changes/exercise-difficulty-filter/` deben responder:
- `proposal.md`: qué y por qué
- `design.md`: cómo (schemas de request/response, contratos de API, decisiones de diseño)
- `tasks.md`: lista de tareas ordenada con dependencias
- `specs/`: specs de cada componente si aplica

Para features pequeñas (1-3 archivos, cambio trivial), omitir este paso y ir directo a la implementación.

---

## 5. Paso 4 — Implementar el Backend

El orden importa. Cada capa depende de la anterior.

### 4.1 — Modelo SQLAlchemy (si hay cambio en schema)

```python
# backend/app/models/exercise_model.py
class Exercise(Base):
    __tablename__ = "exercises"
    __table_args__ = {"schema": "operational"}
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, ...)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)  # nuevo o ya existe
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # ...
```

Si se agrega/modifica una columna, continuar con el paso de migración.

### 4.2 — Migración Alembic (si hay cambio en schema)

```bash
cd backend
source .venv/bin/activate

# Generar migración automática
alembic revision --autogenerate -m "add_difficulty_to_exercises"

# OBLIGATORIO: revisar el archivo generado antes de aplicar
# Verificar que el schema es correcto y no hay operaciones no deseadas
code alembic/versions/xxxx_add_difficulty_to_exercises.py

# Aplicar
alembic upgrade head

# Verificar
alembic current
```

Para el ejemplo de filtro de dificultad: si la columna `difficulty` ya existe en el modelo, no se genera migración. Solo si es una columna nueva.

### 4.3 — Repository

```python
# backend/app/repositories/exercise_repository.py
class ExerciseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def find_all_active(
        self,
        page: int = 1,
        per_page: int = 20,
        difficulty: int | None = None,  # nuevo parámetro
    ) -> tuple[list[Exercise], int]:
        query = select(Exercise).where(Exercise.is_active.is_(True))
        
        # Agregar filtro de dificultad si se especifica
        if difficulty is not None:
            query = query.where(Exercise.difficulty == difficulty)
        
        # Contar total (sin paginación)
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query)
        
        # Paginación
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.session.execute(query)
        return result.scalars().all(), total or 0
```

### 4.4 — Service

```python
# backend/app/features/exercises/service.py
class ExerciseService:
    def __init__(self, repository: ExerciseRepository):
        self.repository = repository
    
    async def list_exercises(
        self,
        page: int,
        per_page: int,
        difficulty: int | None = None,
    ) -> PaginatedExercisesResponse:
        # Validar dificultad
        if difficulty is not None and difficulty not in range(1, 5):
            raise InvalidDifficultyError(f"Difficulty must be between 1 and 4, got {difficulty}")
        
        exercises, total = await self.repository.find_all_active(
            page=page,
            per_page=per_page,
            difficulty=difficulty,
        )
        
        return PaginatedExercisesResponse(
            items=[ExerciseResponse.model_validate(e) for e in exercises],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=math.ceil(total / per_page),
        )
```

### 4.5 — Router

```python
# backend/app/routers/exercise_router.py
@router.get(
    "/",
    response_model=SuccessResponse[PaginatedExercisesResponse],
    summary="Listar ejercicios activos",
)
async def list_exercises(
    page: int = Query(default=1, ge=1, description="Número de página"),
    per_page: int = Query(default=20, ge=1, le=100, description="Elementos por página"),
    difficulty: int | None = Query(default=None, ge=1, le=4, description="Filtrar por nivel de dificultad (1-4)"),
    service: ExerciseService = Depends(get_exercise_service),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[PaginatedExercisesResponse]:
    result = await service.list_exercises(page=page, per_page=per_page, difficulty=difficulty)
    return SuccessResponse(data=result)
```

---

## 6. Paso 5 — Implementar el Frontend

### 5.1 — Types TypeScript

```typescript
// frontend/src/features/exercises/types.ts
export interface Exercise {
  id: string
  title: string
  description: string
  difficulty: 1 | 2 | 3 | 4
  isActive: boolean
  createdAt: string
}

export interface ExerciseFilters {
  difficulty?: 1 | 2 | 3 | 4
  page?: number
  perPage?: number
}

export interface PaginatedExercisesResponse {
  items: Exercise[]
  total: number
  page: number
  perPage: number
  totalPages: number
}
```

### 5.2 — API Client

```typescript
// frontend/src/features/exercises/api/exerciseApi.ts
import type { ExerciseFilters, PaginatedExercisesResponse } from '../types'
import { apiClient } from '@/shared/api/client'

export async function fetchExercises(
  filters: ExerciseFilters = {}
): Promise<PaginatedExercisesResponse> {
  const params = new URLSearchParams()
  if (filters.page) params.set('page', String(filters.page))
  if (filters.perPage) params.set('per_page', String(filters.perPage))
  if (filters.difficulty) params.set('difficulty', String(filters.difficulty))
  
  const response = await apiClient.get(`/exercises?${params}`)
  return response.data.data
}
```

### 5.3 — Zustand Store

```typescript
// frontend/src/features/exercises/stores/exerciseStore.ts
import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { Exercise, ExerciseFilters } from '../types'

interface ExerciseStore {
  exercises: Exercise[]
  filters: ExerciseFilters
  isLoading: boolean
  error: string | null
  
  // Acciones
  setExercises: (exercises: Exercise[]) => void
  setFilters: (filters: Partial<ExerciseFilters>) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  resetFilters: () => void
}

const DEFAULT_FILTERS: ExerciseFilters = {
  page: 1,
  perPage: 20,
}

export const useExerciseStore = create<ExerciseStore>()(
  devtools(
    (set) => ({
      exercises: [],
      filters: DEFAULT_FILTERS,
      isLoading: false,
      error: null,
      
      setExercises: (exercises) => set({ exercises }),
      setFilters: (newFilters) =>
        set((state) => ({ filters: { ...state.filters, ...newFilters, page: 1 } })),
      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
      resetFilters: () => set({ filters: DEFAULT_FILTERS }),
    }),
    { name: 'ExerciseStore' }
  )
)
```

### 5.4 — Custom Hook

```typescript
// frontend/src/features/exercises/hooks/useExercises.ts
import { useEffect } from 'react'
import { useShallow } from 'zustand/react/shallow'
import { fetchExercises } from '../api/exerciseApi'
import { useExerciseStore } from '../stores/exerciseStore'

export function useExercises() {
  const { filters, setExercises, setLoading, setError } = useExerciseStore(
    useShallow((state) => ({
      filters: state.filters,
      setExercises: state.setExercises,
      setLoading: state.setLoading,
      setError: state.setError,
    }))
  )
  
  useEffect(() => {
    let cancelled = false
    
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await fetchExercises(filters)
        if (!cancelled) setExercises(data.items)
      } catch (err) {
        if (!cancelled) setError('Error al cargar ejercicios')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    
    load()
    return () => { cancelled = true }
  }, [filters])  // re-fetch cuando cambian los filtros
}
```

### 5.5 — Componentes

```typescript
// frontend/src/features/exercises/components/DifficultyFilter.tsx
import { useShallow } from 'zustand/react/shallow'
import { useExerciseStore } from '../stores/exerciseStore'

const DIFFICULTIES = [
  { value: undefined, label: 'Todos' },
  { value: 1, label: 'Nivel 1 - Básico' },
  { value: 2, label: 'Nivel 2 - Intermedio' },
  { value: 3, label: 'Nivel 3 - Avanzado' },
  { value: 4, label: 'Nivel 4 - Experto' },
] as const

export function DifficultyFilter() {
  const { difficulty, setFilters } = useExerciseStore(
    useShallow((state) => ({
      difficulty: state.filters.difficulty,
      setFilters: state.setFilters,
    }))
  )
  
  return (
    <select
      value={difficulty ?? ''}
      onChange={(e) =>
        setFilters({ difficulty: e.target.value ? Number(e.target.value) as 1|2|3|4 : undefined })
      }
      className="border rounded px-3 py-2 text-sm"
      aria-label="Filtrar por dificultad"
    >
      {DIFFICULTIES.map((d) => (
        <option key={d.label} value={d.value ?? ''}>
          {d.label}
        </option>
      ))}
    </select>
  )
}
```

---

## 7. Paso 6 — Tests

### Tests de backend

```python
# backend/tests/unit/test_exercise_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.exercise_service import ExerciseService
from app.schemas.exercise_schemas import ExerciseResponse

@pytest.mark.unit
async def test_list_exercises_with_difficulty_filter():
    # Arrange
    mock_repo = MagicMock()
    mock_repo.find_all_active = AsyncMock(return_value=([], 0))
    service = ExerciseService(mock_repo)
    
    # Act
    result = await service.list_exercises(page=1, per_page=20, difficulty=2)
    
    # Assert
    mock_repo.find_all_active.assert_called_once_with(page=1, per_page=20, difficulty=2)
    assert result.total == 0

@pytest.mark.unit
async def test_list_exercises_with_invalid_difficulty_raises_error():
    mock_repo = MagicMock()
    service = ExerciseService(mock_repo)
    
    with pytest.raises(InvalidDifficultyError):
        await service.list_exercises(page=1, per_page=20, difficulty=5)
```

```python
# backend/tests/integration/test_exercise_router.py
@pytest.mark.integration
async def test_get_exercises_filtered_by_difficulty(client, auth_headers, seeded_exercises):
    # seeded_exercises contiene ejercicios con difficulty 1, 2, 3, 4
    response = await client.get(
        "/api/v1/exercises?difficulty=2",
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert all(e["difficulty"] == 2 for e in data["data"]["items"])

@pytest.mark.integration
async def test_get_exercises_without_filter_returns_all(client, auth_headers, seeded_exercises):
    response = await client.get("/api/v1/exercises", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["total"] == len(seeded_exercises)
```

### Tests de frontend

```typescript
// frontend/src/features/exercises/stores/exerciseStore.test.ts
import { describe, it, expect, beforeEach } from 'vitest'
import { useExerciseStore } from './exerciseStore'
import { act, renderHook } from '@testing-library/react'

describe('exerciseStore', () => {
  beforeEach(() => {
    useExerciseStore.setState({ exercises: [], filters: { page: 1, perPage: 20 } })
  })
  
  it('setFilters resets page to 1', () => {
    const { result } = renderHook(() => useExerciseStore())
    
    act(() => {
      result.current.setFilters({ page: 3 })
    })
    act(() => {
      result.current.setFilters({ difficulty: 2 })
    })
    
    expect(result.current.filters.page).toBe(1)
    expect(result.current.filters.difficulty).toBe(2)
  })
})
```

---

## 8. Paso 7 — Pull Request

### Antes de abrir el PR

```bash
# Asegurarse de que la branch está actualizada con main
git fetch origin
git rebase origin/main

# Correr todos los tests localmente
cd backend && pytest tests/ -v
cd frontend && npm run test:run

# Correr el linter
cd backend && ruff check . && mypy app/
cd frontend && npm run lint && npm run format:check

# Si todo está bien, pushear
git push origin feat/exercise-difficulty-filter
```

### Abrir el PR

Título del PR: debe seguir el formato de Conventional Commits:
```
feat(exercise): add difficulty filter to exercise list
```

Descripción del PR:

```markdown
## Qué cambia
Agrega soporte para filtrar ejercicios por nivel de dificultad (1-4) en el endpoint 
`GET /api/v1/courses/{course_id}/exercises` y en el componente `ExerciseList` del frontend.

## Cómo testearlo
1. Backend: `pytest tests/ -v -k "difficulty"`
2. Frontend: `npm run test:run`
3. Manual: `GET /api/v1/courses/{course_id}/exercises?difficulty=2` debe retornar solo ejercicios de nivel 2

## Screenshots
[Si aplica para cambios visuales en el frontend]

## Checklist
- [x] Tests unitarios agregados
- [x] Tests de integración agregados
- [x] Convenciones de código seguidas
- [x] Documentación actualizada si aplica
- [x] CI pasa localmente

Closes #42
```

---

## 9. Paso 8 — Code Review y Merge

### Para el reviewer

Revisar:
- ¿La implementación sigue las convenciones del proyecto?
- ¿Los tests cubren los casos happy path y edge cases?
- ¿Hay trampas conocidas ignoradas (lazy loading, selectores de Zustand, etc.)?
- ¿Las queries de DB son eficientes? (¿hay N+1?)
- ¿La feature cumple los criterios de aceptación de la issue?

Aprobar con `gh pr review --approve` o solicitar cambios con comentarios específicos.

### Merge

```bash
# El tech lead o el autor del PR hace el merge después de la aprobación
gh pr merge 42 --squash --delete-branch

# O via GitHub UI: "Squash and merge"
```

Se usa **squash merge** para mantener un historial limpio en `main`. Todos los commits de la feature branch se aplastan en uno solo.

La branch se borra automáticamente después del merge (configurado en GitHub Settings).

---

## 10. Ejemplo Completo — Filtro de Dificultad en Ejercicios

A continuación, el resumen del flujo real para la feature de filtro de dificultad:

### Commits en la branch (antes del squash)

```
feat(exercise): add difficulty filter to exercise service
test(exercise): add unit tests for difficulty filter
feat(exercise): add difficulty query param to exercise router
feat(exercise): add difficulty filter to exercise repository
test(exercise): add integration tests for exercise difficulty filter
feat(exercise): add DifficultyFilter component
feat(exercise): update exerciseStore to support difficulty filter
feat(exercise): wire DifficultyFilter into ExerciseList
test(exercise): add Vitest tests for exerciseStore difficulty filter
```

### Commit final en main (después del squash)

```
feat(exercise): add difficulty filter to exercise list endpoint and UI (#42)

Adds support for filtering exercises by difficulty level (1-4) in both
the API endpoint and the React frontend. The filter resets pagination
to page 1 on each change to avoid stale results.

- Backend: difficulty query param validated in router, passed through service to repository
- Frontend: DifficultyFilter component, exerciseStore updated with filters slice
- Tests: unit + integration backend, Vitest frontend

Closes #42
```

### Tiempo estimado

| Tarea | Tiempo estimado |
|---|---|
| Issue + diseño | 30 min |
| Backend (repo + service + router) | 2 horas |
| Backend tests | 1 hora |
| Frontend (types + api + store + component) | 2 horas |
| Frontend tests | 1 hora |
| PR + review + ajustes | 1 hora |
| **Total** | **~7.5 horas** |

Esta feature es de complejidad baja-media. Features más complejas (p.ej. implementar el motor de evaluación N4 o el tutor socrático) requieren planning adicional con artefactos OPSX y pueden tomar días o semanas.
