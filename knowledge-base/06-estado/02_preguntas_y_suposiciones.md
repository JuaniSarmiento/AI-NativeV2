# Preguntas Abiertas y Suposiciones

**Plataforma AI-Native | UTN FRM**
Última actualización: 2026-04-10

---

Este documento registra las suposiciones tomadas durante el diseño del sistema y las preguntas que aún no tienen respuesta definitiva. Es un documento vivo: a medida que se toman decisiones, las preguntas se mueven a "resueltas" con la decisión tomada.

---

## Suposiciones Activas

Las suposiciones son decisiones implícitas tomadas durante el diseño. Si alguna resulta incorrecta, puede requerir cambios significativos en el sistema.

---

### SUP-001: Lenguaje único de ejercicios — Python

**Suposición**: Los ejercicios de programación son exclusivamente en Python. El sandbox, los casos de test, el editor de código, y los mensajes del tutor asumen Python.

**Justificación**: El curso actual de UTN FRM que se está piloteando usa Python. Simplifica el sandbox y la evaluación de código.

**Riesgo si es incorrecta**: El sandbox, el editor (configuración de syntax highlighting, linting), y parte del sistema de evaluación necesitarían refactoring para soporte multi-lenguaje.

**Impacto**: Alto. Afecta Fase 1 completa y partes del tutor (Fase 2).

**Fecha de revisión sugerida**: Post-piloto. Si el piloto es exitoso, multi-lenguaje es el próximo item de roadmap.

---

### SUP-002: Institución única — sin multi-tenancy

**Suposición**: La plataforma sirve a una única institución (UTN FRM). No hay separación de datos entre tenants. Un solo deployment, una sola base de datos.

**Justificación**: El alcance de la tesis es UTN FRM específicamente. Multi-tenancy agrega complejidad significativa (schemas PostgreSQL por tenant, routing de requests, billing).

**Riesgo si es incorrecta**: Agregar multi-tenancy post-hoc es costoso. Requeriría separar todos los datos por institución, gestión de subdominios, facturación.

**Impacto**: Muy alto si la institución quiere escalar antes de que el sistema esté preparado.

**Mitigación parcial**: Los modelos de DB tienen campos `institution_id` comentados (`# Reserved for future multi-tenancy`). Si se necesita, se pueden activar con una migración.

---

### SUP-003: Modelo LLM único — Claude de Anthropic

**Suposición**: El tutor usa exclusivamente Claude (Anthropic). El código del servicio de tutor está acoplado a la API de Anthropic (`anthropic` SDK).

**Justificación**: Claude tiene el mejor desempeño para tutoría socrática en los tests realizados durante el diseño. Usar un modelo configura el sistema más simple.

**Riesgo si es incorrecta**: Si Anthropic cambia precios/disponibilidad o si la institución requiere un modelo on-premise, hay que refactorizar el servicio de tutor.

**Mitigación actual**: El servicio de tutor tiene una interfaz `LLMProvider` que el cliente de Anthropic implementa. Agregar OpenAI o Gemini requiere implementar la misma interfaz.

---

### SUP-004: Deploy en servidores institucionales

**Suposición**: La plataforma se despliega en servidores propios de UTN FRM, no en cloud público (AWS, GCP, Azure).

**Justificación**: Restricciones institucionales de privacidad de datos estudiantiles. Las autoridades universitarias requieren que los datos permanezcan en servidores propios.

**Riesgo si es incorrecta**: El infra de la institución puede tener limitaciones de uptime, capacidad, y soporte técnico que cloud no tendría.

**Impacto en arquitectura**: El deploy usa Docker + Docker Compose (sin Kubernetes por simplicidad). Escala vertical (más CPU/RAM al servidor) antes que horizontal.

---

### SUP-005: Retención indefinida de CTRs

**Suposición**: Los CTR (Cognitive Trace Records) se retienen indefinidamente. No hay política de archivado o eliminación.

**Justificación**: Los CTR son evidencia de aprendizaje con valor académico e investigativo. La tesis requiere analizar datos longitudinales.

