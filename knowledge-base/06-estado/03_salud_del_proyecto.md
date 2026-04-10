# Salud del Proyecto

**Plataforma AI-Native | UTN FRM**
Última actualización: 2026-04-10

> Este documento es una plantilla de estado que se actualiza semanalmente. Cada sección tiene un estado inicial "No iniciado" o "N/A". A medida que el proyecto avanza, se actualiza con datos reales.

---

## Resumen Ejecutivo

| Dimensión | Estado | Nota |
|---|---|---|
| Fase 0 — Fundación | No iniciada | Comienza semana 1 |
| Fase 1 — Ejercicios | No iniciada | Comienza semana 3 |
| Fase 2 — Tutor | No iniciada | Comienza semana 3 |
| Fase 3 — CTR | No iniciada | Comienza semana 3 |
| Fase 4 — Evaluación | No iniciada | Comienza semana 3 |
| Integración | No iniciada | Semanas 13-14 |
| QA / Piloto | No iniciada | Semanas 15-16 |
| Test Coverage | N/A | Objetivo: 80%+ |
| CI/CD | No configurado | |
| Deploy staging | No desplegado | |

---

## Estado por Fase

### Fase 0 — Fundación

**Estado general**: No iniciada
**Fecha objetivo de finalización**: Fin de semana 2

| Tarea | Estado | Responsable |
|---|---|---|
| Monorepo setup | Pendiente | Todos |
| Docker Compose (PG + Redis) | Pendiente | Todos |
| Pipeline CI/CD | Pendiente | Todos |
| Pre-commit hooks | Pendiente | Todos |
| Schema de DB (4 schemas) | Pendiente | Todos |
| Migraciones Alembic iniciales | Pendiente | Todos |
| Auth backend (login/refresh/logout) | Pendiente | Todos |
| Frontend base (Vite + React + Zustand) | Pendiente | Todos |
| Login funcionando end-to-end | Pendiente | Todos |
| Seed data script | Pendiente | Todos |
| Contratos de API documentados | Pendiente | Todos |

**Bloqueantes**: Ninguno conocido.

**Riesgos**: El setup inicial puede tomar más tiempo del estimado si hay conflictos de configuración de entornos entre los desarrolladores.

---

### Fase 1 — Gestión de Ejercicios y Sandbox

**Estado general**: No iniciada
**Semanas asignadas**: 3-12
**Developer**: Dev 1

| Componente | Estado |
|---|---|
| CRUD de ejercicios (backend) | Pendiente |
| Sandbox de ejecución Python | Pendiente |
| Evaluación de casos de test | Pendiente |
| UI de listado de ejercicios | Pendiente |
| Editor de código | Pendiente |
| Panel admin de profesores | Pendiente |
| Tests unitarios de sandbox | Pendiente |
| Tests de integración | Pendiente |

**Última actualización**: N/A — no iniciada.

---

### Fase 2 — Tutor Socrático

**Estado general**: No iniciada
**Semanas asignadas**: 3-12
**Developer**: Dev 2

| Componente | Estado |
|---|---|
| Gestión de sesiones de tutor | Pendiente |
| Integración Anthropic API | Pendiente |
| Sistema de prompts socrático | Pendiente |
| Guardrails anti-solver | Pendiente |
| Streaming via WebSocket | Pendiente |
| Componente TutorChat (frontend) | Pendiente |
| Tests adversariales (20+ prompts) | Pendiente |
| Rate limiting | Pendiente |

**Última actualización**: N/A — no iniciada.

---

### Fase 3 — Trazabilidad Cognitiva

**Estado general**: No iniciada
**Semanas asignadas**: 3-12
**Developer**: Dev 3

| Componente | Estado |
|---|---|
| Modelo CTR completo | Pendiente |
| Servicio de hash chain | Pendiente |
| Registro automático de eventos | Pendiente |
| API de consulta de CTRs | Pendiente |
| Job de verificación de integridad | Pendiente |
| Panel de trazabilidad (frontend) | Pendiente |
| Tests de integridad del chain | Pendiente |

**Última actualización**: N/A — no iniciada.

---

### Fase 4 — Evaluación Cognitiva N4

**Estado general**: No iniciada
**Semanas asignadas**: 3-12
**Developer**: Dev 4

| Componente | Estado |
|---|---|
| Algoritmo de scoring N1-N4 | Pendiente (bloqueado por PQ-001) |
| Carga de rúbricas desde governance | Pendiente |
| Cálculo de Qe (Calidad Epistémica) | Pendiente |
| Dashboard de alumno | Pendiente |
| Dashboard de profesor | Pendiente |
| Jobs de cálculo de métricas | Pendiente |
| Reports exportables | Pendiente |

