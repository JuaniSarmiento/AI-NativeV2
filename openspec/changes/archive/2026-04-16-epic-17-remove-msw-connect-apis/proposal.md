## Why

La EPIC-17 original asumia que el frontend usaba MSW (Mock Service Worker) durante desarrollo paralelo. Tras auditoria completa, MSW nunca se implemento — todas las features ya usan `apiClient` contra el backend real via proxy Vite. Sin embargo, hay residuos de configuracion, un flag muerto, y discrepancias entre frontend y backend que rompen flujos end-to-end. El tutor messages endpoint no permite docente (rompe la traza cognitiva), y hay varios componentes que necesitan ajustes para que el flujo completo funcione sin errores.

## What Changes

- Limpiar flag muerto `VITE_ENABLE_MSW` del .env.development
- Fix RBAC del endpoint tutor messages para permitir docente/admin (necesario para traza EPIC-16)
- Agregar endpoint de tutor messages para docente con student_id param
- Verificar y fixear schemas de respuesta vs tipos TypeScript en cada feature
- Validar flujo E2E completo: alumno (login → cursos → actividad → codigo → tutor → submit → reflexion) y docente (dashboard → riesgo → traza → governance)
- Fix discrepancias de tipos y respuestas encontradas en auditoria

## Capabilities

### New Capabilities
- `tutor-messages-teacher-api`: Endpoint para que docente/admin pueda leer mensajes del tutor de cualquier alumno (necesario para traza cognitiva)

### Modified Capabilities
- `tutor-chat-ws`: Se modifica RBAC del endpoint de messages para soportar docente/admin con student_id

## Impact

- **Backend**: Modificacion menor en `tutor/router.py` — nuevo endpoint o ajuste RBAC
- **Frontend**: Cleanup de .env, ajustes menores de tipos en componentes
- **API**: 1 endpoint nuevo o modificado
- **Riesgo**: Bajo — todos los endpoints ya responden 200, solo hay que arreglar permisos y tipos
