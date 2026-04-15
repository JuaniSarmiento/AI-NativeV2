## Context

EPIC-03 dejó auth funcional con login, registro, JWT, RBAC, useAuthStore, y pantallas premium con Plus Jakarta Sans, emerald accent, y editorial split layout. globals.css ya tiene design tokens (@theme), dark mode, y fuentes configuradas. Existe logger.ts, api-client.ts con auth interceptor. No hay componentes compartidos, no hay MSW, no hay app shell con sidebar.

## Goals / Non-Goals

**Goals:**
- Response schemas reutilizables en backend (StandardResponse genérico)
- Health/full endpoint que reporta estado de DB y Redis
- MSW configurado para desarrollo paralelo del frontend
- Componentes base (Button, Input, Card, Modal) usando design tokens existentes
- App Shell con sidebar responsive que cambia según rol
- Routing por rol integrado al shell

**Non-Goals:**
- No implementar features de dominio (ejercicios, tutor, etc.)
- No implementar DataTable (se hará cuando haya datos reales)
- No implementar notificaciones / toast system (EPIC futura)
- No implementar breadcrumbs ni deep navigation (EPIC futura)

## Decisions

### D1: Response schemas como genéricos Pydantic

`StandardResponse[T]` usa `Generic[T]` para tipar `data`. `PaginatedResponse[T]` extiende con `meta: PaginationMeta`. Ambos en `backend/app/shared/schemas/response.py`. Cada endpoint los usa como return type.

### D2: MSW con handlers modulares

`frontend/src/mocks/handlers/` con un archivo por dominio (auth.ts, etc.). `browser.ts` arranca el service worker. Se activa condicionalmente en `main.tsx` solo cuando `import.meta.env.DEV` y `VITE_ENABLE_MSW=true`.

**Alternativa descartada**: MSW siempre activo en dev. Descartada porque ahora tenemos backend real funcional — MSW es opt-in para cuando se trabaja sin backend.

### D3: Componentes base como building blocks mínimos

Button (variantes: primary, secondary, ghost, danger + sizes sm/md/lg), Input (con label + error integrados), Card (double-bezel pattern), Modal (portal + backdrop blur). Todos usan CSS variables del theme, no colores hardcodeados.

### D4: App Shell con sidebar collapsible

`AppLayout` = sidebar (fija en desktop, drawer en mobile) + header + main content area. La sidebar muestra items distintos según el rol del usuario. El layout switcher está en el routing — no hay 3 layout components distintos, sino 1 AppLayout con nav items dinámicos.

**Alternativa descartada**: Layouts separados por rol (AlumnoLayout, DocenteLayout). Descartada porque el 90% del layout es idéntico — solo cambian los nav items.

### D5: Routing nested dentro del shell

```
/login, /register  →  sin shell (ya existe)
/                  →  AppLayout + Dashboard (redirect según rol)
/exercises/*       →  AppLayout + ExerciseRoutes (alumno)
/courses/*         →  AppLayout + CourseRoutes (docente/admin)
/dashboard/*       →  AppLayout + DashboardRoutes (docente/admin)
```

Las rutas futuras se agregan sin tocar el shell.

## Risks / Trade-offs

- **[Risk] MSW intercepta requests inesperadamente** → Mitigation: opt-in via env var `VITE_ENABLE_MSW=true`, desactivado por defecto.
- **[Risk] Sidebar items se desincroniza con rutas reales** → Mitigation: nav items definidos en un array de config centralizado con `path`, `label`, `icon`, `roles`.
- **[Risk] Modal sin portal puede romper z-index** → Mitigation: Modal usa `createPortal` al body.
