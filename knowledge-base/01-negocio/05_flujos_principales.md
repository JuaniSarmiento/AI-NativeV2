# Flujos Principales

## Flujo 1: Alumno Resuelve Ejercicio (End-to-End)

Este es el flujo central del sistema. Involucra las 4 fases y produce un CTR completo.

```
1.  Alumno se loguea ─────────────────────────────── [Auth — Fase 0]
2.  Ve su dashboard (cursos, ejercicios) ─────────── [Frontend — Fase 4]
3.  Selecciona ejercicio de "Condicionales" ──────── [Fase 4 → GET ejercicio Fase 1]
4.  Se inicia sesión cognitiva ───────────────────── [Fase 4 → POST /cognitive/sessions/start Fase 3]
5.  Lee el enunciado ─────────────────────────────── [Frontend emite evento 'reads_problem' → Fase 3, N1]
6.  Escribe código en Monaco Editor ──────────────── [Cada 30s → POST /snapshots Fase 1]
7.  Click "Ejecutar" → código al sandbox ─────────── [Fase 4 → POST /run Fase 1]
    └─ Resultado en panel output ──────────────────── [Fase 3 recibe evento ejecución → N3]
8.  Test falla → abre chat del tutor ─────────────── [Fase 4 → WS Fase 2]
    ├─ "¿Por qué mi función no retorna lo correcto?"
    └─ Tutor responde con pregunta socrática ──────── [Fase 3 recibe evento interacción → N4 critical]
9.  Alumno modifica código → ejecuta → pasa tests ── [N3]
10. Click "Enviar" ───────────────────────────────── [Fase 4 → POST /submit Fase 1]
11. Se cierra sesión cognitiva ───────────────────── [Fase 3]
12. Formulario de reflexión ──────────────────────── [Fase 4 → POST /reflection Fase 2]
    └─ Fase 3 recibe evento metacognición
13. Fase 3 calcula métricas:
    ├─ N1=0.7, N2=0.6, N3=0.9, N4=0.8
    ├─ Qe=0.75, dependency=0.2
    └─ CTR con hash chain válido
14. Docente ve dashboard actualizado ─────────────── [Fase 4 → GET /dashboard Fase 3]
    └─ Radar chart N1-N4 del alumno
```

### Detalle del Event Bus (paso 5-12)

Cada acción del alumno genera un evento interno que Fase 3 consume:

| Acción del alumno | Fase origen | Evento emitido | Clasificación N4 |
|-------------------|-------------|----------------|------------------|
| Lee enunciado | Fase 4 | `reads_problem` | N1 |
| Reformula en chat | Fase 2 | `reformulates_problem` | N1 |
| Pide aclaración al tutor | Fase 2 | `asks_clarification` | N1 |
| Define estrategia (cambia approach) | Fase 4 | `defines_strategy` | N2 |
| Cambia de estrategia | Fase 4 | `changes_strategy` | N2 |
| Pide hint al tutor | Fase 2 | `asks_hint` | N2 |
| Ejecuta código | Fase 1 | `runs_test` | N3 |
| Interpreta error (edita post-error) | Fase 4 | `interprets_error` | N3 |
| Corrige error | Fase 4 | `fixes_error` | N3 |
| Pide explicación al tutor | Fase 2 | `asks_explanation` | N4 |
| Audita sugerencia del tutor | Fase 2 | `audits_ai_suggestion` | N4 |

---

## Flujo 2: Diálogo con el Tutor Socrático

Flujo detallado de una interacción alumno-tutor con guardrails.

```
Alumno envía mensaje ──► Pre-procesador
                          ├─ Normaliza input
                          ├─ Detecta idioma
                          └─ Extrae contexto (ejercicio, código, historial)
                              │
                              ▼
                         Constructor de contexto
                          ├─ System prompt socrático (versionado, con SHA-256)
                          ├─ Enunciado del ejercicio
                          ├─ Código actual del alumno
                          ├─ Historial (últimos N turnos)
                          └─ Restricciones pedagógicas
                              │
                              ▼
                         Cliente LLM (Anthropic API)
                          ├─ Streaming de respuesta
                          └─ Token por token via WebSocket
                              │
                              ▼
                         Post-procesador / Guardrails
                          ├─ ¿Contiene bloques de código > 5 líneas? → reformular
                          ├─ ¿Es solución completa? → reformular
                          ├─ ¿Viola políticas socráticas? → reformular
                          │
                          ├─ Si OK → enviar al alumno
                          └─ Si violación → reformular + governance_event
                              │
                              ▼
                         Registrador de interacción
                          ├─ Persiste en tutor_interactions
                          ├─ classification_n4: critical | exploratory | dependent
                          ├─ policy_check_result: ok | violation_detected | reformulated
                          └─ prompt_hash: SHA-256 del system prompt usado
                              │
                              ▼
                         Event Bus → Fase 3 (evento N4)
```

