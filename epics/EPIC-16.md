# EPIC-16: Traza Cognitiva Visual

> **Issue**: #16 | **Milestone**: Fase 3 — Motor Cognitivo | **Labels**: epic, fase-3, priority:high

## Contexto

La herramienta más poderosa del docente: reconstrucción visual completa de cómo un alumno trabajó en un ejercicio. Timeline de eventos color-coded por N1-N4, código evolutivo con diffs, chat completo con el tutor, y métricas superpuestas. Es como "ver la película" del proceso cognitivo del alumno.

## Alcance

### Backend
- Endpoints:
  - `GET /api/v1/cognitive/sessions/{id}/trace` — traza completa (eventos + snapshots + chat + métricas)
  - `GET /api/v1/cognitive/sessions/{id}/timeline` — eventos ordenados cronológicamente
  - `GET /api/v1/cognitive/sessions/{id}/code-evolution` — snapshots con diffs
- Endpoint de auditoría de hash chain (verificación de integridad):
  - `GET /api/v1/cognitive/sessions/{id}/verify-integrity`
- Endpoint de governance para admin:
  - `GET /api/v1/governance/events` — con filtros (ya creado en EPIC-11, acá se consume)
  - `GET /api/v1/governance/prompts` — historial de prompts con hashes

### Frontend
- **Traza cognitiva visual** (pantalla completa para docente):
  - Timeline vertical con eventos color-coded: N1=azul, N2=verde, N3=naranja, N4=violeta
  - Panel de código evolutivo: diff side-by-side entre snapshots
  - Panel de chat: conversación completa con el tutor
  - Métricas de la sesión superpuestas
  - Indicador de integridad del hash chain (verificado/comprometido)
- **Patrones de ejercicio** (vista agregada):
  - Cómo la clase resolvió un ejercicio particular
  - Distribución de estrategias (N2), patrones de error (N3)
- **Reportes de gobernanza** (admin):
  - Violaciones del tutor (guardrails triggered)
  - Historial de cambios de prompts
  - Alertas de integridad

## Contratos

### Produce
- Pantallas de traza cognitiva, patrones, y governance

### Consume
- Sesiones cognitivas + eventos (de EPIC-13)
- Métricas (de EPIC-14)
- Code snapshots (de EPIC-08)
- Tutor interactions (de EPIC-09)
- Governance events (de EPIC-11)

> **Acceso cross-schema**: Todos los datos de schemas ajenos se obtienen via REST a los endpoints de la fase dueña:
> - `code_snapshots` → GET desde EPIC-08 endpoints
> - `tutor_interactions` → GET desde EPIC-09 endpoints
> - `governance_events` → GET desde EPIC-11 endpoints
> - Solo `cognitive_sessions`, `cognitive_events`, `cognitive_metrics` se acceden por query directo (schema propio de Fase 3).

### Modelos
- No crea modelos nuevos (consume datos de todas las fases)

## Dependencias
- **Blocked by**: EPIC-11 (governance events), EPIC-13, EPIC-14 (necesita CTR y métricas), EPIC-08 (snapshots), EPIC-09 (chat)
- **Blocks**: Nada (feature final de visualización)

## Stories

- [ ] Endpoint: traza completa (eventos + snapshots + chat + métricas unificados)
- [ ] Endpoint: timeline de eventos cronológicos
- [ ] Endpoint: code evolution con diffs
- [ ] Endpoint: verificación de integridad del hash chain
- [ ] Frontend: timeline vertical color-coded (N1=azul, N2=verde, N3=naranja, N4=violeta)
- [ ] Frontend: panel de código evolutivo con diff side-by-side
- [ ] Frontend: panel de chat del tutor embebido
- [ ] Frontend: indicador de integridad hash chain
- [ ] Frontend: vista patrones de ejercicio (distribución de estrategias)
- [ ] Frontend: reportes de gobernanza (violations, prompt history)
- [ ] Tests: endpoints de traza retornan datos correctos
- [ ] Tests: verificación de integridad detecta tampering

## Criterio de Done

- Docente puede ver la traza completa de un alumno en un ejercicio
- Timeline con color-coding N1-N4 funcional
- Code diffs entre snapshots visibles
- Chat del tutor integrado en la traza
- Hash chain verificable desde la UI
- Patrones de ejercicio visibles a nivel clase
- Reportes de governance funcionales
- Tests pasan

## Referencia
- `knowledge-base/02-arquitectura/02_modelo_de_datos.md`
- `knowledge-base/01-negocio/05_flujos_principales.md`
