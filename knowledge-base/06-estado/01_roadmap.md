# Roadmap del Proyecto

**Plataforma AI-Native | UTN FRM**
Última actualización: 2026-04-10

---

## Resumen Ejecutivo

La plataforma se desarrolla en 4 fases paralelas durante 16 semanas, con 4 desarrolladores trabajando simultáneamente. La integración de las fases ocurre en las semanas 13-14, seguida de QA y deploy en semanas 15-16.

---

## Timeline General

```
Semanas  1-2:  Fase 0 — Fundación (todos los devs)
Semanas  3-12: Fases 1-4 en paralelo (1 dev por fase)
Semanas 13-14: Integración y testing E2E
Semanas 15-16: QA, staging deploy, usuarios piloto
Post-pilot:    Iteración y mejoras
```

---

## Fase 0 — Fundación (Semanas 1-2)

**Todos los desarrolladores trabajan juntos en esta fase.**

El objetivo es establecer la infraestructura base que las 4 fases paralelas necesitan para trabajar sin bloquearse entre sí.

### Entregables de Fase 0

**Infraestructura**
- [ ] Monorepo configurado (backend, frontend, shared, infra, devOps)
- [ ] `docker-compose.yml` con PostgreSQL 16 + Redis 7
- [ ] Scripts de seed data básico
- [ ] Pipeline CI/CD en GitHub Actions (lint, test, build)
- [ ] Pre-commit hooks (ruff, mypy, eslint, prettier)
- [ ] `.env.example` completo y documentado

**Base de Datos**
- [ ] 4 schemas creados: `operational`, `cognitive`, `governance`, `analytics`
- [ ] Migraciones Alembic iniciales con tablas base
- [ ] Modelo de usuarios (operational.users)
- [ ] Modelo de roles y permisos
- [ ] Configuración de índices base

**Backend Foundation**
- [ ] Estructura de carpetas establecida (routers, services, repositories, models, schemas)
- [ ] FastAPI application factory configurada
- [ ] Middleware de CORS, logging, error handling
- [ ] Endpoints de healthcheck (`/health`, `/health/full`)
- [ ] Sistema de configuración via Pydantic Settings
- [ ] Dependencias base: async session factory, UoW pattern

**Auth — Contrato establecido**
- [ ] `POST /api/v1/auth/login` → access_token + refresh_token
- [ ] `POST /api/v1/auth/refresh` → nuevo access_token
- [ ] `POST /api/v1/auth/logout` → invalidar tokens
- [ ] Middleware de autenticación JWT
- [ ] Decoradores de autorización por rol

**Frontend Foundation**
- [ ] Proyecto Vite + React 19 + TypeScript + TailwindCSS 4 configurado
- [ ] Sistema de rutas (React Router)
- [ ] Store de autenticación (Zustand) con persistencia
- [ ] Cliente HTTP base con interceptors de auth
- [ ] Pantalla de login funcionando contra el backend real
- [ ] Design system base (tokens de color, tipografía, spacing)

**Contratos entre Fases**
- [ ] OpenAPI spec inicial generado (`/openapi.json`)
- [ ] Tipos TypeScript generados desde el schema de Pydantic (o definidos manualmente)
- [ ] Convenciones documentadas y aprobadas por el equipo
- [ ] Esquemas de DB finalizados (sin cambios disruptivos después de semana 2)

**Testing Base**
- [ ] `conftest.py` con fixtures de session async, testcontainers, cliente HTTP
- [ ] Al menos 1 test de integración de auth funcionando
- [ ] Setup de Vitest para el frontend

### Criterio de Finalización Fase 0

La Fase 0 está completa cuando:
- Un desarrollador nuevo puede correr `make dev` y tener todo funcionando en 10 minutos
- Los tests de auth pasan en CI
- Cada desarrollador puede iniciar su fase sin bloquearse en infraestructura

---

## Fases 1-4 — Desarrollo Paralelo (Semanas 3-12)

Cada developer es responsable de su fase de extremo a extremo: backend, frontend, tests.

### Fase 1 — Gestión de Ejercicios y Evaluación de Código

**Developer**: Dev 1
**Semanas**: 3-12 (10 semanas)

**Objetivo**: Módulo para gestionar el catálogo de ejercicios y ejecutar el código de los estudiantes en sandbox seguro.

**Backend**
- CRUD de ejercicios (professores)
- Modelo de topics/categorías
- Endpoint de listado con filtros (dificultad, topic, búsqueda)
- Sandbox de ejecución de código Python (subprocess con límites de CPU/memoria/tiempo)
- Evaluación de casos de test contra el código del estudiante
- API de envío de soluciones
- Registro de intentos en `operational` schema