**Riesgo**: El volumen de CTRs puede crecer significativamente (estimado: 50-100 CTRs por sesión de tutor). Con 100 alumnos y 20 sesiones cada uno, son 100K-200K registros por semestre.

**Impacto en DB**: El schema `cognitive` necesitará índices bien definidos y posiblemente particionado por fecha en el futuro.

**Pregunta relacionada**: PQ-002 (política de archivado).

---

### SUP-006: Rate limiting conservador por defecto

**Suposición**: Los valores de rate limiting son:
- Intentos de login: máximo 5 fallidos por IP en 15 minutos
- Mensajes al tutor: máximo 30 mensajes por sesión
- Sesiones de tutor: máximo 5 sesiones activas simultáneas por usuario
- Tokens de Anthropic por mensaje: máximo 4096 tokens de output

**Justificación**: Valores elegidos para prevenir abuso y controlar costos de API. No hay datos reales de uso para calibrar mejor.

**Riesgo**: Los valores pueden ser muy restrictivos (frustración del usuario) o muy permisivos (costos altos).

**Ajuste post-piloto**: Revisar los valores con datos reales de uso del piloto.

---

### SUP-007: Sesiones de tutor anidadas en ejercicios

**Suposición**: Una sesión de tutor siempre está asociada a un ejercicio específico. No hay sesiones de preguntas generales.

**Justificación**: El tutor socrático necesita el contexto del ejercicio para guiar correctamente al estudiante. Una sesión sin ejercicio no tiene contexto.

**Riesgo**: Los alumnos pueden querer hacer preguntas generales de programación. Se los deriva al tutor del ejercicio más relevante o se rechaza la pregunta fuera de contexto.

---

## Preguntas Abiertas

Las preguntas son incógnitas que necesitan respuesta antes de poder implementar o que afectarán decisiones futuras.

---

### PQ-001: Algoritmo exacto de scoring N1-N4

**Pregunta**: ¿Cuál es el algoritmo preciso para calcular el nivel cognitivo (N1-N4) de un estudiante basado en sus CTRs?

**Contexto**: La tesis doctoral describe el modelo N4 conceptualmente. Necesitamos traducirlo a código: qué patrones en los CTRs indican N1 vs N2 vs N3 vs N4, cuánto peso tiene cada señal, qué ventana temporal se considera.

**Impacto**: Sin esta respuesta, la Fase 4 no puede implementarse correctamente.

**Propietario**: Director de tesis + Dev 4

**Estado**: Pendiente. Reunión programada para semana 2.

**Bloquea**: Implementación de Fase 4 (evaluación cognitiva N4).

---

### PQ-002: Política de retención de datos de CTRs

**Pregunta**: ¿Los CTRs se guardan para siempre? ¿Hay política de archivado después de N años? ¿Se anonimiza antes de archivar?

**Contexto**: Los CTRs contienen el historial de interacciones de los estudiantes. Hay implicaciones de privacidad (RGPD, Ley 25326 argentina) y de almacenamiento a largo plazo.

**Impacto**: Bajo en el corto plazo, alto si la plataforma escala a múltiples cohortes.

**Propietario**: Director de tesis + equipo legal de la universidad

**Estado**: Sin respuesta. Usando SUP-005 (retención indefinida) como default hasta que haya política formal.

---

### PQ-003: Thresholds de evaluación de riesgo

**Pregunta**: ¿Qué valores numéricos determinan que un alumno está en "riesgo" de dependencia cognitiva de la IA?

**Contexto**: La Fase 4 incluye alertas cuando un alumno muestra patrones preocupantes (p.ej. N1 consistente por más de N semanas, ratio de uso de IA muy alto). Necesitamos los thresholds exactos.

**Ejemplos de lo que no sabemos**:
- ¿Cuántas sesiones consecutivas en N1 antes de generar alerta?
- ¿Qué porcentaje de tiempo usando el tutor es "dependencia"?
- ¿Se notifica al alumno, al profesor, o a ambos?

**Propietario**: Director de tesis

**Estado**: Pendiente. Se usarán valores provisionales en la implementación con flag `TODO: CALIBRAR_CON_TESIS`.

