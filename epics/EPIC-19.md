# EPIC-19: Deploy Staging y Piloto

> **Issue**: #19 | **Milestone**: Integración y QA | **Labels**: epic, integration, priority:high

## Contexto

Deploy del sistema completo a un entorno de staging y ejecución del piloto con usuarios reales (5-10 alumnos voluntarios + docentes de UTN FRM). Este es el test final antes de usar la plataforma en producción académica.

## Alcance

### Infraestructura
- Docker Compose para producción (con volúmenes persistentes, healthchecks)
- Configuración de servidor institucional UTN FRM
- Variables de entorno de producción (secrets seguros)
- Backup de base de datos programado
- Monitoreo básico: logs centralizados, uptime check, alertas de error
- Plan de contingencia: rollback procedure documentado

### Datos
- Carga de ejercicios reales del curso
- Creación de cuentas para alumnos y docentes piloto
- Seed data de producción (cursos, comisiones reales)

### Piloto
- Ejecución con 5-10 alumnos voluntarios
- Monitoreo continuo durante el piloto
- Formulario de feedback estructurado (UX, bugs, sugerencias)
- Fix de bugs críticos en caliente
- Análisis preliminar de datos cognitivos recolectados

## Contratos

### Produce
- Sistema desplegado y funcional en staging
- Feedback de usuarios reales
- Datos cognitivos reales para validar el modelo N4
- Lista de bugs y mejoras post-piloto

### Consume
- Sistema completo E2E tested (post EPIC-18)

## Dependencias
- **Blocked by**: EPIC-18 (E2E tests deben pasar)
- **Blocks**: Nada (es la EPIC final)

## Stories

- [ ] Docker Compose producción con healthchecks y volúmenes
- [ ] Configuración de servidor UTN FRM
- [ ] Variables de entorno de producción (secrets)
- [ ] Backup de DB programado
- [ ] Monitoreo: logs, uptime, alertas de error
- [ ] Carga de ejercicios y datos reales
- [ ] Creación de cuentas piloto
- [ ] Plan de contingencia y rollback documentado
- [ ] Ejecución del piloto (5-10 alumnos)
- [ ] Formulario de feedback
- [ ] Fix de bugs críticos
- [ ] Análisis preliminar de datos cognitivos

## Criterio de Done

- Sistema estable en staging por al menos 48hs sin caídas
- Piloto ejecutado con usuarios reales
- Feedback recolectado y documentado
- Datos cognitivos recolectados y validados preliminarmente
- Bugs críticos resueltos

## Referencia
- `knowledge-base/04-infraestructura/03_deploy.md`
- `knowledge-base/06-estado/01_roadmap.md`
