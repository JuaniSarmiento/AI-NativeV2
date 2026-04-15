## ADDED Requirements

### Requirement: Generic BaseRepository with async CRUD
The system SHALL provide a `BaseRepository[ModelType]` generic class that encapsulates common data access patterns. It SHALL receive an `AsyncSession` via constructor injection and provide methods: `get_by_id()`, `list()`, `create()`, `update()`, `soft_delete()`.

#### Scenario: get_by_id returns a model instance
- **WHEN** `get_by_id(id)` is called with a valid UUID
- **THEN** it SHALL return the model instance or raise `NotFoundError`

#### Scenario: get_by_id filters inactive by default
- **WHEN** `get_by_id(id)` is called for a soft-deleted record (is_active=False)
- **THEN** it SHALL raise `NotFoundError` unless `include_inactive=True` is passed

#### Scenario: list returns paginated results
- **WHEN** `list(page=1, per_page=20)` is called
- **THEN** it SHALL return a tuple of `(items, total_count)` with at most `per_page` items

#### Scenario: list filters inactive by default
- **WHEN** `list()` is called
- **THEN** it SHALL only return records where `is_active` is True

#### Scenario: create persists a new record
- **WHEN** `create(data)` is called with a dict of field values
- **THEN** it SHALL add the model to the session and flush (without committing — commit is UoW responsibility)

#### Scenario: update modifies existing fields
- **WHEN** `update(id, data)` is called with a dict of field values
- **THEN** it SHALL fetch the record, apply changes, flush, and return the updated instance

#### Scenario: soft_delete sets is_active to False
- **WHEN** `soft_delete(id)` is called
- **THEN** it SHALL set `is_active = False` on the record and flush

### Requirement: Configurable eager loading
The BaseRepository SHALL accept `load_options` parameter (list of SQLAlchemy loader options like `selectinload`) in `get_by_id()` and `list()` methods.

#### Scenario: Loading with relationships
- **WHEN** `get_by_id(id, load_options=[selectinload(Course.commissions)])` is called
- **THEN** it SHALL eagerly load the specified relationships in the same query
