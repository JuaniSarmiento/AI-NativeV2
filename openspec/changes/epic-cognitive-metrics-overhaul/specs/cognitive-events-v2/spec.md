## ADDED Requirements

### Requirement: Emit problem.reading_time event
The frontend SHALL emit a `problem.reading_time` event when the student leaves the problem statement section (switches to code editor, changes tab, or starts typing code). The event payload SHALL include `reading_duration_ms` (time spent focused on problem) and `is_first_read` (boolean).

#### Scenario: Student reads problem for 30 seconds then switches to editor
- **WHEN** student views problem statement for 30000ms then clicks on code editor
- **THEN** system emits `problem.reading_time` with `reading_duration_ms: 30000, is_first_read: true`

#### Scenario: Student returns to problem and reads again
- **WHEN** student returns to problem statement and reads for 15000ms
- **THEN** system emits `problem.reading_time` with `reading_duration_ms: 15000, is_first_read: false`

#### Scenario: Student spends less than 3 seconds
- **WHEN** student views problem for less than 3000ms
- **THEN** system SHALL NOT emit the event (noise threshold)

### Requirement: Emit problem.reread event
The frontend SHALL emit a `problem.reread` event when the student returns to the problem statement section AFTER having at least one `code.snapshot` or `code.run` event in the current session.

#### Scenario: Student rereads after coding
- **WHEN** student has already produced a code.snapshot AND navigates back to problem statement
- **THEN** system emits `problem.reread` with `elapsed_since_first_read_ms` and `code_lines_at_reread`

#### Scenario: Student views problem before any coding
- **WHEN** student views problem statement but has no prior code.snapshot or code.run
- **THEN** system SHALL NOT emit `problem.reread` (this is initial reading, not rereading)

### Requirement: Detect and emit pseudocode.written event
The backend SHALL analyze each `code.snapshot` payload to detect pseudocode patterns. A snapshot qualifies as pseudocode when it contains 3+ consecutive comment lines AND those comments contain control flow keywords OR the comment-to-code ratio exceeds 0.5.

#### Scenario: Student writes structured planning comments
- **WHEN** a code.snapshot contains "# primero buscar el mayor\n# luego recorrer de nuevo\n# comparar con el segundo"
- **THEN** system emits `pseudocode.written` with `pseudocode_content`, `line_count: 3`, and `has_executable_code_below`

#### Scenario: Student writes a single documentation comment
- **WHEN** a code.snapshot contains only "# esta funcion ordena una lista"
- **THEN** system SHALL NOT emit `pseudocode.written` (does not meet 3-line threshold)

#### Scenario: Student writes comments in English
- **WHEN** a code.snapshot contains "# first find max\n# then iterate again\n# compare with second"
- **THEN** system emits `pseudocode.written` (control flow keywords detected in English)

### Requirement: Detect and emit code.accepted_from_tutor event
The system SHALL detect when a student incorporates code from a tutor response into their editor, via frontend clipboard detection AND backend similarity analysis.

#### Scenario: Student copies code block from tutor chat
- **WHEN** student uses clipboard copy on a code block within the tutor chat panel
- **THEN** frontend emits `code.accepted_from_tutor` with `fragment_length`, `tutor_message_id`, `detection_method: "clipboard"`

#### Scenario: Backend detects high similarity between snapshot diff and tutor response
- **WHEN** a new code.snapshot diff has >60% LCS similarity with code blocks from tutor responses in the last 5 minutes AND no clipboard event was emitted for the same content within 30 seconds
- **THEN** backend emits `code.accepted_from_tutor` with `fragment_length`, `tutor_message_id`, `detection_method: "similarity"`, `similarity_score`

#### Scenario: Student types code that happens to be similar to tutor suggestion
- **WHEN** similarity is below 60% threshold
- **THEN** system SHALL NOT emit the event

### Requirement: Detect and emit test.manual_case event
The backend SHALL analyze each `code.run` payload to detect when the student wrote their own test cases (assert statements or print statements with values not present in the exercise examples).

#### Scenario: Student writes assert with custom values
- **WHEN** executed code contains `assert segundo_mayor([5,1,8,3]) == 5` and `[5,1,8,3]` is not in the exercise examples
- **THEN** system emits `test.manual_case` with `test_type: "assert"`, `is_edge_case: false`, `values_tested: ["[5,1,8,3]"]`

#### Scenario: Student tests edge case
- **WHEN** executed code contains `assert segundo_mayor([]) == None` or `assert segundo_mayor([1]) == None`
- **THEN** system emits `test.manual_case` with `test_type: "assert"`, `is_edge_case: true`

#### Scenario: Student only runs the example from the problem statement
- **WHEN** executed code only contains values that appear verbatim in the exercise description
- **THEN** system SHALL NOT emit `test.manual_case`

### Requirement: Detect and emit prompt.reformulated event
The backend tutor service SHALL detect when a student rephrases a previous question within 90 seconds with higher specificity, using TF-IDF cosine similarity with threshold 0.4.

#### Scenario: Student reformulates a vague question
- **WHEN** student sends "como ordeno una lista" followed by "como ordeno una lista de diccionarios por el campo edad" within 90 seconds
- **THEN** system emits `prompt.reformulated` with `original_message_id`, `similarity_score`, `added_specificity: true`

#### Scenario: Student asks unrelated follow-up
- **WHEN** student sends "como ordeno una lista" followed by "que es un diccionario" within 90 seconds
- **THEN** system SHALL NOT emit (similarity below 0.4 threshold)

#### Scenario: Student repeats exact same question
- **WHEN** student sends identical message within 90 seconds
- **THEN** system SHALL NOT emit (similarity is 1.0 but no added specificity — this is repetition, not reformulation)

### Requirement: All new events include n4_level classification
Each new event type SHALL be registered in the CognitiveEventClassifier with a fixed n4_level assignment.

#### Scenario: Event classification mapping
- **WHEN** the classifier processes any new event type
- **THEN** it assigns: `problem.reading_time` → N1, `problem.reread` → N1, `pseudocode.written` → N2, `code.accepted_from_tutor` → N4, `test.manual_case` → N3, `prompt.reformulated` → N4
