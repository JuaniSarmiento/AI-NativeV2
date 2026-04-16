## ADDED Requirements

### Requirement: List risks by commission endpoint
The system SHALL provide `GET /api/v1/teacher/commissions/{commission_id}/risks` returning paginated risk assessments for a commission. Requires role docente or admin. Query params: `page` (default 1), `per_page` (default 20, max 100), `risk_level` (optional filter). Response SHALL follow the standard envelope format `{ status, data, meta, errors }`.

#### Scenario: Successful list with pagination
- **WHEN** a docente calls GET `/api/v1/teacher/commissions/{commission_id}/risks?page=1&per_page=10`
- **THEN** the system SHALL return status 200 with `data` containing a list of RiskAssessmentResponse objects and `meta` with pagination fields

#### Scenario: Filter by risk level
- **WHEN** a docente calls GET `/api/v1/teacher/commissions/{commission_id}/risks?risk_level=critical`
- **THEN** the system SHALL return only assessments with risk_level "critical"

#### Scenario: Unauthorized access
- **WHEN** an alumno calls this endpoint
- **THEN** the system SHALL return 403 Forbidden

### Requirement: Student risk history endpoint
The system SHALL provide `GET /api/v1/teacher/students/{student_id}/risks` returning paginated risk assessment history for a student. Requires role docente or admin. Query params: `page`, `per_page`, `commission_id` (optional filter).

#### Scenario: Full history
- **WHEN** a docente calls GET `/api/v1/teacher/students/{student_id}/risks`
- **THEN** the system SHALL return all risk assessments for that student ordered by assessed_at DESC

#### Scenario: Filter by commission
- **WHEN** a docente calls GET `/api/v1/teacher/students/{student_id}/risks?commission_id={id}`
- **THEN** the system SHALL return only assessments for that commission

### Requirement: Acknowledge risk endpoint
The system SHALL provide `PATCH /api/v1/teacher/risks/{risk_id}/acknowledge` that sets `acknowledged_by` to the current user's ID and `acknowledged_at` to now(). Requires role docente or admin. The endpoint SHALL return the updated RiskAssessmentResponse.

#### Scenario: Successful acknowledge
- **WHEN** a docente calls PATCH `/api/v1/teacher/risks/{id}/acknowledge`
- **THEN** the system SHALL set acknowledged_by and acknowledged_at, return 200 with the updated assessment

#### Scenario: Already acknowledged
- **WHEN** a docente acknowledges an already-acknowledged risk
- **THEN** the system SHALL update acknowledged_by and acknowledged_at to the new docente and current time (re-acknowledge)

#### Scenario: Risk not found
- **WHEN** the risk_id does not exist
- **THEN** the system SHALL return 404

### Requirement: Manual risk assessment trigger endpoint
The system SHALL provide `POST /api/v1/teacher/commissions/{commission_id}/risks/assess` that triggers a manual risk assessment for all enrolled students in the commission. Requires role docente or admin. Returns the count of assessments created/updated.

#### Scenario: Successful manual trigger
- **WHEN** a docente calls POST `/api/v1/teacher/commissions/{commission_id}/risks/assess`
- **THEN** the system SHALL run the RiskWorker for each enrolled student, return 200 with `{ data: { assessed_count: N } }`

### Requirement: RiskAssessmentResponse schema
The system SHALL provide a Pydantic v2 DTO `RiskAssessmentResponse` with fields: `id` (str), `student_id` (str), `commission_id` (str), `risk_level` (str), `risk_factors` (dict), `recommendation` (str | None), `triggered_by` (str), `assessed_at` (datetime), `acknowledged_by` (str | None), `acknowledged_at` (datetime | None). ConfigDict SHALL use `from_attributes=True`.

#### Scenario: Serialization from ORM
- **WHEN** a RiskAssessment ORM object is serialized
- **THEN** all UUID fields SHALL be converted to str and the response SHALL match the standard envelope format