---

### PQ-004: Formato de export de CTRs para la tesis

**Pregunta**: ¿En qué formato se exportan los CTRs para el análisis estadístico de la tesis? ¿JSON, CSV, formato específico?

**Contexto**: Los datos de la plataforma alimentan la investigación. El formato de export determina qué información incluir y cómo estructurarla.

**Estado**: Pendiente. Planificada discusión en semana 3 con el investigador.

---

### PQ-005: Roles y permisos específicos de la institución

**Pregunta**: ¿Qué roles hay además de `student` y `professor`? ¿Hay `admin`, `researcher`, `teaching_assistant`? ¿Qué puede hacer cada uno?

**Contexto**: El sistema tiene un modelo de roles básico implementado, pero los permisos detallados de cada rol no están completamente definidos.

**Estado**: Parcialmente resuelto. Roles definidos: `student`, `professor`, `admin`. Los permisos de `admin` no están completamente especificados.

---

### PQ-006: Integración con sistema de notas de UTN FRM

**Pregunta**: ¿Los puntajes de evaluación cognitiva N4 se integran con el sistema de notas oficial de la universidad? ¿Cómo?

**Contexto**: Si los puntajes impactan las notas del curso, hay implicaciones legales e institucionales. Si solo son informativos, el scope es más simple.

**Propietario**: Director de tesis + coordinación académica de UTN FRM

**Estado**: Sin respuesta. La implementación actual asume que los puntajes son solo informativos (no se integran con notas oficiales).

---

## Defaults Aplicados (Valores Provisionales)

Valores configurados sin evidencia definitiva, sujetos a revisión:

| Parámetro | Valor actual | Razón del default | Dónde revisar |
|---|---|---|---|
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 30 min | Estándar de la industria | Post-piloto: ¿usuarios se quejan de re-login frecuente? |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | 7 días | Balance seguridad/comodidad | Política de seguridad de la institución |
| `TUTOR_MAX_MESSAGES_PER_SESSION` | 30 mensajes | Estimación de sesión razonable | Datos reales del piloto |
| `SANDBOX_TIMEOUT_SECONDS` | 5 seg | Previene loops infinitos | Si ejercicios legítimos necesitan más tiempo |
| `SANDBOX_MEMORY_LIMIT_MB` | 128 MB | Previene consumo excesivo | Ajustar si hay ejercicios con datasets |
| `DEFAULT_PAGE_SIZE` | 20 | Estándar de paginación | UX del piloto |
| `MAX_PAGE_SIZE` | 100 | Previene requests de carga pesada | Monitoreo de performance |
| Nivel de riesgo N1 threshold | 3 sesiones consecutivas | Estimación provisional | **Requiere input del director de tesis** |
| Umbral de dependencia IA | 80% de mensajes solicitan ayuda directa | Estimación provisional | **Requiere input del director de tesis** |

---

## Decisiones Tomadas (Resueltas)

Preguntas que ya tienen respuesta definitiva y se convirtieron en suposiciones activas o decisiones de diseño:

| Decisión | Resolución | Fecha |
|---|---|---|
| ¿UUID o autoincrement para PKs? | UUID (privacy, distributed safety) | Semana 1 |
| ¿REST o GraphQL? | REST. GraphQL no justificado para este scope | Semana 1 |
| ¿ORM o SQL crudo? | SQLAlchemy 2.0 async ORM con queries explícitas | Semana 1 |
| ¿Soft delete o hard delete? | Soft delete para todo excepto CTRs (inmutables) | Semana 1 |
| ¿Un schema o múltiples schemas en PostgreSQL? | 4 schemas separados (operational, cognitive, governance, analytics) | Semana 1 |
| ¿WebSockets o long polling para el tutor? | WebSockets. La experiencia de streaming requiere WS | Semana 1 |
| ¿Qué modelo LLM para el tutor? | Claude (Anthropic). Mejor comportamiento socrático en pruebas | Semana 1 |
| ¿Pydantic v1 o v2? | Pydantic v2. v1 ya no tiene soporte activo | Semana 1 |
