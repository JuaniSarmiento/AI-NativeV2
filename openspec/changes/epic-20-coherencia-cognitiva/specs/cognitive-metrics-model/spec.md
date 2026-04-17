## ADDED Requirements

### Requirement: Coherence score columns
The cognitive_metrics table SHALL include three new NULLABLE NUMERIC(5,2) columns: temporal_coherence_score, code_discourse_score, inter_iteration_score.

#### Scenario: Migration adds coherence columns
- **WHEN** the Alembic migration runs
- **THEN** cognitive_metrics SHALL have temporal_coherence_score, code_discourse_score, inter_iteration_score columns (NUMERIC(5,2), NULLABLE)

### Requirement: Coherence anomalies column
The cognitive_metrics table SHALL include a NULLABLE JSONB column coherence_anomalies storing an array of detected anomalies, each with type, description, and evidence_event_ids.

#### Scenario: Anomalies persisted as JSONB
- **WHEN** CoherenceEngine detects anomalies during session close
- **THEN** coherence_anomalies SHALL contain a JSON array like [{"type": "solution_without_comprehension", "description": "...", "evidence_event_ids": ["uuid1", "uuid2"]}]

### Requirement: Prompt type distribution column
The cognitive_metrics table SHALL include a NULLABLE JSONB column prompt_type_distribution storing the count of each prompt type in the session.

#### Scenario: Distribution persisted
- **WHEN** a session is closed with tutor interactions
- **THEN** prompt_type_distribution SHALL contain {"exploratory": N, "verifier": N, "generative": N}

#### Scenario: No tutor interactions
- **WHEN** a session is closed without tutor interactions
- **THEN** prompt_type_distribution SHALL be null
