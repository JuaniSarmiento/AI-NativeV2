## MODIFIED Requirements

### Requirement: LLM-based code-discourse coherence
The code-discourse coherence score SHALL be computed using an LLM evaluation instead of keyword overlap (Jaccard). The LLM SHALL receive the student's chat messages and latest code snapshot and return a coherence score 0-100.

#### Scenario: Session closed with chat and code
- **WHEN** a cognitive session is closed AND the session has chat messages AND code snapshots
- **THEN** the system SHALL call the LLM with a coherence evaluation prompt
- **THEN** the LLM response SHALL be parsed as JSON with `score` (0-100) and `reasoning` fields
- **THEN** the `code_discourse_score` SHALL use the LLM score
- **THEN** the reasoning SHALL be stored in `coherence_anomalies.details.llm_reasoning`

#### Scenario: LLM call fails during coherence computation
- **WHEN** the LLM call raises any exception during code-discourse computation
- **THEN** the system SHALL fall back to the Jaccard keyword overlap method
- **THEN** the system SHALL log a warning with the error details

#### Scenario: Session closed without chat or code
- **WHEN** a session has no chat messages or no code snapshots
- **THEN** `code_discourse_score` SHALL be None (unchanged behavior)

### Requirement: Cross-session inter-iteration coherence
The inter-iteration coherence score SHALL compare the current session's cognitive patterns against the student's last 5 closed sessions, measuring whether the student maintains or improves good practices across exercises.

#### Scenario: Student has 5+ prior sessions
- **WHEN** a session is closed AND the student has 5 or more prior closed sessions
- **THEN** the system SHALL fetch the last 5 closed sessions' pattern summaries
- **THEN** the system SHALL compare current session patterns (N1 ratio, N3 ratio, exploratory prompt ratio, post-tutor verification) against historical mean
- **THEN** a high score (>70) SHALL indicate maintained or improved practices
- **THEN** a low score (<40) SHALL indicate regression

#### Scenario: Student has fewer than 5 prior sessions
- **WHEN** a session is closed AND the student has 1-4 prior closed sessions
- **THEN** the system SHALL use all available prior sessions for comparison

#### Scenario: Student's first session
- **WHEN** a session is closed AND the student has no prior closed sessions
- **THEN** `inter_iteration_score` SHALL be None

### Requirement: Qe composite with N1-N4 covariación
The epistemic quality score (Qe) SHALL incorporate contributions from all 4 cognitive levels, not only N4-derived sub-scores.

#### Scenario: Session with activity across all levels
- **WHEN** a session is closed with events at N1, N2, N3, and N4 levels
- **THEN** Qe SHALL be computed as a weighted average of 4 components:
  - Qe_N1: based on reading time adequacy and problem re-reads
  - Qe_N2: based on evidence of planning (pseudocode or planning comments)
  - Qe_N3: based on post-tutor verification runs and manual test cases
  - Qe_N4: based on existing sub-scores (quality_prompt, critical_evaluation, integration, verification)
- **THEN** weights SHALL come from the rubric YAML configuration

#### Scenario: Session with no N1 or N2 activity
- **WHEN** a session has no N1 events and no N2 events
- **THEN** Qe_N1 and Qe_N2 SHALL be 0 (not None)
- **THEN** these zero values SHALL lower the overall Qe score, reflecting incomplete epistemic quality

#### Scenario: Session with only tutor interaction
- **WHEN** a session only has N4 events (tutor questions) with no N1, N2, or N3 activity
- **THEN** Qe SHALL be low, reflecting pure delegation without comprehension, planning, or verification
