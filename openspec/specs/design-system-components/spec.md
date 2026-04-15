## ADDED Requirements

### Requirement: Button component
The system SHALL provide a `Button` component with variants (primary, secondary, ghost, danger), sizes (sm, md, lg), loading state, disabled state, and optional icon slot. It SHALL use design tokens from the theme.

#### Scenario: Primary button renders with accent color
- **WHEN** `<Button variant="primary">` is rendered
- **THEN** it SHALL use the accent-600 background with white text and active:scale-[0.98] feedback

#### Scenario: Loading state shows spinner
- **WHEN** `<Button loading>` is rendered
- **THEN** it SHALL show a spinner and disable click

### Requirement: Input component
The system SHALL provide an `Input` component with integrated label, optional helper text, error state, and consistent styling using theme tokens.

#### Scenario: Error state shows red border and message
- **WHEN** `<Input error="Campo requerido">` is rendered
- **THEN** the input SHALL have a red border and the error message displayed below

### Requirement: Card component
The system SHALL provide a `Card` component using the double-bezel pattern (outer ring + inner elevated surface) from the design system.

#### Scenario: Card renders with elevation
- **WHEN** `<Card>` is rendered
- **THEN** it SHALL have an outer border, inner background, and diffused shadow

### Requirement: Modal component
The system SHALL provide a `Modal` component rendered via `createPortal` with backdrop blur, close on escape, close on backdrop click, and spring animation.

#### Scenario: Modal opens with animation
- **WHEN** `<Modal open>` transitions from closed to open
- **THEN** the backdrop SHALL fade in and the content SHALL scale up with spring easing

#### Scenario: Modal closes on escape key
- **WHEN** the user presses Escape while a Modal is open
- **THEN** the Modal SHALL close
