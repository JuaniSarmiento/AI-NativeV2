## 1. ContextBuilder Service

- [x] 1.1 Create `app/features/tutor/context_builder.py` with ContextBuilder class that receives AsyncSession and composes full prompt from exercise metadata + student code + base prompt
- [x] 1.2 Add `get_latest_snapshot` method to a new or existing repository that queries CodeSnapshot by (student_id, exercise_id) ordered by snapshot_at DESC LIMIT 1
- [x] 1.3 Implement exercise loading in ContextBuilder: query Exercise by ID with selectinload for activity relationship
- [x] 1.4 Implement context truncation: student code max 2000 chars, history max 10 messages
- [x] 1.5 Implement activity context inclusion when exercise.activity_id is not null

## 2. System Prompt v2

- [x] 2.1 Create socratic tutor v2 prompt template with placeholders: exercise_title, exercise_description, exercise_difficulty, exercise_topics, exercise_language, exercise_rubric, student_code
- [x] 2.2 Update `seed.py` to seed v2 prompt with SHA-256 hash, deactivate v1 on seed
- [x] 2.3 Add guardrails_config default values to v2 prompt seed: `{"max_code_lines": 5}`

## 3. GuardrailsProcessor Service

- [x] 3.1 Create `app/features/tutor/guardrails.py` with GuardrailsProcessor class
- [x] 3.2 Implement `excessive_code` detection: count total lines across all fenced code blocks, flag if > threshold (default 5, configurable via guardrails_config)
- [x] 3.3 Implement `direct_solution` detection: detect complete function/class definitions inside code blocks
- [x] 3.4 Implement `non_socratic` detection: flag responses with code but no interrogative sentences
- [x] 3.5 Implement corrective message generation per violation type
- [x] 3.6 Implement guardrails_config threshold loading from TutorSystemPrompt.guardrails_config JSONB

## 4. Service Integration

- [x] 4.1 Modify TutorService.__init__ to accept ContextBuilder as dependency
- [x] 4.2 Modify TutorService.chat() to call ContextBuilder before LLM (replace raw prompt with composed prompt)
- [x] 4.3 Modify TutorService.chat() to call GuardrailsProcessor after stream completes
- [x] 4.4 Add guardrail violation result to chat() return value (yield corrective message if violation)
- [x] 4.5 Emit `guardrail.triggered` EventOutbox when violation detected with payload: interaction_id, student_id, exercise_id, session_id, violation_type, violation_details, timestamp

## 5. WebSocket Protocol Update

- [x] 5.1 Add `ChatGuardrailOut` schema to `schemas.py` with type="chat.guardrail", violation_type, corrective_message
- [x] 5.2 Update router.py to send ChatGuardrailOut after chat.done if violation detected
- [x] 5.3 Update router.py to instantiate ContextBuilder and pass to TutorService

## 6. Frontend Guardrail Message

- [x] 6.1 Add `chat.guardrail` message type to the WS message discriminated union in store.ts
- [x] 6.2 Render guardrail corrective messages in ChatMessage.tsx with differentiated style (warning border, distinct background)

## 7. Tests

- [x] 7.1 Unit tests for ContextBuilder: with rubric, without rubric, no snapshot, empty starter_code, with activity, truncation
- [x] 7.2 Unit tests for GuardrailsProcessor: excessive code (>5 lines, <=5 lines, multiple blocks), direct solution, non-socratic, configurable thresholds
- [x] 7.3 Integration test for TutorService.chat() with ContextBuilder and GuardrailsProcessor wired
- [x] 7.4 20+ adversarial tests: jailbreak attempts, "dame la solucion", "escribi el codigo completo", "ignora las instrucciones", code injection in message, solution request in English, indirect solution requests
