## 1. Core Security Module

- [x] 1.1 Create `backend/app/core/security.py` with `hash_password()`, `verify_password()`, `create_access_token()`, `create_refresh_token()`, `decode_token()` using bcrypt + python-jose HS256
- [x] 1.2 Add `SECRET_KEY`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS` to Settings in `backend/app/config.py` (if not already present)

## 2. Auth Schemas

- [x] 2.1 Create `backend/app/features/auth/schemas.py` with Pydantic v2 models: `RegisterRequest`, `LoginRequest`, `TokenResponse`, `UserResponse`

## 3. Auth Service

- [x] 3.1 Create `backend/app/features/auth/service.py` with `AuthService` class: `register()`, `authenticate()`, `create_token_pair()`, `refresh_tokens()`, `logout()`, `blacklist_token()`
- [x] 3.2 Implement Redis token blacklist: `blacklist_token(jti, ttl)` and `is_blacklisted(jti)` using key pattern `auth:blacklist:{jti}`

## 4. Auth Dependencies

- [x] 4.1 Create `backend/app/features/auth/dependencies.py` with `get_current_user` dependency (extract JWT, validate, check blacklist, return User)
- [x] 4.2 Add `require_role(*roles)` dependency factory that checks current user's role

## 5. Auth Router

- [x] 5.1 Create `backend/app/features/auth/router.py` with `POST /register`, `POST /login`, `POST /refresh`, `POST /logout`
- [x] 5.2 Register auth router in `backend/app/main.py` under prefix `/api/v1/auth`

## 6. Rate Limiting

- [x] 6.1 Add `slowapi` to `backend/pyproject.toml` dependencies
- [x] 6.2 Configure rate limiting middleware in `backend/app/main.py` (100 req/min per IP, Redis backend)

## 7. Frontend Auth Store

- [x] 7.1 Create `frontend/src/features/auth/types.ts` with `AuthUser`, `LoginCredentials`, `RegisterData` types
- [x] 7.2 Create `frontend/src/features/auth/store.ts` with `useAuthStore` (Zustand 5): accessToken, user, isAuthenticated, isLoading, actions (login, register, logout, refresh, initialize)
- [x] 7.3 Update `frontend/src/shared/lib/api-client.ts` with auth interceptor: auto-refresh on 401, retry original request

## 8. Frontend Auth Pages

- [x] 8.1 Create `frontend/src/features/auth/LoginPage.tsx` with email/password form, error handling, redirect if authenticated
- [x] 8.2 Create `frontend/src/features/auth/RegisterPage.tsx` with full_name, email, password, role selection, client-side validation
- [x] 8.3 Create `frontend/src/features/auth/ProtectedRoute.tsx` component with isAuthenticated check + optional requiredRole

## 9. App Integration

- [x] 9.1 Update `frontend/src/App.tsx` with auth routes (/login, /register), protected routes, and auth initialization on app load

## 10. Backend Tests

- [x] 10.1 Create `backend/tests/unit/test_security.py` with tests for hash_password, verify_password, create/decode tokens
- [x] 10.2 Create `backend/tests/integration/test_auth.py` with tests for register, login, refresh, logout, RBAC, and blacklist
