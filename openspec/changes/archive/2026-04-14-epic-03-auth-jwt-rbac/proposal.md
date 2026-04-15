## Why

Todo endpoint de la plataforma necesita autenticación y autorización. Sin auth, las Fases 1-3 no pueden proteger sus recursos. EPIC-02 dejó el modelo User listo. Ahora necesitamos el flujo completo: login, registro, JWT con refresh rotation, RBAC por roles, y un frontend de auth funcional (login, registro, protected routes, auth store).

## What Changes

### Backend
- Endpoints de auth: register, login, refresh, logout
- JWT access token (15min) + refresh token (7d) con rotation
- Password hashing con bcrypt (módulo `core/security.py`)
- `get_current_user` dependency para inyectar usuario autenticado
- `require_role()` dependency para RBAC (alumno, docente, admin)
- Token blacklist en Redis para logout y refresh rotation
- Rate limiting middleware (100 req/min general)

### Frontend
- Pantallas de Login y Registro con diseño premium
- `useAuthStore` (Zustand 5) con token management en memoria
- API client con auth interceptor + auto-refresh transparente
- Protected routes con redirect a login
- Logout funcional

## Capabilities

### New Capabilities

- `auth-backend`: Endpoints REST de autenticación (register, login, refresh, logout), JWT generation/validation, password hashing, token blacklist en Redis
- `auth-rbac`: Dependencies de autorización (get_current_user, require_role), middleware de rate limiting
- `auth-frontend`: Pantallas de Login/Registro, useAuthStore (Zustand), auth interceptor en HTTP client, protected routes

### Modified Capabilities

- `monorepo-structure`: Se agregan archivos de auth feature al backend y frontend

## Impact

- **Backend**: `backend/app/features/auth/`, `backend/app/core/security.py`, `backend/app/dependencies.py`
- **Frontend**: `frontend/src/features/auth/`, `frontend/src/shared/lib/api-client.ts`, `frontend/src/App.tsx`
- **Redis**: Keys `auth:blacklist:{jti}` con TTL
- **Downstream**: Desbloquea EPIC-05 (CRUD autenticado), EPIC-09 (tutor WebSocket con JWT), EPIC-12 (reflexión)
