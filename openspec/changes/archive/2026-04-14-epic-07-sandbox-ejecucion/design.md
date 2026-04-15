## Context

EPIC-06B dejó actividades con ejercicios que tienen test_cases ejecutables (stdin/stdout). El alumno ve los ejercicios en orden dentro de la actividad con progress bar. Hay un placeholder donde debería ir el editor de código. Los test cases tienen estructura: `{ input: "5\n3", expected_output: "8" }`.

## Goals / Non-Goals

**Goals:**
- Subprocess aislado que ejecute Python con límites estrictos
- Test runner que evalúe cada test case por separado
- Endpoint REST para ejecución
- Editor de código + panel de output en el frontend
- Bloqueo de código malicioso
- Eventos al Event Bus para trazabilidad cognitiva

**Non-Goals:**
- No implementar submissions ni persistencia de intentos (EPIC-08)
- No implementar editor avanzado (Monaco) — usamos textarea con monospace por ahora
- No soportar otros lenguajes (solo Python)
- No implementar ejecución concurrente masiva (un alumno a la vez es suficiente para MVP)

## Decisions

### D1: subprocess.run con resource limits

Usamos `subprocess.run` con `timeout` parameter. Para memory limits usamos `resource.setrlimit` en un preexec_fn. No usamos Docker-in-Docker ni containers — un subprocess es suficiente para MVP y mucho más simple de operar.

```python
import subprocess, resource

def _set_limits():
    # 128MB memory limit
    resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024, 128 * 1024 * 1024))
    # No network
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))

result = subprocess.run(
    ["python3", "-c", code],
    input=stdin_data,
    capture_output=True,
    timeout=10,
    preexec_fn=_set_limits,
    text=True,
)
```

### D2: Import blacklist como wrapper

En vez de parsear el código para detectar imports (bypasseable), wrapeamos la ejecución con un script que overridea `__import__` para bloquear módulos peligrosos: os, subprocess, socket, shutil, pathlib, importlib, ctypes, etc.

### D3: Test runner ejecuta cada case por separado

Para cada test case, se corre el código del alumno con el `input` del case via stdin y se compara stdout con `expected_output`. Esto da resultados individuales (pass/fail por case).

### D4: Editor simple con textarea monospace

Para MVP usamos un `<textarea>` con fuente mono y syntax highlighting básico (no Monaco todavía). Funciona, es liviano, no agrega dependencias. Monaco viene en una EPIC de polish.

### D5: Eventos al outbox atómicos

Después de cada ejecución, el endpoint escribe `code.executed` o `code.execution.failed` en la tabla `event_outbox`. El outbox worker lo publica al stream `events:code`.

## Risks / Trade-offs

- **[Risk] Subprocess escape** → Mitigation: resource limits + import blacklist + no filesystem access (chdir a /tmp). No es un sandbox de producción enterprise, pero es suficiente para una cátedra universitaria.
- **[Risk] Memory limit kill vs graceful** → Mitigation: `RLIMIT_AS` causa MemoryError en Python, que capturamos como resultado "memory exceeded".
- **[Risk] Infinite loops** → Mitigation: `timeout=10` en subprocess.run mata el proceso.
- **[Risk] textarea no tiene syntax highlighting** → Aceptable para MVP. Los alumnos escriben 20-50 líneas, no necesitan un IDE completo.
