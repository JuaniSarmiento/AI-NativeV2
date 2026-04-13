# Resumen Consolidado — 03-seguridad

> 2 archivos. Última actualización: 2026-04-13

---

## 01_modelo_de_seguridad.md — Datos Clave

### Capas de defensa
```
Cliente → CORS → Rate Limiter → Auth Middleware → RBAC → Handler → Sandbox/LLM/DB
```

### Auth flow
- **Registro**: email+password+full_name → bcrypt hash (factor 12) → role=alumno server-side → 201 sin tokens
- **Login**: email+password → verify bcrypt → access token (JWT 15min) + refresh token (JWT 7d en cookie httpOnly SameSite=Strict)
- **Refresh**: lee cookie httpOnly → verifica jti en Redis → DEL viejo → genera nuevo par → rotation pattern
- **Logout**: blacklist access jti en Redis (TTL=remaining) + DEL refresh jti + limpiar cookie
- **Detección de robo**: si refresh jti no existe en Redis → invalida TODAS las sesiones del usuario

### JWT Structure
- **Access**: sub(user_id), role, email, jti, iat, exp(15min), type="access". Algoritmo HS256.
- **Refresh**: sub, jti, iat, exp(7d), type="refresh". Sin role ni email.
- **Firma**: HS256 con SECRET_KEY 256 bits mínimo. Futuro: RS256 para microservicios.

### Redis keys (auth)
- `auth:refresh:{jti}` → user_id, TTL 604800s
- `auth:blacklist:{jti}` → "1", TTL = tiempo restante del token

### Token storage
- Access: Zustand (memoria), se pierde al recargar
- Refresh: cookie httpOnly, browser envía automáticamente al recargar

### Password hashing
- bcrypt factor 12 (~300ms)
- Política: min 8 chars, 1 mayúscula, 1 minúscula, 1 dígito, no puede ser = email

### RBAC
- 3 roles: alumno, docente, admin
- RequireRole dependency con factory pattern
- IDOR prevention: ownership check para recursos del alumno
- Endpoint `POST /admin/users/{id}/role` para cambiar roles (solo admin)

### WebSocket auth
- JWT en query param `?token=<jwt>` (no headers post-handshake)
- Verificación ANTES de websocket.accept()
- Si inválido: close(4001)
- Nota: token en query string aparece en logs → usar tokens corta vida + no loggear query strings en prod

### Rate limiting
- Sliding Window con Redis (ZSET)
- Límites:
  - Tutor: 30/hr por user+exercise (`rl:tutor:{uid}:{eid}`)
  - API general: 100/min por IP (`rl:api:{ip}`)
  - Login: 10/5min por IP (`rl:login:{ip}`)
  - Register: 5/hr por IP
  - Sandbox: 20/min por user (`rl:sandbox:{uid}`)

### CORS
- Dev: localhost:5173 only
- Prod: FRONTEND_URL env var
- allow_credentials=True (para cookie httpOnly)
- Wildcard "*" PROHIBIDO

### Security Headers
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- HSTS: 1 año (solo prod)
- CSP: script-src 'self' 'wasm-unsafe-eval' (para Monaco WASM), connect-src 'self' wss:
- Permissions-Policy: camera=(), microphone=(), geolocation=()

### INCONSISTENCIAS

**IC-S1: Rate limiting — algoritmo diverge**
- 03-seguridad/01: Sliding Window (ZSET)
- 02-arquitectura/03_api: Token Bucket
- **Son algoritmos distintos. Necesita unificación.** Sliding Window es más justo.

**IC-S2: Rate limit sandbox endpoint name**
- 03-seguridad: `POST /code/execute` con `rl:sandbox:{user_id}` 20/min
- 02-arquitectura/03_api: `POST /student/exercises/{id}/run` 30/min
- **Endpoint name y límites difieren.**

**IC-S3: Tutor endpoint name**
- 03-seguridad: `POST /tutor/message` y `POST /tutor/session`
- 02-arquitectura/03_api: `WS /ws/tutor/chat`
- **El tutor usa WebSocket, no POST. Los endpoint names de la RBAC matrix son incorrectos.**

---

## 02_superficie_de_ataque.md — Datos Clave

### 7 áreas de ataque analizadas
1. **Sandbox**: RCE, DoS (CPU/mem), exfiltración env vars, container escape
2. **Tutor LLM**: prompt injection, jailbreak, token abuse
3. **API REST**: auth bypass, IDOR, SQL injection, mass assignment, info disclosure
4. **WebSocket**: hijacking, DoS/flooding
5. **CTR Hash Chain**: tampering, event injection
6. **Frontend**: XSS, CSRF, token theft
7. **Post-procesador tutor**: pipeline de guardrails

### Mitigaciones clave (todas marcadas como "Implementado" o "Estructural")

| Amenaza | Mitigación |
|---------|-----------|
| RCE en sandbox | timeout 10s + RLIMIT_AS 128MB + seccomp (prod) + RLIMIT_NPROC |
| Prompt injection | System prompt defensivo + post-processor pipeline |
| IDOR | Ownership check en TODOS los endpoints sensibles |
| SQL injection | SQLAlchemy ORM parametrizado, no raw SQL con interpolación |
| Mass assignment | Pydantic schemas separados input/output (role no en UserCreate) |
| XSS | React escaping + CSP + react-markdown con sanitize |
| CSRF | Token en header Authorization, no en cookie |
| Token theft | Access token en memoria (Zustand), refresh en httpOnly cookie |
| WS hijacking | JWT verificado ANTES de websocket.accept() |
| Hash chain tampering | SHA-256 chain + tabla inmutable + permisos PostgreSQL |

### Sandbox dev vs prod
- **Dev**: asyncio.create_subprocess_exec() con timeout + resource limits. NUNCA subprocess.run() en async.
- **Prod**: Docker container sin root, sin red (--network none), seccomp, --no-new-privileges, UID 1000

### Nota sobre subprocess
- Doc usa `asyncio.create_subprocess_exec()` (correcto para async)
- ADR-005 en 07_adrs.md mencionaba `subprocess.Popen` (sync)
- **IC-S4**: Debería ser asyncio.create_subprocess_exec en toda la doc

---

## FIXES PENDIENTES (intra-carpeta)

1. IC-S1: Unificar algoritmo rate limiting a Sliding Window (actualizar 02-arquitectura/03_api)
2. IC-S2: Alinear nombre endpoint sandbox (POST /student/exercises/{id}/run, 30/min)
3. IC-S3: Alinear RBAC matrix — usar nombres reales de endpoints (WS /ws/tutor/chat, no POST /tutor/message)
4. IC-S4: Sandbox debe usar asyncio.create_subprocess_exec, no subprocess.Popen en ADR-005
