## MODIFIED Requirements

### Requirement: Independent N1 comprehension scoring
The MetricsEngine SHALL compute N1 as an independent measure of comprehension presence and depth. N1 score SHALL NOT use total_events as denominator. Factors: presence of reads_problem, time before first code event (min_engagement_seconds from rubric), evidence of reformulation in N1-level tutor questions.

#### Scenario: Student reads problem and engages before coding
- **WHEN** a session has reads_problem event, >10s gap before first code.run, and N1-level tutor questions
- **THEN** N1 score SHALL be >= 70

#### Scenario: Student jumps directly to coding
- **WHEN** a session has no reads_problem event and first event is code.run
- **THEN** N1 score SHALL be <= 20

### Requirement: Independent N2 strategy scoring
The MetricsEngine SHALL compute N2 as an independent measure of strategic planning. Factors: presence of N2-level tutor questions before code.run, evidence of structure selection, deliberate planning before implementation.

#### Scenario: Student plans before implementing
- **WHEN** a session has N2-level tutor questions followed by code.run events
- **THEN** N2 score SHALL be >= 60

#### Scenario: No strategy evidence
- **WHEN** a session has only code.run and submission events with no N2 signals
- **THEN** N2 score SHALL be <= 20

### Requirement: Independent N3 validation scoring
The MetricsEngine SHALL compute N3 as an independent measure of validation quality. Factors: number of run→fix→run cycles, convergence (errors decreasing), presence of correction after errors.

#### Scenario: Iterative validation with convergence
- **WHEN** a session has 3+ code.run events with error count decreasing across iterations
- **THEN** N3 score SHALL be >= 70

#### Scenario: Single run with no correction
- **WHEN** a session has exactly 1 code.run event
- **THEN** N3 score SHALL be <= 30

### Requirement: Independent N4 AI interaction scoring
The MetricsEngine SHALL compute N4 based on prompt_type distribution and dependency_score. Dominance of exploratory+verifier prompts over generative SHALL produce higher N4. High dependency_score SHALL penalize N4.

#### Scenario: Reflective AI usage
- **WHEN** a session has >70% exploratory+verifier prompts and dependency_score < 0.3
- **THEN** N4 score SHALL be >= 70

#### Scenario: Delegative AI usage
- **WHEN** a session has >60% generative prompts and dependency_score > 0.5
- **THEN** N4 score SHALL be <= 30

### Requirement: Reflection score computation
The MetricsEngine SHALL compute reflection_score from reflection.submitted events. Factors: number of fields completed in the reflection (5 fields max), difficulty_perception and confidence_level values present in payload.

#### Scenario: Complete reflection submitted
- **WHEN** a session has a reflection.submitted event with all 5 fields completed
- **THEN** reflection_score SHALL be >= 80

#### Scenario: No reflection submitted
- **WHEN** a session has no reflection.submitted event
- **THEN** reflection_score SHALL be None

### Requirement: Fixed qe_critical_evaluation
The qe_critical_evaluation sub-score SHALL measure code.run events after EACH tutor.response_received event, not only after the last one.

#### Scenario: Runs after multiple tutor responses
- **WHEN** a student has 3 tutor responses and runs code after each one
- **THEN** qe_critical_evaluation SHALL reflect all 3 post-response run counts

### Requirement: Fixed qe_score_max in risk derivation
The _derive_risk_level method SHALL evaluate qe_score against qe_score_max threshold for medium risk level.

#### Scenario: Low Qe triggers medium risk
- **WHEN** all N scores are above 40 but qe_score is below qe_score_max (40)
- **THEN** risk_level SHALL be "medium"

### Requirement: CoherenceEngine integration
MetricsEngine.compute() SHALL accept optional snapshots and chat_messages parameters. When provided, it SHALL invoke CoherenceEngine and include coherence scores in the result.

#### Scenario: Coherence computed at session close
- **WHEN** MetricsEngine.compute() is called with events, snapshots, and chat_messages
- **THEN** the result SHALL include temporal_coherence_score, code_discourse_score, inter_iteration_score, and coherence_anomalies
