## Context

Auditoria pre-integracion revelo:
- MSW nunca existio en el codebase (solo un flag muerto en .env.development)
- 100% de los stores/hooks ya usan apiClient contra el backend real
- Todos los endpoints responden 200 excepto tutor messages para docente (403)
- El trace store (EPIC-16) necesita leer chat del tutor como docente

Endpoints auditados: auth, courses, exercises, activities, evaluation, risk, cognitive, governance, tutor, health — todos 200.

## Goals / Non-Goals

**Goals:**
- Todo endpoint responde correctamente para el rol que lo necesita
- Flujo E2E alumno funciona sin errores en console
- Flujo E2E docente funciona sin errores en console
- No quedan residuos de MSW

**Non-Goals:**
- Refactor de componentes existentes
- Mejoras de UX/UI
- Nuevas features

## Decisions

### D1: Endpoint separado para docente tutor messages

En vez de modificar el endpoint existente de alumno (que filtra por current_user.id), agrego un endpoint nuevo `GET /api/v1/teacher/students/{student_id}/exercises/{exercise_id}/messages` para docente/admin. Esto preserva la seguridad del endpoint del alumno.

### D2: Cleanup minimo, no refactor

Solo se tocan los archivos estrictamente necesarios para que el E2E funcione. No se refactorean tipos, no se mejoran componentes, no se agregan features.

## Risks / Trade-offs

- **[Bajo]** El endpoint nuevo de teacher messages expone chat de alumnos a docentes — esto es intencional (el docente NECESITA ver el chat para la traza cognitiva).
