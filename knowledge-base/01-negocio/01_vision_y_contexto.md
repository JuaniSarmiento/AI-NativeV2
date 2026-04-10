# Visión y Contexto

## El Problema

En la enseñanza universitaria de programación, la irrupción de la IA generativa ha roto la relación entre el código que un estudiante entrega y lo que realmente aprendió. Un alumno puede presentar una solución técnica impecable generada por ChatGPT sin haber comprendido el problema. **El código ya no es evidencia confiable de aprendizaje.**

La respuesta institucional típica (prohibir, detectar, sancionar) no resuelve el problema: solo lo desplaza. Lo que se necesita es un cambio de paradigma: **pasar de evaluar productos a observar procesos cognitivos**.

## La Solución: Plataforma AI-Native

Es un sistema pedagógico-tecnológico que integra:

1. **Tutor IA socrático regulado**: guía al alumno sin dar respuestas directas, utilizando preguntas elicitadoras basadas en el método socrático
2. **Registro estructurado del proceso cognitivo (CTR)**: el Cognitive Trace Record captura, organiza y preserva evidencia del proceso de razonamiento del estudiante
3. **Evaluación multidimensional basada en el modelo N4**: cuatro dimensiones para observar cómo piensa un alumno
4. **Marco de gobernanza**: garantiza coherencia entre el modelo teórico doctoral y la implementación técnica

## El Modelo N4

Cuatro dimensiones irreductibles del proceso de resolución en contextos mediados por IA:

| Nivel | Dimensión | Qué observa |
|-------|----------|-------------|
| **N1** | Comprensión del problema | ¿El alumno entiende qué se le pide? Reformulación, identificación de entradas/salidas, casos borde |
| **N2** | Razonamiento estratégico | ¿Diseña una estrategia? Elección de estructuras, justificación de decisiones |
| **N3** | Evaluación y validación | ¿Valida su solución? Ejecución de tests, interpretación de errores, corrección iterativa |
| **N4** | Interacción con IA | ¿Cómo usa la asistencia de IA? Crítico, exploratorio o dependiente |

La incorporación del nivel N4 introduce una dimensión epistemológicamente novedosa: la interacción con la IA deja de ser un factor externo y pasa a ser un **componente constitutivo del proceso de aprendizaje**.

### Función evaluativa formal

```
E = f(N1, N2, N3, N4, Qe)
```

Donde `Qe` (calidad epistémica) es un constructo jerárquico compuesto por:
- Calidad del prompt
- Evaluación crítica de la respuesta de IA
- Integración del conocimiento
- Verificación independiente

Esto reemplaza el modelo tradicional: `E = correctness(output)`

## Calidad Epistémica (Qe)

Constructo jerárquico que evalúa la calidad del acoplamiento cognitivo del estudiante con el proceso de resolución y con la IA. No se permiten métricas aisladas sin integración en este constructo.

| Componente | Qué mide |
|-----------|---------|
| `quality_prompt` | ¿Formula consultas específicas y bien dirigidas? |
| `critical_evaluation` | ¿Evalúa críticamente las respuestas de la IA? |
| `integration` | ¿Integra el conocimiento recibido con su propio razonamiento? |
| `verification` | ¿Verifica independientemente lo que la IA le dice? |

## Cognitive Trace Record (CTR)

El CTR no es un log técnico — es un artefacto interpretativo que contiene:

- Eventos cognitivos clasificados según N1-N4
- Interacciones con la IA (prompts y respuestas)
- Versiones intermedias del código
- Instancias de validación
- Reflexiones del estudiante

### Propiedades del CTR

- **Inmutable post-cierre**: hash encadenado `hash(n) = SHA256(hash(n-1) + datos(n))`
- **Auditable**: cada evento tiene hash, timestamp, contexto
- **Interpretable pedagógicamente**: todo dato puede ser interpretado en términos de aprendizaje
- **Mínimo viable**: al menos 1 evento por cada N1-N4 por episodio

## Indicador Cruzado Código↔Discurso

Salvaguarda contra performatividad: un estudiante que dice lo que el tutor quiere oír sin comprender. El sistema computa un indicador cruzado: cada afirmación conceptual del estudiante en el diálogo socrático debe encontrar correlato en una modificación coherente del código dentro de la misma ventana temporal, y viceversa. **El diálogo, por sí solo, no constituye evidencia suficiente.**

## Contexto Institucional

- **Institución**: Universidad Tecnológica Nacional — Facultad Regional Mendoza
- **Origen académico**: Tesis doctoral del Dr. Alberto Cortez
- **Documento maestro**: empate3.docx (Documento Maestro de Unificación Conceptual)
- **Principio rector**: todo componente técnico debe poder justificar su existencia mediante una referencia explícita a un constructo teórico, una función pedagógica o una exigencia de gobernanza definida en la tesis

## Principios de Herencia Semántica (empate3)

1. **Subordinación técnica**: la arquitectura depende del modelo, no al revés
2. **No degradación semántica**: ningún concepto teórico puede simplificarse al punto de perder su significado en la implementación
3. **Trazabilidad semántica**: todo dato almacenado debe poder ser interpretado pedagógicamente
4. **Coherencia evaluativa**: toda evaluación debe derivarse del modelo N4 o de la calidad epistémica
5. **Integración IA**: la IA no es externa al sistema — es parte del fenómeno evaluado

## Resultado Esperado

Una plataforma web donde:
- El alumno resuelve ejercicios de programación asistido por un tutor IA socrático
- El sistema registra todo su proceso cognitivo en un CTR inmutable y auditable
- El docente accede a un dashboard con el perfil cognitivo de cada alumno: patrones de razonamiento, nivel de dependencia de la IA, métricas de calidad epistémica
- Todo trazable, auditable y alineado con el modelo teórico de la tesis doctoral

En una frase: **el sistema no solo enseña a programar. Hace visible, medible y defendible el acto de aprender.**
