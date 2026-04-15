## 1. Backend Response Schemas

- [x] 1.1 Create `backend/app/shared/schemas/response.py` with `StandardResponse[T]`, `PaginatedResponse[T]`, `PaginationMeta`, `ErrorDetail`
- [x] 1.2 Create `backend/app/shared/schemas/__init__.py` re-exporting response schemas

## 2. Health Full Endpoint

- [x] 2.1 Add `GET /api/v1/health/full` endpoint in main.py that checks DB and Redis connectivity, returns 200 or 503

## 3. MSW Setup

- [x] 3.1 Install `msw` as dev dependency in frontend
- [x] 3.2 Create `frontend/src/mocks/browser.ts` with MSW worker setup
- [x] 3.3 Create `frontend/src/mocks/handlers/auth.ts` with mock handlers for login, register, refresh, logout
- [x] 3.4 Create `frontend/src/mocks/handlers/index.ts` aggregating all handlers
- [x] 3.5 Update `frontend/src/main.tsx` to conditionally start MSW when `VITE_ENABLE_MSW=true`

## 4. Design System Components

- [x] 4.1 Create `frontend/src/shared/components/Button.tsx` with variants (primary, secondary, ghost, danger), sizes (sm, md, lg), loading, disabled, icon slot
- [x] 4.2 Create `frontend/src/shared/components/Input.tsx` with integrated label, helper text, error state
- [x] 4.3 Create `frontend/src/shared/components/Card.tsx` with double-bezel pattern
- [x] 4.4 Create `frontend/src/shared/components/Modal.tsx` with createPortal, backdrop blur, close on escape, spring animation

## 5. App Shell

- [x] 5.1 Create navigation config at `frontend/src/shared/lib/navigation.ts` with items per role (path, label, icon, roles)
- [x] 5.2 Create `frontend/src/shared/components/AppLayout.tsx` with sidebar (fixed desktop, drawer mobile), header, content area
- [x] 5.3 Update `frontend/src/App.tsx` with nested routing inside AppLayout, lazy-loaded feature routes

## 6. Testing

- [x] 6.1 Create `frontend/src/shared/components/__tests__/Button.test.tsx` smoke test
- [x] 6.2 Create `backend/tests/integration/test_health_full.py` testing health/full endpoint
