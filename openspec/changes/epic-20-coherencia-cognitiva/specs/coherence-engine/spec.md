## ADDED Requirements

### Requirement: Temporal coherence analysis
The CoherenceEngine SHALL analyze the sequence of N-level events in a closed session and produce a temporal_coherence_score (0-100). It SHALL detect anomalies where cognitive levels appear in sequences that are not coherent (e.g., N3 validation without prior N1 comprehension or N2 strategy).

#### Scenario: Normal sequence produces high score
- **WHEN** a session has events in order: reads_problem(N1) → tutor.question_asked(N2) → code.run(N3) → submission.created(N2)
- **THEN** temporal_coherence_score SHALL be >= 70

#### Scenario: Solution without comprehension detected
- **WHEN** a session has code.run and submission.created events but zero reads_problem or N1-level tutor events
- **THEN** temporal_coherence_score SHALL be <= 30 AND anomalies SHALL include type "solution_without_comprehension"

#### Scenario: Pure delegation detected
- **WHEN** a session has >80% of events as tutor.question_asked/tutor.response_received with no N1/N2/N3 events between them
- **THEN** temporal_coherence_score SHALL be <= 40 AND anomalies SHALL include type "pure_delegation"

### Requirement: Code-discourse coherence analysis
The CoherenceEngine SHALL cross-reference chat message content with subsequent code snapshot diffs and produce a code_discourse_score (0-100).

#### Scenario: Discourse matches code changes
- **WHEN** a student discusses "recursión" in tutor chat AND the subsequent code diff adds a recursive function
- **THEN** code_discourse_score SHALL be >= 60

#### Scenario: Discourse does not match code changes
- **WHEN** a student discusses strategy in tutor chat but no code changes follow within the session
- **THEN** code_discourse_score SHALL be <= 40

#### Scenario: No chat in session
- **WHEN** a session has zero tutor interactions
- **THEN** code_discourse_score SHALL be None (not applicable)

### Requirement: Inter-iteration consistency analysis
The CoherenceEngine SHALL analyze successive code snapshots for trajectory coherence and produce an inter_iteration_score (0-100). It SHALL detect possible external code integration.

#### Scenario: Gradual code evolution
- **WHEN** code snapshots show incremental changes (<20 net lines each) with preceding code.run or tutor events
- **THEN** inter_iteration_score SHALL be >= 70

#### Scenario: Massive code jump detected
- **WHEN** a code snapshot has a diff of >50 net added lines AND there were no N1/N2/N3 events in the preceding 5 minutes
- **THEN** inter_iteration_score SHALL be <= 40 AND anomalies SHALL include type "possible_external_integration"

#### Scenario: No snapshots in session
- **WHEN** a session has zero code.snapshot events
- **THEN** inter_iteration_score SHALL be None (not applicable)

### Requirement: Anomaly evidence trail
Each anomaly detected by the CoherenceEngine SHALL include the event_ids of the evidence events that triggered the detection, enabling full auditability.

#### Scenario: Anomaly has evidence
- **WHEN** an anomaly of type "solution_without_comprehension" is detected
- **THEN** the anomaly record SHALL contain type, description, and a list of event_ids that constitute the evidence

### Requirement: CoherenceEngine is pure Python
The CoherenceEngine SHALL have zero database I/O and zero FastAPI imports. It SHALL receive pre-loaded data as input and return a CoherenceResult dataclass.

#### Scenario: Engine computes without I/O
- **WHEN** CoherenceEngine.compute() is called with lists of events, snapshots, and chat messages
- **THEN** it SHALL return a CoherenceResult without making any database or network calls
