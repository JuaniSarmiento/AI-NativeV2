# EPIC-18: Testing E2E con Playwright

> **Issue**: #18 | **Milestone**: Integración y QA | **Labels**: epic, integration, priority:critical

## Contexto

Tests end-to-end que verifican los flujos completos como los usaría un usuario real. Playwright simula un browser y recorre los flujos críticos: alumno resuelve ejercicio → chatea con tutor → envía → reflexiona. Docente ve dashboard → navega traza cognitiva.

## Alcance

### Testing
- Setup Playwright con configuración del proyecto
- **Flujo alumno completo**:
  1. Login → ver cursos → seleccionar ejercicio
  2. Escribir código en Monaco → ejecutar → ver output
  3. Chatear con tutor → recibir respuesta streaming
  4. Iterar código → re-ejecutar → pasar tests
  5. Enviar submission → completar reflexión
  6. Ver historial de submissions
- **Flujo docente completo**:
  1. Login → dashboard de comisión
  2. Ver indicadores agregados + radar chart
  3. Ver tabla de alumnos en riesgo
  4. Click en alumno → perfil cognitivo
  5. Ver traza cognitiva visual de una sesión
- **Tests de seguridad básicos**:
  - Acceso sin token → 401
  - Alumno accede a ruta docente → 403
  - Rate limiting funciona
- **Performance básico**:
  - Tiempo de respuesta del tutor < 5s primer token
  - Carga de dashboard < 3s

### CI Integration
- Playwright en GitHub Actions
- Screenshots de evidencia en caso de fallo

## Contratos

### Produce
- Suite E2E que valida los flujos críticos
- Evidencia de que el sistema funciona end-to-end
- Reporte de performance básico

### Consume
- Todo el sistema integrado (post EPIC-17)

## Dependencias
- **Blocked by**: EPIC-17 (necesita integración completa)
- **Blocks**: EPIC-19 (deploy solo si E2E pasan)

## Stories

- [ ] Setup Playwright con configuración del proyecto
- [ ] E2E: flujo completo del alumno (login → código → tutor → submit → reflexión)
- [ ] E2E: flujo completo del docente (login → dashboard → traza cognitiva)
- [ ] E2E: tests de seguridad (401, 403, rate limiting)
- [ ] E2E: performance básico (tiempo primer token, carga dashboard)
- [ ] CI: Playwright en GitHub Actions con screenshots en fallo
- [ ] Fix de bugs descubiertos durante E2E

## Criterio de Done

- Flujo alumno completo pasa E2E
- Flujo docente completo pasa E2E
- Tests de seguridad pasan
- Performance dentro de umbrales
- CI ejecuta E2E en cada PR

## Referencia
- `knowledge-base/05-dx/06_estrategia_de_testing.md`
