## Context

EPIC-02 dejó el modelo `User` (con `UserRole` ENUM: alumno/docente/admin), `BaseRepository`, `AsyncUnitOfWork` y la session factory. El frontend tiene un `apiClient` con `setTokenProvider()` listo para recibir el token, y un App.tsx con BrowserRouter básico. No existe `core/security.py`, no hay feature de auth en backend ni frontend.

Estado actual relevante:
- `backend/app/shared/models/user.py` — User con email, password_hash, role, is_active
- `backend/app/shared/repositories/base.py` — BaseRepository genérico
- `frontend/src/shared/lib/api-client.ts` — fetch wrapper con `setTokenProvider()` y `Authorization: Bearer`
- `frontend/src/styles/globals.css` — TailwindCSS 4 con @theme tokens (primary, surface, text, border, radius)
- `frontend/src/App.tsx` — BrowserRouter con Landing + 404
- Redis disponible en `localhost:6379`

## Goals / Non-Goals

**Goals:**
- Auth end-to-end funcional (register → login → use token → refresh → logout)
- JWT con access (15min) + refresh (7d) y rotation segura
- RBAC funcional con 3 roles
- Frontend premium (Login + Registro) usando design tokens existentes
- Protected routes con redirect transparente
- Token blacklist en Redis para logout + rotation

**Non-Goals:**
- OAuth / social login (futuro)
- Email verification (futuro)
- Password reset flow (futuro)
- 2FA / MFA (futuro)
- Admin panel para gestión de usuarios (EPIC separada)

## Decisions

### D1: JWT con python-jose, bcrypt para passwords

`python-jose[cryptography]` para JWT (ya en pyproject.toml). `bcrypt` para password hashing (ya en deps). HS256 con SECRET_KEY del env. Access token con `exp` de 15 minutos y `jti` (JWT ID) único. Refresh token con `exp` de 7 días y `jti` propio.

**Alternativa descartada**: PyJWT. Descartada porque python-jose ya está en las dependencias y soporta más algoritmos.

### D2: Refresh token en httpOnly cookie, access token en memoria

El access token se retorna en el JSON body y vive en Zustand (memoria). El refresh token se setea como `httpOnly`, `Secure`, `SameSite=Lax` cookie. Esto previene XSS (no se puede leer el refresh desde JS) sin requerir BFF.

**Alternativa descartada**: Ambos tokens en localStorage. Descartada por vulnerabilidad a XSS.

### D3: Token blacklist en Redis con TTL automático

Keys: `auth:blacklist:{jti}` con TTL = tiempo restante del token. Al hacer logout o refresh, el `jti` del token viejo se agrega a la blacklist. La verificación de JWT chequea que el `jti` no esté en blacklist.

**Alternativa descartada**: Tabla SQL para blacklist. Descartada porque cada request validaría contra DB, Redis es O(1) y los tokens expiran solos.

### D4: Auth feature como módulo backend con router + schemas + service

Estructura:
```
backend/app/features/auth/
├── __init__.py
├── router.py        # Thin router: register, login, refresh, logout
├── schemas.py       # Pydantic v2: RegisterRequest, LoginRequest, TokenResponse
├── service.py       # AuthService: register, authenticate, create_tokens, refresh, logout
└── dependencies.py  # get_current_user, require_role
```

El service recibe un `UserRepository` + `AsyncSession` via DI. Nunca importa session directamente.

### D5: Rate limiting con slowapi

`slowapi` (basado en `limits`) integrado como middleware FastAPI. 100 req/min general por IP. Configurable por endpoint. Redis como backend para contadores distribuidos.

**Alternativa descartada**: Rate limiting custom con Redis Lua scripts. Descartada por complejidad innecesaria — slowapi ya resuelve el caso.

### D6: Frontend auth con Zustand 5 patterns

`useAuthStore` sigue los patterns del proyecto:
- Selectores individuales, nunca destructurar el store
- `useShallow` para objetos/arrays
- Actions dentro del store
- Access token en state (memoria), refresh token en httpOnly cookie (invisible a JS)
- Auto-refresh: el apiClient intercepta 401, intenta refresh, y reintenta el request original

### D7: Protected routes con componente wrapper

`<ProtectedRoute>` wraps content, chequea `isAuthenticated` del store, redirect a `/login` si no. Opcionalmente recibe `requiredRole` para RBAC en frontend.

## Risks / Trade-offs

- **[Risk] Refresh token cookie no disponible en dev (HTTP)** → Mitigation: en desarrollo `Secure=false`, solo `httpOnly` y `SameSite=Lax`. Variable `APP_ENV` controla esto.
- **[Risk] Race condition en refresh rotation** → Mitigation: el refresh endpoint es atomic — blacklist del token viejo + emisión del nuevo en una sola operación Redis. Requests concurrentes con el mismo refresh token: el primero gana, los demás reciben 401.
- **[Risk] slowapi dependency extra** → Mitigation: es lightweight, bien mantenido, y evita escribir rate limiting manual. Si necesitamos sliding window avanzado, migramos a Lua scripts (Redis patterns skill).
- **[Risk] Token en Zustand se pierde al recargar página** → Mitigation: al cargar la app, el frontend intenta un `POST /refresh` (la cookie viaja automáticamente). Si tiene refresh válido, recupera la sesión. Si no, redirect a login.
