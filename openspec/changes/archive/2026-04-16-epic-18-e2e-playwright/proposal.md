## Why

Todo el sistema esta integrado (EPICs 1-17) pero no hay tests E2E que validen los flujos completos como los usaria un usuario real. Necesitamos evidencia automatizada de que el flujo alumno (login → codigo → tutor → submit → nota) y docente (login → dashboard → correccion → traza) funcionan end-to-end.

## What Changes

- Setup Playwright en el proyecto
- E2E tests para flujo alumno completo
- E2E tests para flujo docente completo
- Tests de seguridad basicos (401, 403)
- Tests de performance basicos

## Capabilities

### New Capabilities
- `e2e-testing`: Suite Playwright con tests E2E para flujos criticos

## Impact

- **Testing**: Nuevo directorio `e2e/` con Playwright config y tests
- **Dependencies**: `@playwright/test` como devDependency
- **CI**: Playwright ejecutable en GitHub Actions (futuro)
