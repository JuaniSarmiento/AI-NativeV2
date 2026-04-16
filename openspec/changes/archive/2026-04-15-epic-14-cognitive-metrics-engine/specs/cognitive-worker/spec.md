## ADDED Requirements

### Requirement: Automatic metrics computation on session close
The system SHALL compute cognitive metrics automatically when a `CognitiveSession` transitions to `closed` status. The computation SHALL happen synchronously within the same database transaction as the session close, ensuring no closed sessions exist without metrics.

#### Scenario: Session closed by submission
- **WHEN** `CognitiveEventConsumer` receives a `submission.created` event and closes the session
- **THEN** a `CognitiveMetrics` row SHALL be created for that session with all scores computed

#### Scenario: Session closed by timeout
- **WHEN** the timeout checker closes a stale session
- **THEN** a `CognitiveMetrics` row SHALL be created for that session

#### Scenario: Session with no events
- **WHEN** a session is closed but has zero `CognitiveEvent` records (only genesis_hash)
- **THEN** all score fields SHALL be NULL, `total_interactions` SHALL be 0, and `risk_level` SHALL be NULL

### Requirement: N1-N4 score computation
The system SHALL compute N1 through N4 scores as NUMERIC(5,2) values in range 0.00-100.00. Scoring SHALL be based on event type distribution and quality factors from the rubric. N1 (comprehension) considers `reads_problem` and `code.snapshot` events. N2 (strategy) considers `submission.created` events with prior `code.run` iterations. N3 (validation) considers `code.run` events with subsequent corrections. N4 (AI interaction) considers `tutor.question_asked` quality via `n4_level` in payload.

#### Scenario: Session with only reads_problem events
- **WHEN** a closed session contains only `reads_problem` events
- **THEN** N1 score SHALL be > 0, and N2/N3/N4 scores SHALL be 0.00

#### Scenario: Deterministic scoring
- **WHEN** the same set of events is scored twice
- **THEN** the resulting N1-N4 scores SHALL be identical

### Requirement: Help-seeking ratio and autonomy index
The system SHALL compute `help_seeking_ratio` as the proportion of tutor interactions to total actions (NUMERIC(4,3), 0.000-1.000). The system SHALL compute `autonomy_index` as `1.0 - help_seeking_ratio`, representing the degree of independent work.

#### Scenario: No tutor interactions
- **WHEN** a session has events but no `tutor.question_asked` events
- **THEN** `help_seeking_ratio` SHALL be 0.000 and `autonomy_index` SHALL be 1.000

#### Scenario: All events are tutor interactions
- **WHEN** every event in the session is `tutor.question_asked` or `tutor.response_received`
- **THEN** `help_seeking_ratio` SHALL approach 1.000

### Requirement: Dependency score computation
The system SHALL compute `dependency_score` as the ratio of N4 events classified as "dependent" (sub_classification in event payload) to total N4 events. Range NUMERIC(4,3), 0.000-1.000.

#### Scenario: No dependent interactions
- **WHEN** all N4 events have sub_classification "exploratory" or "critical"
- **THEN** `dependency_score` SHALL be 0.000

### Requirement: Risk level derivation
The system SHALL derive `risk_level` from computed metrics using these rules in order: (1) critical: dependency_score > 0.7 AND n4_ai_interaction_score < 30; (2) high: dependency_score > 0.5 OR any N-score < 20; (3) medium: any N-score < 40 OR qe_score < 40; (4) low: default.

#### Scenario: High dependency student
- **WHEN** `dependency_score` is 0.75 and `n4_ai_interaction_score` is 25.00
- **THEN** `risk_level` SHALL be "critical"

#### Scenario: Balanced student
- **WHEN** all N-scores are > 60 and `dependency_score` < 0.3 and `qe_score` > 60
- **THEN** `risk_level` SHALL be "low"
