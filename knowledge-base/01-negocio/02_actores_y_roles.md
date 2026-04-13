# Actores y Roles

## Actores del Sistema

### Estudiante (Alumno)

El actor principal del sistema. Resuelve ejercicios de programación en un entorno mediado por IA, interactúa con el tutor socrático, y genera evidencia de su proceso cognitivo.

**Capacidades**:
- Ver cursos inscriptos y ejercicios asignados
- Escribir código en editor Monaco con syntax highlighting Python
- Ejecutar código en sandbox seguro y ver resultados (stdout, stderr, test results)
- Chatear con el tutor IA socrático durante la resolución
- Enviar submissions cuando considera terminado el ejercicio
- Completar formulario de reflexión post-ejercicio
- Ver su perfil cognitivo propio (scores N1-N4, calidad epistémica, dependency)
- Ver historial de submissions con score multidimensional

**Restricciones**:
- No puede ver perfiles cognitivos de otros alumnos
- No puede crear ni modificar ejercicios
- Rate limited a 30 mensajes/hora con el tutor por ejercicio
- El código ejecutado está sandboxed (10s timeout, 128MB RAM, sin red)

### Docente

El evaluador y analista del proceso de aprendizaje. No interactúa directamente con el tutor — su rol es observar, interpretar y actuar sobre los datos que el sistema produce.

**Capacidades**:
- Gestionar cursos y comisiones
- Crear, editar y configurar ejercicios (enunciado, test cases, dificultad, taxonomía)
- Ver todas las submissions de alumnos de sus comisiones
- Acceder al dashboard de curso: promedios N1-N4, distribución de calidad epistémica, alumnos en riesgo
- Ver perfil cognitivo individual de cada alumno: radar chart N1-N4, evolución temporal, dependency score
- Reconstruir la traza cognitiva completa de un episodio: timeline visual con eventos color-coded, código evolutivo con diff, chat con tutor
- Ver patrones agregados de ejercicio: estrategias más comunes, errores frecuentes, nivel de dependencia de IA
- Ver reportes de gobernanza: violaciones del tutor, cambios de prompts, alertas del sistema

**Restricciones**:
- Solo ve datos de alumnos de sus comisiones
- No puede modificar el CTR ni las métricas calculadas (son inmutables)
- No puede modificar el system prompt del tutor (requiere admin)

### Administrador

Gestiona la configuración del sistema y las políticas de gobernanza.

**Capacidades**:
- Todo lo que puede hacer un docente, sin restricción de comisión
- Gestionar usuarios: crear, asignar roles, activar/desactivar
- Gestionar configuración del sistema
- Gestionar system prompts del tutor (crear nuevas versiones, activar/desactivar)
- Ver todos los reportes de gobernanza
- Acceder a eventos de auditoría del sistema completo

**Restricciones**:
- No puede modificar CTRs cerrados (inmutabilidad garantizada por hash chain)
- Cambios en system prompt generan governance event y nueva versión semántica

### Tutor IA (Actor no humano)

Agente pedagógico regulado implementado sobre Anthropic Claude. No es un usuario del sistema — es un **componente** del sistema cuyo comportamiento está normado.

**Comportamiento regulado**:
- NUNCA entrega la solución completa
- Responde con preguntas elicitadoras cuando el alumno pide la solución
- Ofrece definiciones conceptuales cuando se pregunta por significado
- Máximo 5 líneas de código por bloque de ejemplo, siempre parcial y contextual
- Tono de andamiaje, sin paternalismo, adaptado al nivel del alumno
- No introduce vocabulario técnico que el alumno no haya usado primero (salvo como pregunta)

**Principios socráticos operativos** (alineados con Cap. 15 y Anexo A de active6.docx):
1. Nunca entregar la solución completa
2. Partir del error real del estudiante
3. Preguntas breves y progresivas
4. Forzar prueba con caso concreto
5. Cierre con reflexión metacognitiva explícita
6. No introducir vocabulario no usado por el alumno

**Invariancia entre proveedores**: La invariancia entre proveedores es un objetivo de diseño para versiones futuras (P3). En v1, el comportamiento se valida exclusivamente contra el adaptador de Anthropic. Los items P3 del backlog (#29, #30) cubren adaptadores OpenAI y Ollama.

## Matriz de Permisos (RBAC)

| Recurso | alumno | docente | admin |
|---------|--------|---------|-------|
| Cursos | ver propios | gestionar propios | gestionar todos |
| Comisiones | ver propias | gestionar propias | gestionar todas |
| Ejercicios | ver + resolver | crear + editar | gestionar todos |
| Submissions | crear + ver propias | ver todas (su comisión) | ver todas |
| Tutor chat | chatear (rate limited) | — | — |
| Métricas cognitivas | ver propias | ver todas (su comisión) | ver todas |
| Traza cognitiva (CTR) | — | ver (su comisión) | ver todas |
| Risk assessments | — | ver (su comisión) | ver todos |
| Governance events | — | ver reportes | gestionar |
| Tutor system prompts | — | — | gestionar |
| Usuarios | — | — | gestionar |

## Flujo de Interacción entre Actores

```
Alumno                    Sistema                      Docente
  │                         │                            │
  ├─── resuelve ejercicio ──►│                            │
  │    (código, ejecución)   │                            │
  │                         │◄── registra eventos N1-N3   │
  │                         │                            │
  ├─── chatea con tutor ───►│                            │
  │◄── pregunta socrática ──┤                            │
  │                         │◄── registra evento N4       │
  │                         │◄── guardrails check         │
  │                         │                            │
  ├─── envía submission ───►│                            │
  ├─── completa reflexión ──►│                            │
  │                         │                            │
  │                         ├── construye CTR ───────────►│
  │                         ├── calcula métricas ────────►│
  │                         ├── detecta riesgo ─────────►│
  │                         │                            │
  │◄── ve su perfil ────────┤          analiza dashboard ─┤
  │                         │          ve traza cognitiva ─┤
  │                         │          identifica patrones ┤
```
