## ADDED Requirements

### Requirement: AppLayout component
The system SHALL provide an `AppLayout` component with a collapsible sidebar (fixed on desktop, drawer on mobile), a header bar, and a main content area. The sidebar SHALL show navigation items based on the authenticated user's role.

#### Scenario: Desktop sidebar is visible
- **WHEN** the viewport is wider than 768px
- **THEN** the sidebar SHALL be visible as a fixed left panel

#### Scenario: Mobile sidebar is a drawer
- **WHEN** the viewport is narrower than 768px
- **THEN** the sidebar SHALL be hidden by default and openable via a hamburger button in the header

### Requirement: Role-based navigation items
The system SHALL define navigation items in a centralized config array with `path`, `label`, `icon`, and `roles` fields. Only items matching the current user's role SHALL be displayed.

#### Scenario: Alumno sees student nav items
- **WHEN** an alumno is authenticated
- **THEN** the sidebar SHALL show only alumno-relevant items (dashboard, ejercicios)

#### Scenario: Docente sees teacher nav items
- **WHEN** a docente is authenticated
- **THEN** the sidebar SHALL show docente-relevant items (dashboard, cursos, alumnos, reportes)

### Requirement: Nested routing within shell
The system SHALL configure React Router with nested routes inside AppLayout. Feature routes SHALL be lazy-loaded.

#### Scenario: Navigation does not reload the page
- **WHEN** the user clicks a sidebar link
- **THEN** only the main content area SHALL update, the sidebar and header remain stable
