# EPIC-03: Autenticación JWT y RBAC

> **Issue**: #3 | **Milestone**: Fase 0 — Fundación | **Labels**: epic, fase-0, priority:critical

**Nivel de gobernanza**: CRITICAL — cambios requieren revisión formal

## Contexto

Sistema de autenticación y autorización que protege toda la plataforma. JWT con access token (15min) + refresh token (7d) con rotation. RBAC con 3 roles: alumno, docente, admin. Este sistema es CRÍTICO — todo endpoint de Fases 1-3 depende de que auth funcione correctamente.

## Alcance

### Backend
- `POST /api/v1/auth/register` — registro de usuarios
- `POST /api/v1/auth/login` — login, retorna access + refresh tokens
- `POST /api/v1/auth/refresh` — rota refresh token, retorna nuevo access token
- `POST /api/v1/auth/logout` — invalida tokens (blacklist en Redis)
- Middleware JWT que extrae y valida el token en cada request
- Decoradores/dependencies de autorización por rol (`require_role("docente")`)
- Hashing de passwords con bcrypt
- Rate limiting: 100 req/min general, configurable por endpoint

### Frontend
- Pantalla de Login (email + password)
- Pantalla de Registro (nombre, email, password, rol)
- `useAuthStore` (Zustand): access token en memoria, refresh en httpOnly cookie
- HTTP client con interceptor que adjunta `Authorization: Bearer <token>` y maneja refresh automático
- Protected routes (redirect a login si no autenticado)
- Logout funcional

## Contratos

### Produce
- `get_current_user` dependency para inyectar el usuario autenticado en cualquier endpoint
- `require_role(role)` dependency para RBAC en endpoints
- `useAuthStore` con acciones: `login()`, `logout()`, `refresh()`, `isAuthenticated`
- HTTP client configurado con auth interceptor
- Token blacklist en Redis para logout/refresh rotation

### Consume
- Modelo `users` (de EPIC-02)
- Redis para token blacklist (de EPIC-01)

### Modelos (owner)
- `operational.users` (ya creado en EPIC-02, acá se usa)
- Redis keys: `token:blacklist:{jti}` con TTL = tiempo restante del token

## Dependencias
- **Blocked by**: EPIC-01, EPIC-02 (necesita users + Redis)
- **Blocks**: EPIC-05 (primeros endpoints autenticados), EPIC-09 (auth JWT en WebSocket del tutor), EPIC-12 (auth protege endpoints de reflexión)

## Stories

- [ ] Endpoint `POST /api/v1/auth/register` con validación Pydantic
- [ ] Endpoint `POST /api/v1/auth/login` — JWT access (15min) + refresh (7d)
- [ ] Endpoint `POST /api/v1/auth/refresh` con refresh token rotation
- [ ] Endpoint `POST /api/v1/auth/logout` con blacklist en Redis
- [ ] `get_current_user` dependency (extrae JWT, valida, retorna user)
- [ ] `require_role()` dependency para RBAC
- [ ] Rate limiting middleware (100 req/min general)
- [ ] Frontend: pantallas Login y Registro
- [ ] Frontend: `useAuthStore` (Zustand) con token management
- [ ] Frontend: HTTP client con auth interceptor + auto-refresh
- [ ] Frontend: Protected routes con redirect
- [ ] Tests de integración: login, refresh, logout, RBAC, rate limiting

## Criterio de Done

- Login/registro funcionan end-to-end (API + UI)
- Refresh rotation funciona sin perder sesión
- Endpoints protegidos rechazan requests sin token (401) y sin permiso (403)
- Rate limiting activo
- Tests de integración pasan

## Referencia
- `knowledge-base/03-seguridad/01_modelo_de_seguridad.md`
- `knowledge-base/03-seguridad/02_superficie_de_ataque.md`
