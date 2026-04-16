## ADDED Requirements

### Requirement: Evaluation function E = f(N1, N2, N3, N4, Qe)
The system SHALL implement an evaluation function that combines N1-N4 scores and Qe into a multidimensional profile. The function SHALL use configurable weights loaded from `rubrics/n4_anexo_b.yaml`. The result SHALL be stored as JSONB in `cognitive_sessions.n4_final_score`, NOT in `cognitive_metrics`.

#### Scenario: Evaluation with default weights
- **WHEN** a session closes with N1=70, N2=65, N3=80, N4=50, Qe=72
- **THEN** `n4_final_score` SHALL contain a JSONB object with individual scores, weighted_total, weights used, risk_level, and computed_at timestamp

#### Scenario: Weights sum validation
- **WHEN** rubric weights are loaded
- **THEN** the sum of all weights SHALL equal 1.0 (tolerance 0.001)

### Requirement: Qe (epistemic quality) computation
The system SHALL compute `qe_score` as a weighted average of 4 sub-dimensions: `qe_quality_prompt` (quality of tutor questions — N4 classification ≥ N2 is good), `qe_critical_evaluation` (presence of N3 events post-tutor response), `qe_integration` (ratio of successful code executions post-tutor help), `qe_verification` (presence of code.run after changes). Each sub-score ranges 0.00-100.00 NUMERIC(5,2).

#### Scenario: Student who verifies after tutor help
- **WHEN** a session shows tutor.response_received followed by code.run events
- **THEN** `qe_verification` SHALL be > 0 and `qe_integration` SHALL reflect success rate

#### Scenario: Student who never verifies
- **WHEN** a session has tutor interactions but no subsequent code.run events
- **THEN** `qe_verification` SHALL be 0.00

### Requirement: Rubric file n4_anexo_b.yaml
The system SHALL load scoring configuration from `rubrics/n4_anexo_b.yaml`. The file SHALL define: weights for E function components, thresholds for risk level derivation, and quality factors for each N-level scoring. The file SHALL be loaded at service initialization (not per-request).

#### Scenario: Rubric file missing
- **WHEN** the rubric file does not exist at startup
- **THEN** the system SHALL use hardcoded default weights and log a warning

#### Scenario: Rubric file present
- **WHEN** the rubric file exists and is valid YAML
- **THEN** the MetricsEngine SHALL use the configured weights for all computations

### Requirement: MetricsEngine is pure computation
The `MetricsEngine` service SHALL be a pure computation layer — it receives session data and events as input and returns computed metrics as output. It SHALL NOT perform any database I/O. The caller is responsible for persisting results.

#### Scenario: MetricsEngine testability
- **WHEN** MetricsEngine.compute() is called with a list of CognitiveEvent objects
- **THEN** it returns metrics without requiring a database session or any I/O
