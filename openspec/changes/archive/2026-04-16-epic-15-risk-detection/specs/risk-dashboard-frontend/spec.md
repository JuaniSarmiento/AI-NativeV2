## ADDED Requirements

### Requirement: Risk alerts table component
The system SHALL provide a `RiskAlertsTable` component that displays a list of risk assessments for the current commission. Each row SHALL show: student name/ID, risk level (color-coded), risk factors (expanded from JSONB), recommendation, assessed_at, and an "Acknowledge" button. The table SHALL support filtering by risk_level.

#### Scenario: Risk alerts table renders
- **WHEN** the teacher dashboard loads with risk data
- **THEN** a table of risk alerts SHALL be displayed below the existing charts, sorted by risk_level (critical first)

#### Scenario: Color coding
- **WHEN** a risk alert has risk_level "critical"
- **THEN** the row SHALL display with error color tokens (--color-error-600)

#### Scenario: Risk factors display
- **WHEN** a risk alert has risk_factors `{"dependency": {"score": 0.75}, "stagnation": {"score": 0.5}}`
- **THEN** the row SHALL display factor names with their scores as readable labels (e.g., "Dependencia: 0.75, Estancamiento: 0.5")

### Requirement: Acknowledge button
The system SHALL provide an "Acknowledge" button on each risk alert row. Clicking it SHALL call PATCH `/api/v1/teacher/risks/{id}/acknowledge` and update the row to show acknowledged_by and acknowledged_at. Acknowledged rows SHALL have a muted visual style.

#### Scenario: Acknowledge a risk
- **WHEN** a docente clicks "Reconocer" on a risk alert
- **THEN** the system SHALL call the PATCH endpoint, show a check mark, and display the acknowledge timestamp

#### Scenario: Already acknowledged display
- **WHEN** a risk alert has acknowledged_at set
- **THEN** the row SHALL show a muted style with the acknowledge info instead of the button

### Requirement: Risk store actions
The system SHALL extend the teacher dashboard Zustand store with: `risks` (RiskAssessment[]), `isLoadingRisks` (boolean), `fetchRisks(commissionId)`, `acknowledgeRisk(riskId)`, and `triggerAssessment(commissionId)` actions. Store SHALL follow the existing pattern of individual selectors.

#### Scenario: Fetch risks on commission change
- **WHEN** the commission selector changes
- **THEN** `fetchRisks` SHALL be called and `risks` state SHALL update

#### Scenario: Acknowledge updates store
- **WHEN** `acknowledgeRisk` succeeds
- **THEN** the risk in the store SHALL be updated with acknowledged_by and acknowledged_at without refetching the full list

### Requirement: Risk factor labels in Spanish
The system SHALL map factor keys to Spanish labels: "dependency" → "Dependencia", "disengagement" → "Desvinculacion", "stagnation" → "Estancamiento". Unknown factors SHALL display their key name capitalized.

#### Scenario: Known factor label
- **WHEN** rendering risk_factors with key "dependency"
- **THEN** the label SHALL display "Dependencia"

#### Scenario: Unknown factor label
- **WHEN** rendering risk_factors with key "new_factor"
- **THEN** the label SHALL display "New_factor"
