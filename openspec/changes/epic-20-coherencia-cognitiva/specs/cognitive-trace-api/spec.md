## MODIFIED Requirements

### Requirement: TraceResponse returns complete data
The GET /api/v1/cognitive/sessions/{id}/trace endpoint SHALL return a complete TraceResponse with populated timeline, chat, code_evolution, metrics, and verification fields. The router SHALL call CognitiveService.get_trace() which assembles all data.

#### Scenario: Closed session trace returns all sections
- **WHEN** a docente requests the trace for a closed session
- **THEN** the response SHALL include timeline (list of events), chat (list of tutor interactions), code_evolution (list of snapshots with diffs), metrics (cognitive metrics), and verification (hash chain result)

#### Scenario: Open session trace returns available data
- **WHEN** a docente requests the trace for an open session
- **THEN** the response SHALL include timeline and chat (available data), metrics=null, and verification=null

### Requirement: TraceResponse includes coherence data
The TraceResponse SHALL include coherence scores and anomalies when available (session closed and coherence computed).

#### Scenario: Closed session with coherence
- **WHEN** a trace is requested for a closed session with computed coherence
- **THEN** the response SHALL include temporal_coherence_score, code_discourse_score, inter_iteration_score, and coherence_anomalies in the metrics section