**Bloqueantes**: PQ-001 (algoritmo exacto de scoring) sin respuesta del director de tesis.

**Última actualización**: N/A — no iniciada.

---

## Métricas de Calidad

### Test Coverage

| Módulo | Coverage Actual | Objetivo |
|---|---|---|
| `app/core/` | N/A | 90%+ |
| `app/services/` | N/A | 85%+ |
| `app/repositories/` | N/A | 80%+ |
| `app/routers/` | N/A | 80%+ |
| Frontend stores | N/A | 85%+ |
| Frontend components | N/A | 70%+ |
| **Total** | **N/A** | **80%+** |

### Issues Abiertas

| Tipo | Cantidad | Más antigua |
|---|---|---|
| Bug crítico | 0 | — |
| Bug medio | 0 | — |
| Bug bajo | 0 | — |
| Feature request | 0 | — |
| Tech debt | 0 | — |

*Actualizar cuando se abran issues en GitHub.*

### Deuda Técnica

Ver `knowledge-base/06-estado/04_deuda_tecnica.md`.

Resumen:
- Items críticos: 0
- Items altos: 0
- Items medios: 0
- Items bajos: 0

---

## Riesgos Activos

Los riesgos se actualizan cada semana. Para detalles completos, ver `knowledge-base/06-estado/02_preguntas_y_suposiciones.md`.

### Riesgo 1: Costo de API de Anthropic en desarrollo

**Probabilidad**: Alta
**Impacto**: Medio
**Estado**: Abierto (mitigación parcial: usar haiku en dev)

En desarrollo intensivo, cada desarrollador hace muchas llamadas de prueba a la API de Anthropic. Sin disciplina, los costos pueden dispararse.

**Mitigación**: 
- Variable `ANTHROPIC_MODEL=claude-haiku-3-5` en `.env` de desarrollo
- Presupuesto mensual de API establecido con alertas en Anthropic Console
- Tests adversariales corren solo en CI semanal, no en desarrollo local

---

### Riesgo 2: Seguridad del Sandbox Python

**Probabilidad**: Media
**Impacto**: Crítico
**Estado**: Abierto

El sandbox que ejecuta código arbitrario de estudiantes es una superficie de ataque importante. Código malicioso podría intentar acceder al sistema de archivos, red, o consumir recursos.

**Mitigación**:
- Timeout estricto de 5 segundos
- Límite de memoria
- Sin acceso a red en el subprocess
- Tests de seguridad específicos del sandbox
- Revisión de seguridad antes del piloto

---

### Riesgo 3: Alineación con Tesis Doctoral

**Probabilidad**: Media
**Impacto**: Alto
**Estado**: Abierto

El sistema implementa conceptos definidos en la tesis doctoral en progreso. Si la tesis cambia definiciones clave (p.ej. cómo se calcula N4, qué es "uso crítico" de IA), el código necesita actualizarse.

**Mitigación**:
- Reunión semanal con el director de tesis
- Preguntas abiertas PQ-001, PQ-003 bloqueadas hasta tener respuesta oficial
- Código de evaluación cognitiva bien separado y testeable para facilitar cambios

---

### Riesgo 4: Rendimiento de WebSocket en red universitaria

**Probabilidad**: Baja-Media
**Impacto**: Medio
**Estado**: Abierto

Las redes universitarias pueden tener proxies y firewalls que interfieren con WebSocket. Si WS está bloqueado, el streaming del tutor no funciona.

**Mitigación**:
- Implementar fallback a long polling si WS falla
- Testear en la red de UTN FRM antes del piloto
- Configurar nginx como WebSocket proxy si es necesario

---

## Historial de Salud Semanal

*Tabla para actualizar cada semana con el estado al cierre de la misma.*

| Semana | Fase 0 | F1 | F2 | F3 | F4 | Coverage | Issues críticos | Nota |
|---|---|---|---|---|---|---|---|---|
| Semana 1 | En curso | — | — | — | — | N/A | 0 | — |
| Semana 2 | — | — | — | — | — | N/A | — | — |
| Semana 3 | — | En curso | En curso | En curso | En curso | — | — | — |
| ... | | | | | | | | |

*Poblar esta tabla al final de cada semana.*

---

## Cómo Actualizar Este Documento

Al final de cada semana:

1. Actualizar el estado de cada tarea en las secciones de fase
2. Actualizar la tabla de métricas de coverage (correr `make test-cov`)
3. Actualizar el conteo de issues abiertas (revisar GitHub)
4. Actualizar la tabla de riesgos activos (¿hay nuevos? ¿se resolvió alguno?)
5. Agregar una fila a la tabla de historial semanal
6. Commitear: `docs(estado): update project health week N`