**Frontend**
- Pantalla de listado de ejercicios (con filtros, paginación)
- Vista detalle de ejercicio
- Editor de código (CodeMirror o Monaco Editor)
- Botón de ejecutar con feedback visual
- Resultado de evaluación (casos que pasan/fallan)
- Panel de administración para profesores (CRUD ejercicios)

**Tests**
- Sandbox: test de timeout, memory limit, sin acceso a red
- Evaluación: casos de test correctos e incorrectos
- CRUD de ejercicios con roles (solo profesores crean)

**Milestones intermedios**:
- Semana 4: CRUD básico de ejercicios funcionando
- Semana 7: Sandbox ejecutando código con límites
- Semana 10: Evaluación de casos de test completa
- Semana 12: UI completa, tests pasando

---

### Fase 2 — Tutor Socrático

**Developer**: Dev 2
**Semanas**: 3-12 (10 semanas)

**Objetivo**: Motor de tutoría socrática con IA que guía sin dar soluciones, con guardrails robustos.

**Backend**
- Gestión de sesiones de tutor (crear, continuar, cerrar)
- Integración con Anthropic API (streaming)
- Sistema de prompts: prompt base socrático, contexto del ejercicio, historial de conversación
- Guardrails anti-solver: pre-processing del input del estudiante, post-processing de la respuesta
- Rate limiting por usuario/sesión
- Registro de cada interacción de tutor en `operational` schema (tabla `tutor_interactions`)
- WebSocket gateway para streaming de respuestas en tiempo real

**Frontend**
- Componente de chat (TutorChat) con streaming de texto
- Indicador de "el tutor está escribiendo..."
- Historial de conversación persistente en la sesión
- Botón para iniciar/finalizar sesión
- Indicador de uso de créditos/tokens restantes

**Tests**
- 20+ tests adversariales (ver estrategia de testing)
- Tests de rate limiting
- Tests de persistencia del historial
- Tests de WebSocket reconnection

**Milestones intermedios**:
- Semana 5: Integración básica con Anthropic API (sin streaming)
- Semana 7: Streaming via WebSocket funcionando
- Semana 9: Guardrails implementados y testeados
- Semana 12: Tests adversariales pasando

---

### Fase 3 — Trazabilidad Cognitiva (CTR + Hash Chain)

**Developer**: Dev 3
**Semanas**: 3-12 (10 semanas)

**Objetivo**: Sistema de registro de eventos cognitivos inmutables con integridad verificable via hash chain.

**Backend**
- Modelo CTR completo en `cognitive` schema
- Servicio de hash chain: compute, verify, detect breaks
- Registro automático de eventos cognitivos desde las otras fases (hooks/events)
- API de consulta de CTRs por usuario/sesión
- Job de verificación periódica de integridad del chain
- Sistema de alertas en `governance` schema cuando hay rupturas
- Export de CTRs en formato estructurado (para análisis)

**Frontend**
- Panel de trazabilidad cognitiva para profesores
- Timeline de eventos del estudiante por ejercicio
- Visualización del nivel cognitivo en el tiempo (N1-N4)
- Indicadores de uso de IA (crítico vs dependiente)
- Vista de detalle de un CTR específico

**Tests**
- Hash chain: determinismo, integridad, detección de tampering
- Inmutabilidad: verificar que no hay endpoints de modificación de CTRs
- Concurrencia: múltiples CTRs creados simultáneamente
- Job de verificación: simular ruptura y verificar alerta

**Milestones intermedios**:
- Semana 5: Modelo CTR y hash chain básico funcionando
- Semana 7: Registro automático desde eventos del tutor
- Semana 9: Job de verificación implementado
- Semana 12: Panel de visualización completo

---

### Fase 4 — Evaluación Cognitiva N4

**Developer**: Dev 4
**Semanas**: 3-12 (10 semanas)

**Objetivo**: Motor de evaluación del nivel cognitivo (N1-N4) basado en los CTRs, con dashboard de analytics.

**Backend**
- Algoritmo de scoring N1-N4 basado en los CTRs de una sesión
- Carga de rúbricas de evaluación desde `governance` schema
- Cálculo de Calidad Epistémica (Qe) por sesión
- Detección de patrones de uso: crítico vs dependiente de IA
- Agregaciones para analytics en `analytics` schema
- Jobs de cálculo de métricas (diario/semanal)
- API de reportes para profesores y alumnos