### Ejemplo canónico: Bug n/2==0 vs n%2==0

(Preservado del documento original tutorSocratico.docx como caso de referencia)

> **Ejercicio**: Escribí una función `sumar_pares(lista)` que devuelva la suma de los números pares.
>
> **Código del alumno**: `if n / 2 == 0:` (error: usa división en vez de módulo)
>
> **Tutor**: "¿Qué condición estás usando para decidir si un número es par?"
> **Alumno**: "Estoy usando n / 2 == 0"
> **Tutor**: "Si n vale 4, ¿cuánto da 4 / 2? ¿Ese resultado te ayuda a saber si 4 es par?"
> **Alumno**: "Da 2"
> **Tutor**: "Entonces, ¿tu condición está comprobando si el número es par o si al dividirlo por 2 da cero?"
> **Alumno**: "Ah, está comprobando otra cosa"
> **Tutor**: "Exacto. ¿Qué operación en Python te permite saber si sobra algo al dividir?"
> **Alumno**: "El módulo, %"
> **Tutor**: "Probalo con [1, 2, 3, 4]. ¿Qué resultado esperás obtener?"

---

## Flujo 3: Docente Analiza Dashboard

```
1. Docente se loguea → ve lista de comisiones
2. Selecciona comisión "Programación I — Turno Mañana"
3. Dashboard de curso:
   ├─ Promedio N1-N4 de la comisión (bar chart)
   ├─ Distribución de calidad epistémica (histogram)
   ├─ Alumnos en riesgo (tabla color-coded: high=rojo, medium=amarillo)
   └─ Ejercicios más difíciles (ranking por tasa de abandono)
4. Click en alumno en riesgo alto (dependency):
   ├─ Perfil individual:
   │   ├─ Radar chart N1-N4
   │   ├─ Evolución temporal de scores
   │   ├─ dependency_score: 0.85 (alta dependencia del tutor)
   │   └─ Historial de submissions con scores
   └─ Click en último ejercicio → Traza cognitiva:
       ├─ Timeline visual con eventos color-coded
       │   (N1=azul, N2=verde, N3=naranja, N4=violeta)
       ├─ Código evolutivo con diff entre snapshots
       └─ Chat completo con el tutor (cada turno con clasificación N4)
5. Docente identifica patrón: alumno pregunta solución directa → tutor reformula →
   alumno copia sugerencia sin entender → dependency score alto
6. Acción docente: intervención pedagógica presencial
```

---

## Flujo 4: Construcción del CTR

Flujo interno del Cognitive Trace Engine.

```
Eventos crudos llegan via Event Bus
        │
        ▼
Event Classifier
├─ Clasifica event_type según mapeo canónico
├─ Asigna n4_level (N1/N2/N3/N4)
├─ Enriquece con contexto (ejercicio, timestamp, estado)
└─ Emite cognitive_event
        │
        ▼
CTR Builder
├─ Agrupa eventos por cognitive_session
├─ Calcula hash encadenado:
│   hash(génesis) = SHA256("GENESIS:" + session_id + ":" + started_at.isoformat())
│   hash(n) = SHA256(hash(n-1) + datos(n))
├─ Incrementa sequence_number
└─ Al cierre de sesión:
    ├─ Almacena ctr_hash_chain (hash final)
    ├─ Valida CTR mínimo (≥1 evento por N1-N4)
    └─ Setea is_valid_ctr
        │
        ▼
Cognitive Worker (post-cierre)
├─ Computa scores N1-N4 basados en rúbrica
├─ Computa Qe = f(quality_prompt, critical_evaluation, integration, verification)
├─ Computa dependency_score = ratio de eventos N4 clasificados como "dependent"
├─ Computa reflection_score (basado en evento de reflexión post-ejercicio)
├─ Computa success_efficiency = score / (intentos + tiempo)
└─ Persiste en cognitive_metrics
        │
        ▼
Risk Worker (periódico, por alumno/curso)
├─ Dependencia excesiva: muchas interacciones "dependent" en N4
├─ Desenganche: sesiones abandonadas o muy cortas
├─ Estancamiento: múltiples intentos sin progreso
└─ Persiste en risk_assessments con risk_level
```

---

## Flujo 5: Validación de Integridad del CTR

Flujo de auditoría que puede ejecutarse en cualquier momento.

```
1. Seleccionar cognitive_session por ID
2. Obtener todos los cognitive_events ordenados por sequence_number
3. Recalcular hash chain desde cero:
   ├─ hash_computed(génesis) = SHA256("GENESIS:" + session_id + ":" + started_at.isoformat())
   ├─ hash_computed(n) = SHA256(hash_computed(n-1) + datos(n))
4. Comparar hash_computed(último) con ctr_hash_chain almacenado
5. Si coinciden → CTR íntegro
6. Si difieren → CTR comprometido → governance_event con detalles
```
