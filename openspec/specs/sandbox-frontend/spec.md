## ADDED Requirements

### Requirement: Code editor in activity view
The system SHALL provide a code editor (textarea with monospace font) within the student activity view, pre-filled with the exercise's starter_code. The editor SHALL have a "Ejecutar" button.

#### Scenario: Student writes and runs code
- **WHEN** a student types code and clicks "Ejecutar"
- **THEN** the system SHALL send the code to the run endpoint and display results

#### Scenario: Loading state during execution
- **WHEN** code is being executed
- **THEN** the button SHALL show a spinner and be disabled

### Requirement: Output panel with test results
The system SHALL display execution results below the editor: stdout/stderr in a terminal-style panel, and test case results as a list with pass (green) / fail (red) indicators. Hidden test cases show "fail" without revealing expected output.

#### Scenario: All tests pass shows green
- **WHEN** all test cases pass
- **THEN** the panel SHALL show a green success indicator with "Todos los tests pasaron"

#### Scenario: Timeout shows yellow warning
- **WHEN** execution times out
- **THEN** the panel SHALL show a yellow indicator with "Tiempo limite excedido"

#### Scenario: Error shows red with stderr
- **WHEN** code has a runtime error
- **THEN** the panel SHALL show the error in red with the stderr content