**Frontend**
- Dashboard de alumno: progreso cognitivo en el tiempo
- Dashboard de profesor: vista de toda la clase
- Gráficos de distribución N1-N4 por ejercicio
- Heatmap de actividad cognitiva
- Reporte individual exportable (PDF)
- Alertas de riesgo (alumno estancado en N1 por mucho tiempo)

**Tests**
- Scoring: resultados conocidos contra rúbrica conocida
- Qe: cálculo correcto con casos borde (sesión sin CTRs, sesión muy corta)
- Detección de patrones: identificar correctamente uso crítico vs dependiente
- Jobs: idempotencia (correr dos veces no duplica datos)

**Milestones intermedios**:
- Semana 5: Algoritmo de scoring N1 y N2 implementado
- Semana 7: N3 y N4 completos
- Semana 9: Dashboard básico de alumno
- Semana 12: Reportes y dashboard de profesor completos

---

## Integración (Semanas 13-14)

**Todos los desarrolladores trabajan juntos.**

El objetivo es verificar que las 4 fases funcionan correctamente de forma integrada.

### Actividades

**Semana 13 — Integración Técnica**
- [ ] Despliegue conjunto en entorno de staging
- [ ] Tests E2E de flujos completos (alumno resuelve ejercicio → chat con tutor → CTR registrado → puntaje calculado)
- [ ] Verificación de contratos entre módulos (Fase 1 ↔ Fase 2, Fase 2 ↔ Fase 3, Fase 3 ↔ Fase 4)
- [ ] Resolución de incompatibilidades encontradas
- [ ] Performance testing básico (tiempo de respuesta del tutor, latencia de WebSocket)

**Semana 14 — Estabilización**
- [ ] Corrección de bugs de integración
- [ ] Tests de carga ligeros (10 usuarios simultáneos)
- [ ] Revisión de seguridad básica (headers, CORS, rate limiting)
- [ ] Documentación de APIs actualizada
- [ ] Demo interno para el director de tesis

---

## QA y Deploy Piloto (Semanas 15-16)

**Semana 15 — Preparación para Piloto**
- [ ] Deploy en servidor institucional de UTN FRM
- [ ] Configuración de monitoreo básico (logs, uptime)
- [ ] Carga de ejercicios reales del curso
- [ ] Reclutamiento de 5-10 alumnos voluntarios para el piloto
- [ ] Capacitación a profesores participantes
- [ ] Plan de contingencia (rollback si hay problemas críticos)

**Semana 16 — Piloto Controlado**
- [ ] Ejecución del piloto con usuarios reales
- [ ] Monitoreo continuo de logs y errores
- [ ] Recolección de feedback (formulario estructurado)
- [ ] Identificación de problemas de UX/funcionalidad
- [ ] Bug fixes críticos (los que bloquean el uso)
- [ ] Análisis preliminar de datos cognitivos recolectados

---

## Post-Piloto — Iteraciones Futuras

Después del piloto, las mejoras se priorizan según el feedback recibido:

### Corto plazo (1-4 semanas post-piloto)
- Fixes de bugs reportados por usuarios
- Mejoras de UX basadas en observaciones del piloto
- Optimización de performance si es necesario
- Ajuste de los prompts del tutor según calidad observada

### Mediano plazo (1-3 meses)
- Soporte para múltiples modelos LLM (Google Gemini, OpenAI GPT)
- Ejercicios en JavaScript y Java (no solo Python)
- Sistema de notificaciones (alertas de progreso)
- Mejoras al algoritmo de scoring N4 basadas en datos reales
- Analytics dashboard más rico (semestre completo de datos)

### Largo plazo / Futuro
- Soporte multi-institución (otras sedes de UTN, otras universidades)
- Multi-tenancy en la base de datos
- API pública para integración con LMS institucionales (Moodle, Canvas)
- Mobile app (React Native)
- Análisis longitudinal de cohortes (comparación entre años académicos)
- Publicación de resultados de investigación (alineado con tesis doctoral)

---

## Riesgos del Roadmap

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Fase 0 se extiende más de 2 semanas | Media | Alto | Scope mínimo definido, no gold-plating |
| Las fases paralelas generan conflictos de DB | Baja | Alto | Schema de DB frozen después de semana 2 |
| Los guardrails del tutor no logran bloquear prompts adversariales | Alta | Crítico | Revisión continua de guardrails desde semana 5 |
| LLM costs superan presupuesto en desarrollo | Media | Medio | Usar haiku en dev, opus solo en tests de calidad |
| Alineación con tesis es insuficiente | Media | Alto | Revisión semanal con director de tesis |
| Problemas de performance en staging | Media | Medio | Load testing en semana 14, no en semana 15 |
