## Context

EPIC-07 dejó sandbox funcional (terminal-only output, no test results visibles). Exercises tienen rubric + test_cases de referencia. Activities agrupan exercises. El alumno navega ejercicio por ejercicio dentro de la actividad con editor de código + stdin.

## Goals / Non-Goals

**Goals:**
- Submissions per exercise with code, status, attempt tracking
- Activity-level submission (enviar todos los ejercicios de la actividad juntos)
- Code snapshots inmutables (30s auto-save + ante ejecución)
- Historial de envíos para alumno y docente
- Eventos al event bus

**Non-Goals:**
- No implementar evaluación por IA (EPIC futura — rúbrica + nota)
- No implementar Monaco Editor (textarea monospace es suficiente para MVP)
- No implementar diff entre snapshots
- No implementar score/nota — el campo queda null hasta que la IA evalúe

## Decisions

### D1: ActivitySubmission como agrupador

Cuando el alumno envía una actividad, se crea un `ActivitySubmission` (activity_id, student_id, status, submitted_at) y N `Submission` (uno por ejercicio). Esto permite trackear el envío como unidad y los ejercicios individualmente.

### D2: Submission status simplificado

`pending` (recién creado, sin evaluar) → se mantiene en pending hasta que la IA evalúe (EPIC futura). No hay `running/passed/failed` todavía porque no evaluamos con test cases.

### D3: Snapshots fire-and-forget

El endpoint de snapshot es POST-only, sin auth pesado. El frontend envía cada 30s. Si falla, no bloquea al alumno. Los snapshots son inmutables — no hay UPDATE ni DELETE.

### D4: attempt_number incremental

Cada vez que el alumno envía la actividad, se incrementa attempt_number en cada submission. Esto permite ver cuántas veces intentó.

## Risks / Trade-offs

- **[Risk] Snapshots cada 30s generan mucho volumen** → Mitigation: solo guarda si el código cambió desde el último snapshot.
- **[Risk] Enviar actividad sin haber escrito código en algún ejercicio** → Mitigation: validar que cada ejercicio tenga código antes de permitir envío.
