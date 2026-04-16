## Context

El StudentActivityViewPage tiene un estado `submitted` que muestra una pantalla de confirmacion "Actividad enviada" con un link para volver. Este es el punto de integracion para el formulario de reflexion — en lugar de redirigir inmediatamente, mostrar el formulario primero.

Submissions existentes: ActivitySubmission → Submission (1:N). La reflexion se asocia a ActivitySubmission (una reflexion por entrega de actividad completa, no por ejercicio individual).

## Goals / Non-Goals

**Goals:** Modelo reflections, CRUD endpoints, formulario guiado post-submit, vista read-only, evento reflection.submitted

**Non-Goals:** Reflexion por ejercicio individual (es por submission de actividad), analisis de reflexiones (Fase 3), gamificacion de reflexion

## Decisions

### D1: Reflection como modulo dentro de submissions, no separado
La reflexion es conceptualmente parte del flujo de submissions. Agregar modelo, service y endpoints dentro de `app/features/submissions/` en lugar de crear un modulo nuevo. Reduce fragmentacion.

### D2: Reflexion asociada a ActivitySubmission, no a Submission individual
Una reflexion por entrega de actividad completa. El alumno reflexiona sobre la experiencia completa, no sobre cada ejercicio por separado.

### D3: Frontend — formulario inline despues del submit, no modal
El formulario de reflexion reemplaza la pantalla de "Actividad enviada" con un formulario guiado. Despues de enviar la reflexion, se muestra la confirmacion final. Si el alumno no quiere reflexionar, tiene un link para saltar.

### D4: Campos todos requeridos con validacion client-side y server-side
Los 5 campos (difficulty_perception, strategy_description, ai_usage_evaluation, what_would_change, confidence_level) son todos requeridos. Validacion Pydantic en backend, validacion de form en frontend.

### D5: Evento reflection.submitted en stream events:submissions
Se routea por el prefix "reflection" que hay que agregar al outbox worker, o se usa el prefix existente "submission" renombrando el evento. Decision: agregar routing para "reflection" → events:submissions.
