## ADDED Requirements

### Requirement: Login page
The system SHALL provide a Login page at `/login` with email and password fields, a submit button, error display, and a link to the registration page. The page SHALL use the project's design tokens and follow premium UI patterns.

#### Scenario: Successful login redirects to dashboard
- **WHEN** a user enters valid credentials and submits
- **THEN** the system SHALL call `POST /api/v1/auth/login`, store the access token in the auth store, and redirect to `/`

#### Scenario: Invalid credentials show error
- **WHEN** a user enters wrong credentials
- **THEN** the system SHALL display an error message without revealing which field is wrong

#### Scenario: Login page redirects if already authenticated
- **WHEN** an authenticated user navigates to `/login`
- **THEN** the system SHALL redirect to `/`

### Requirement: Registration page
The system SHALL provide a Registration page at `/register` with full_name, email, password, and role selection fields. The page SHALL validate inputs client-side before submitting.

#### Scenario: Successful registration redirects to login
- **WHEN** a user fills valid registration data and submits
- **THEN** the system SHALL call `POST /api/v1/auth/register` and redirect to `/login` with a success message

#### Scenario: Duplicate email shows error
- **WHEN** a user registers with an existing email
- **THEN** the system SHALL display a "Email already registered" error

### Requirement: useAuthStore with Zustand 5
The system SHALL provide `useAuthStore` following Zustand 5 patterns: individual selectors, actions inside the store, no destructuring. State SHALL include `accessToken`, `user` (id, email, fullName, role), `isAuthenticated`, `isLoading`. Actions: `login(email, password)`, `register(data)`, `logout()`, `refresh()`, `initialize()`.

#### Scenario: Login action updates store
- **WHEN** `login(email, password)` succeeds
- **THEN** the store SHALL set `accessToken`, `user`, and `isAuthenticated = true`

#### Scenario: Logout action clears store
- **WHEN** `logout()` is called
- **THEN** the store SHALL clear `accessToken`, `user`, set `isAuthenticated = false`, and call `POST /api/v1/auth/logout`

#### Scenario: Initialize attempts silent refresh
- **WHEN** `initialize()` is called on app load
- **THEN** the store SHALL call `POST /api/v1/auth/refresh`. If successful, set `accessToken` and `user`. If failed, set `isAuthenticated = false`.

### Requirement: API client auth interceptor
The `apiClient` SHALL be configured with the auth store's token provider via `setTokenProvider`. On 401 response, the client SHALL attempt a single refresh and retry the original request. If refresh fails, clear auth state and redirect to `/login`.

#### Scenario: Automatic token refresh on 401
- **WHEN** a request returns 401 and a refresh token cookie exists
- **THEN** the client SHALL call refresh, update the access token, and retry the original request

#### Scenario: Failed refresh redirects to login
- **WHEN** a 401 response occurs and refresh also fails
- **THEN** the client SHALL clear auth state and redirect to `/login`

### Requirement: Protected route component
The system SHALL provide a `<ProtectedRoute>` component that checks `isAuthenticated` from the auth store. If not authenticated, redirect to `/login`. Optionally accept `requiredRole` prop for frontend RBAC.

#### Scenario: Unauthenticated user redirected
- **WHEN** an unauthenticated user accesses a protected route
- **THEN** the system SHALL redirect to `/login`

#### Scenario: Wrong role redirected
- **WHEN** an alumno accesses a route with `requiredRole="docente"`
- **THEN** the system SHALL redirect to an unauthorized page or show an error
