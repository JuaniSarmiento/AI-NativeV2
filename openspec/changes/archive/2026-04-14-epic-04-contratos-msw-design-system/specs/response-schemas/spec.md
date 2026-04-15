## ADDED Requirements

### Requirement: Standard API response schema
The system SHALL provide `StandardResponse[T]` generic Pydantic model with fields: `status` ("ok"|"error"), `data` (T), `meta` (dict, optional), `errors` (list of ErrorDetail, optional).

#### Scenario: Successful response shape
- **WHEN** an endpoint returns a successful response
- **THEN** the body SHALL match `{ "status": "ok", "data": <T>, "meta": {}, "errors": [] }`

### Requirement: Paginated response schema
The system SHALL provide `PaginatedResponse[T]` extending StandardResponse with `meta` containing `page`, `per_page`, `total`, `total_pages`.

#### Scenario: Paginated list response
- **WHEN** a list endpoint returns paginated data
- **THEN** `meta` SHALL contain page, per_page, total, total_pages with correct values

### Requirement: Error detail schema
The system SHALL provide `ErrorDetail` model with fields: `code` (str), `message` (str), `field` (str, optional).

#### Scenario: Validation error includes field
- **WHEN** a validation error occurs on the `email` field
- **THEN** the error detail SHALL include `field: "email"`
