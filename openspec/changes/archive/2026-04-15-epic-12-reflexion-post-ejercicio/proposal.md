## Why

Despues de enviar una submission, no hay mecanismo para que el alumno reflexione sobre su proceso. La reflexion metacognitiva es clave para el modelo N4 — captura explicitamente que fue dificil, que estrategia uso, como evalua su uso de la IA. Sin este dato, Fase 3 no puede calcular reflection_score ni completar el perfil cognitivo.

## What Changes

- Nuevo modelo `reflections` en schema operational con campos guiados
- ReflectionService con validacion (post-submit, una por submission, RBAC)
- Endpoints REST: crear y ver reflexion
- Frontend: panel de reflexion post-submission (formulario guiado)
- Frontend: vista read-only de reflexion enviada
- Frontend docente: ver reflexiones de su comision
- Evento `reflection.submitted` al outbox

## Capabilities

### New Capabilities
- `reflection-model`: Modelo SQLAlchemy reflections en schema operational con Alembic migration
- `reflection-service`: Domain service con validacion, RBAC, evento reflection.submitted
- `reflection-api`: Endpoints REST para crear y leer reflexiones
- `reflection-frontend`: Panel de reflexion post-submission y vista read-only

### Modified Capabilities
- `tutor-chat-ws`: No modificado — la reflexion es independiente del chat

## Impact

- Backend: nuevo modulo `app/features/reflections/` o extension de `submissions/`
- Migration: nueva tabla operational.reflections
- Frontend: modificar StudentActivityViewPage para mostrar formulario post-submit
- Eventos: reflection.submitted → events:submissions stream
