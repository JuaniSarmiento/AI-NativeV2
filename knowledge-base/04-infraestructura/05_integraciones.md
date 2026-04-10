# Integraciones Externas — Plataforma AI-Native

**Última actualización**: 2026-04-10
**Audiencia**: desarrolladores del proyecto
**Clasificación**: Documentación interna — infraestructura

---

## Índice

1. [Anthropic Claude API](#1-anthropic-claude-api)
2. [LLM Adapter Protocol — abstracción multi-proveedor](#2-llm-adapter-protocol)
3. [Monaco Editor — integración en frontend](#3-monaco-editor)
4. [Recharts — dashboards de analytics](#4-recharts)
5. [MSW — mocking en desarrollo y tests](#5-msw)

---

## 1. Anthropic Claude API

### 1.1 Visión general

El tutor socrático usa la API de Anthropic como único proveedor LLM en la implementación inicial. La integración es la más crítica del sistema por su impacto en la experiencia pedagógica y el costo operativo.

**Modelo usado**: `claude-sonnet-4-5` (configurable via `ANTHROPIC_MODEL` env var).
**Justificación del modelo**: balance entre capacidad de razonamiento pedagógico, velocidad de respuesta, y costo por token. Los modelos Haiku son demasiado limitados para el diálogo socrático complejo; Opus tiene latencia alta para una plataforma educativa interactiva.

### 1.2 SDK Python — Instalación y cliente

```python
# app/integrations/anthropic_client.py
import anthropic
from app.core.config import settings

# Cliente singleton — inicializado en startup de la app
_client: anthropic.AsyncAnthropic | None = None

def get_anthropic_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=settings.ANTHROPIC_TIMEOUT,
            max_retries=2,               # reintentos automáticos en rate limit / 5xx
        )
    return _client
```

### 1.3 Mensajes API — Estructura de la conversación

La API de Anthropic usa el formato Messages API donde el historial de la conversación se envía completo en cada request:

```python
# app/services/tutor/llm_service.py
from anthropic import AsyncAnthropic
from anthropic.types import MessageParam

async def send_tutor_message(
    messages: list[MessageParam],     # historial completo
    system_prompt: str,
    user_message: str,
) -> str:
    client = get_anthropic_client()

    response = await client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=settings.ANTHROPIC_MAX_TOKENS,
        temperature=settings.ANTHROPIC_TEMPERATURE,
        system=system_prompt,
        messages=messages + [{"role": "user", "content": user_message}],
    )

    return response.content[0].text
```

**Estructura del mensaje enviado a la API**:

```json
{
  "model": "claude-sonnet-4-5",
  "max_tokens": 2048,
  "temperature": 0.7,
  "system": "Sos un tutor socrático especializado en Python...",
  "messages": [
    {"role": "user", "content": "¿Cómo hago un bucle en Python?"},
    {"role": "assistant", "content": "¿Qué tipo de iteración necesitás? ¿Repetir N veces o recorrer una colección?"},
    {"role": "user", "content": "Quiero recorrer una lista"}
  ]
}
```

### 1.4 Streaming — Respuesta en tiempo real

Para una experiencia de tutor fluida, las respuestas se streaman al cliente via WebSocket:

```python
# app/services/tutor/streaming_service.py
from anthropic import AsyncAnthropic
from fastapi import WebSocket

async def stream_tutor_response(
    messages: list[dict],
    system_prompt: str,
    websocket: WebSocket,
    session_id: str,
) -> str:
    """
    Streama la respuesta del LLM al WebSocket del cliente.
    Retorna el texto completo para persistir en DB.
    """
    client = get_anthropic_client()
    full_response = ""

    async with client.messages.stream(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=settings.ANTHROPIC_MAX_TOKENS,
        system=system_prompt,
        messages=messages,
    ) as stream:
        async for text_chunk in stream.text_stream:
            full_response += text_chunk
            # Enviar chunk al cliente via WS
            await websocket.send_json({
                "type": "tutor_chunk",
                "session_id": session_id,
                "content": text_chunk,
                "done": False,
            })

        # Obtener uso de tokens del mensaje final
        final_message = await stream.get_final_message()
        token_usage = {
            "input_tokens": final_message.usage.input_tokens,
            "output_tokens": final_message.usage.output_tokens,
        }

    # Señal de fin de stream
    await websocket.send_json({
        "type": "tutor_chunk",
        "session_id": session_id,
        "content": "",
        "done": True,
        "token_usage": token_usage,
    })

    return full_response, token_usage
```

### 1.5 Token counting — Monitoreo de costo

Cada interacción registra el uso de tokens para:
- Controlar el costo operativo por alumno
- Datos de investigación (tokens por sesión ~ profundidad del diálogo)
- Alertas si un usuario está abusando del sistema

```python
# Estructura de uso de tokens en la respuesta de Anthropic:
# response.usage.input_tokens   — tokens del system prompt + historial + mensaje del usuario
# response.usage.output_tokens  — tokens de la respuesta del asistente

# Registrar en DB (tabla tutor.messages):
await session.execute(
    text("""
        INSERT INTO tutor.messages (id, session_id, role, content, token_count, prompt_version_hash)
        VALUES (:id, :session_id, :role, :content, :token_count, :prompt_hash)
    """),
    {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "role": "assistant",
        "content": full_response,
        "token_count": token_usage["output_tokens"],
        "prompt_hash": compute_prompt_hash(system_prompt),
    }
)
```

**Costo estimado de operación**:
- `claude-sonnet-4-5`: ~$3/MTok input, ~$15/MTok output (abril 2026, verificar precios actuales)
- Sesión típica de 30 mensajes: ~2000 tokens input acumulados + ~1500 tokens output total
- Costo por sesión: ~$0.03
- 100 alumnos × 2 sesiones/día = ~$6/día

### 1.6 Manejo de errores

```python
# app/services/tutor/error_handling.py
import anthropic
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

async def call_anthropic_with_error_handling(func, *args, **kwargs):
    """Wrapper que maneja todos los errores de la API de Anthropic."""
    try:
        return await func(*args, **kwargs)

    except anthropic.RateLimitError as e:
        # Anthropic limita requests — esperar y reintentar
        logger.warning("Anthropic rate limit alcanzado", extra={"error": str(e)})
        raise HTTPException(
            status_code=429,
            detail="El servicio de tutor está temporalmente saturado. Intentá en un momento.",
        )

    except anthropic.APITimeoutError as e:
        # Request demoró más de ANTHROPIC_TIMEOUT segundos
        logger.error("Timeout en Anthropic API", extra={"error": str(e)})
        raise HTTPException(
            status_code=504,
            detail="El tutor demoró demasiado en responder. Intentá de nuevo.",
        )

    except anthropic.APIConnectionError as e:
        # No se pudo conectar a la API de Anthropic
        logger.critical("No se puede conectar a Anthropic API", extra={"error": str(e)})
        raise HTTPException(
            status_code=503,
            detail="El servicio de tutor no está disponible en este momento.",
        )

    except anthropic.AuthenticationError as e:
        # API key inválida — error de configuración
        logger.critical("ANTHROPIC_API_KEY inválida", extra={"error": str(e)})
        raise HTTPException(
            status_code=500,
            detail="Error de configuración del sistema.",
        )

    except anthropic.BadRequestError as e:
        # Request malformado (contexto demasiado largo, etc.)
        logger.error("Bad request a Anthropic", extra={"error": str(e)})
        if "context_length_exceeded" in str(e):
            raise HTTPException(
                status_code=400,
                detail="La conversación es demasiado larga. Iniciá una nueva sesión.",
            )
        raise HTTPException(status_code=400, detail="Error en la solicitud al tutor.")

    except anthropic.APIStatusError as e:
        # Otros errores HTTP de Anthropic
        logger.error("Error de API Anthropic", extra={"status": e.status_code, "error": str(e)})
        raise HTTPException(
            status_code=502,
            detail="Error en el servicio de tutor.",
        )
```

### 1.7 Gestión de costos — Rate limiting por alumno

El rate limiting no es solo seguridad: es control de gasto en la API de Anthropic:

```python
# Configuración de rate limits orientada al costo:
# 30 mensajes/hora por alumno
# Con sesión de ~2000 tokens input + 500 output por mensaje:
# 30 × (2000/1M × $3 + 500/1M × $15) = 30 × ($0.006 + $0.0075) = ~$0.40/hora/alumno
# Esto acota el costo máximo a $0.40/hora/alumno con uso intensivo
```

---

## 2. LLM Adapter Protocol

Para no acoplarse permanentemente a Anthropic, la integración se diseña detrás de un protocolo (interfaz) que permite swappear providers.

### 2.1 Protocolo abstracto

```python
# app/integrations/llm_protocol.py
from typing import Protocol, AsyncIterator, runtime_checkable

@runtime_checkable
class LLMMessage(Protocol):
    role: str     # "user" | "assistant" | "system"
    content: str

@runtime_checkable
class LLMAdapter(Protocol):
    """
    Protocolo que deben implementar todos los providers de LLM.
    Permite swappear entre Anthropic, OpenAI, Ollama, etc.
    """

    async def complete(
        self,
        messages: list[LLMMessage],
        system_prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        """Genera una respuesta completa (no streaming)."""
        ...

    async def stream(
        self,
        messages: list[LLMMessage],
        system_prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Genera una respuesta en streaming, yielding chunks de texto."""
        ...

    async def count_tokens(self, messages: list[LLMMessage], system_prompt: str) -> int:
        """Cuenta tokens de la conversación (para control de contexto)."""
        ...
```

### 2.2 Implementación para Anthropic

```python
# app/integrations/adapters/anthropic_adapter.py
from anthropic import AsyncAnthropic
from app.integrations.llm_protocol import LLMAdapter, LLMMessage
from typing import AsyncIterator

class AnthropicAdapter:
    """Implementación del LLMAdapter para Anthropic Claude."""

    def __init__(self, api_key: str, model: str, timeout: int = 30):
        self._client = AsyncAnthropic(api_key=api_key, timeout=timeout)
        self._model = model

    def _format_messages(self, messages: list[LLMMessage]) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in messages]

    async def complete(self, messages, system_prompt, max_tokens=2048, temperature=0.7) -> str:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=self._format_messages(messages),
        )
        return response.content[0].text

    async def stream(self, messages, system_prompt, max_tokens=2048, temperature=0.7) -> AsyncIterator[str]:
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=self._format_messages(messages),
        ) as stream:
            async for chunk in stream.text_stream:
                yield chunk

    async def count_tokens(self, messages, system_prompt) -> int:
        response = await self._client.messages.count_tokens(
            model=self._model,
            system=system_prompt,
            messages=self._format_messages(messages),
        )
        return response.input_tokens
```

### 2.3 Implementaciones futuras

```python
# app/integrations/adapters/openai_adapter.py (futuro)
class OpenAIAdapter:
    """Adapter para OpenAI GPT-4o."""
    ...

# app/integrations/adapters/ollama_adapter.py (futuro — modelos locales)
class OllamaAdapter:
    """
    Adapter para Ollama (modelos locales como Llama 3, Mistral).
    Útil para:
    - Desarrollo sin costo de API
    - Comparación de modelos para la investigación de tesis
    - Entorno sin internet
    """
    ...
```

### 2.4 Inyección del adapter

```python
# app/core/dependencies.py
from app.integrations.adapters.anthropic_adapter import AnthropicAdapter
from app.integrations.llm_protocol import LLMAdapter
from app.core.config import settings
from functools import lru_cache

@lru_cache(maxsize=1)
def get_llm_adapter() -> LLMAdapter:
    """
    Factory del adapter de LLM.
    Retorna el adapter configurado según ANTHROPIC_MODEL.
    En el futuro: seleccionar adapter según LLM_PROVIDER env var.
    """
    return AnthropicAdapter(
        api_key=settings.ANTHROPIC_API_KEY,
        model=settings.ANTHROPIC_MODEL,
        timeout=settings.ANTHROPIC_TIMEOUT,
    )

# Uso en servicio:
# llm = get_llm_adapter()
# response = await llm.complete(messages, system_prompt)
```

---

## 3. Monaco Editor

Monaco Editor es el editor de código de VS Code empaquetado como componente React. Se usa en las páginas de ejercicios para que los alumnos escriban código Python.

### 3.1 Carga lazy para no penalizar bundle inicial

Monaco pesa ~2MB gzipped. Se carga solo cuando el usuario accede a una página con ejercicios:

```typescript
// src/components/CodeEditor/CodeEditor.tsx
import { lazy, Suspense } from "react";
import type { CodeEditorProps } from "./types";

// Carga lazy del componente pesado
const MonacoEditorInner = lazy(() => import("./MonacoEditorInner"));

export function CodeEditor(props: CodeEditorProps) {
  return (
    <Suspense fallback={<EditorSkeleton />}>
      <MonacoEditorInner {...props} />
    </Suspense>
  );
}

function EditorSkeleton() {
  return (
    <div className="h-[400px] rounded-lg bg-gray-900 animate-pulse flex items-center justify-center">
      <span className="text-gray-500 text-sm">Cargando editor...</span>
    </div>
  );
}
```

### 3.2 Configuración del editor para Python

```typescript
// src/components/CodeEditor/MonacoEditorInner.tsx
import Editor, { useMonaco } from "@monaco-editor/react";
import { useEffect } from "react";
import type { editor } from "monaco-editor";
import type { CodeEditorProps } from "./types";

export default function MonacoEditorInner({
  value,
  onChange,
  readOnly = false,
  height = "400px",
  theme = "vs-dark",
}: CodeEditorProps) {
  const monaco = useMonaco();

  useEffect(() => {
    if (!monaco) return;

    // Configurar completions básicas para Python (sin Language Server)
    monaco.languages.registerCompletionItemProvider("python", {
      provideCompletionItems: (model, position) => {
        const PYTHON_BUILTINS = [
          "print", "len", "range", "input", "int", "str", "float",
          "list", "dict", "set", "tuple", "bool", "type",
          "enumerate", "zip", "map", "filter", "sorted", "reversed",
        ];
        return {
          suggestions: PYTHON_BUILTINS.map((name) => ({
            label: name,
            kind: monaco.languages.CompletionItemKind.Function,
            insertText: name,
          })),
        };
      },
    });
  }, [monaco]);

  const editorOptions: editor.IStandaloneEditorConstructionOptions = {
    minimap: { enabled: false },    // Minimap off para más espacio
    fontSize: 14,
    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
    lineNumbers: "on",
    scrollBeyondLastLine: false,
    automaticLayout: true,          // Resize automático con el container
    tabSize: 4,
    insertSpaces: true,             // Python usa espacios, no tabs
    readOnly,
    wordWrap: "on",
    suggest: {
      showKeywords: true,
      showSnippets: true,
    },
  };

  return (
    <Editor
      height={height}
      language="python"
      value={value}
      onChange={(v) => onChange?.(v ?? "")}
      theme={theme}
      options={editorOptions}
      loading={<EditorSkeleton />}
    />
  );
}
```

### 3.3 Configuración de Workers de Monaco

Monaco usa Web Workers para el análisis de código. En Vite se necesita configuración especial:

```typescript
// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    include: ["monaco-editor/esm/vs/language/json/json.worker?worker"],
    exclude: ["@monaco-editor/react"],
  },
  worker: {
    format: "es",
  },
});
```

### 3.4 Integración con el flujo de ejercicios

```typescript
// src/pages/ExercisePage/ExercisePage.tsx
import { useState } from "react";
import { CodeEditor } from "@/components/CodeEditor";
import { useSubmitCode } from "@/hooks/useSubmitCode";

export function ExercisePage({ exerciseId }: { exerciseId: string }) {
  const [code, setCode] = useState(STARTER_CODE);
  const { submit, isLoading, result } = useSubmitCode(exerciseId);

  return (
    <div className="flex flex-col gap-4">
      <CodeEditor
        value={code}
        onChange={setCode}
        height="400px"
      />
      <button
        onClick={() => submit(code)}
        disabled={isLoading}
        className="btn-primary"
      >
        {isLoading ? "Ejecutando..." : "Enviar código"}
      </button>
      {result && <ExecutionResult result={result} />}
    </div>
  );
}
```

---

## 4. Recharts

Recharts es la librería de visualización para los dashboards de analytics. Se usa en:
- Dashboard del alumno: progreso personal, intentos por ejercicio, racha de sesiones
- Dashboard del docente: métricas del curso, distribución de errores, alumnos en riesgo

### 4.1 Carga lazy

Al igual que Monaco, Recharts (~80KB gzipped) se carga solo en páginas de analytics:

```typescript
// src/components/charts/index.ts
export const ProgressChart = lazy(() =>
  import("./ProgressChart").then((m) => ({ default: m.ProgressChart }))
);
export const AttemptDistribution = lazy(() =>
  import("./AttemptDistribution").then((m) => ({ default: m.AttemptDistribution }))
);
```

### 4.2 Gráfico de progreso del alumno

```typescript
// src/components/charts/ProgressChart.tsx
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend
} from "recharts";
import type { StudentProgress } from "@/types/analytics";

interface ProgressChartProps {
  data: StudentProgress[];    // [{ date, sessionsCompleted, exercisesPassed }]
}

export function ProgressChart({ data }: ProgressChartProps) {
  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            dataKey="date"
            stroke="#9CA3AF"
            tick={{ fontSize: 12 }}
            tickFormatter={(v) => new Date(v).toLocaleDateString("es-AR", { month: "short", day: "numeric" })}
          />
          <YAxis stroke="#9CA3AF" tick={{ fontSize: 12 }} />
          <Tooltip
            contentStyle={{ backgroundColor: "#1F2937", border: "none", borderRadius: "8px" }}
            labelStyle={{ color: "#F9FAFB" }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="sessionsCompleted"
            stroke="#6366F1"
            strokeWidth={2}
            dot={{ r: 3 }}
            name="Sesiones completadas"
          />
          <Line
            type="monotone"
            dataKey="exercisesPassed"
            stroke="#10B981"
            strokeWidth={2}
            dot={{ r: 3 }}
            name="Ejercicios aprobados"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

### 4.3 Distribución de errores por tipo

```typescript
// src/components/charts/ErrorDistributionChart.tsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

const ERROR_COLORS: Record<string, string> = {
  "SyntaxError": "#EF4444",
  "TypeError": "#F97316",
  "IndexError": "#EAB308",
  "NameError": "#3B82F6",
  "LogicError": "#8B5CF6",
  "Other": "#6B7280",
};

export function ErrorDistributionChart({ data }: { data: ErrorCount[] }) {
  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={data} layout="vertical">
        <XAxis type="number" stroke="#9CA3AF" />
        <YAxis type="category" dataKey="error_type" width={100} stroke="#9CA3AF" tick={{ fontSize: 12 }} />
        <Tooltip
          contentStyle={{ backgroundColor: "#1F2937", border: "none" }}
          formatter={(value: number) => [`${value} ocurrencias`, ""]}
        />
        <Bar dataKey="count" radius={[0, 4, 4, 0]}>
          {data.map((entry) => (
            <Cell key={entry.error_type} fill={ERROR_COLORS[entry.error_type] ?? ERROR_COLORS["Other"]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
```

---

## 5. MSW — Mock Service Worker

MSW intercepta requests HTTP y WebSocket en el browser (usando un Service Worker) o en Node (en tests), sin modificar el código de producción.

### 5.1 Casos de uso

| Caso | Descripción |
|------|-------------|
| **Desarrollo sin backend** | Trabajar en el frontend con la API mockeada mientras el backend no está listo |
| **Tests unitarios** | Aislar componentes de la red real |
| **Tests de integración** | Simular casos borde (errores 500, timeouts, rate limits) |
| **Storybook** | Renderizar componentes con datos realistas sin servidor |

### 5.2 Setup básico

```typescript
// src/mocks/handlers.ts
import { http, HttpResponse, ws } from "msw";
import { MOCK_USER, MOCK_SESSIONS, MOCK_EXERCISES } from "./fixtures";

export const handlers = [
  // ── Auth ──────────────────────────────────────
  http.post("/api/v1/auth/login", async ({ request }) => {
    const body = await request.json() as { email: string; password: string };

    if (body.email === "alumno1@test.com" && body.password === "Test1234!") {
      return HttpResponse.json({
        access_token: "mock-access-token-12345",
        refresh_token: "mock-refresh-token-67890",
        token_type: "bearer",
      });
    }
    return HttpResponse.json({ detail: "Credenciales incorrectas" }, { status: 401 });
  }),

  http.get("/api/v1/auth/me", () => {
    return HttpResponse.json(MOCK_USER);
  }),

  // ── Tutor ─────────────────────────────────────
  http.post("/api/v1/tutor/sessions", () => {
    return HttpResponse.json({
      id: "mock-session-uuid",
      user_id: MOCK_USER.id,
      started_at: new Date().toISOString(),
      status: "active",
    }, { status: 201 });
  }),

  // ── Exercises ─────────────────────────────────
  http.get("/api/v1/exercises", () => {
    return HttpResponse.json({ items: MOCK_EXERCISES, total: MOCK_EXERCISES.length });
  }),

  http.get("/api/v1/exercises/:id", ({ params }) => {
    const exercise = MOCK_EXERCISES.find((e) => e.id === params.id);
    if (!exercise) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    return HttpResponse.json(exercise);
  }),

  // ── Error simulation ──────────────────────────
  http.get("/api/v1/health", () => {
    return HttpResponse.json({ status: "healthy" });
  }),
];

// ── WebSocket mock ─────────────────────────────
export const tutorWsHandler = ws.link("ws://localhost:8000/ws/tutor").on(
  "connection",
  ({ client }) => {
    client.addEventListener("message", (event) => {
      const data = JSON.parse(event.data as string);

      if (data.type === "tutor_message") {
        // Simular streaming de respuesta del tutor
        const chunks = ["¿Qué ", "estructura ", "de datos ", "pensás ", "que necesitás?"].map(
          (chunk, i) => ({ type: "tutor_chunk", content: chunk, done: i === 4 })
        );
        chunks.forEach((chunk, i) => {
          setTimeout(() => client.send(JSON.stringify(chunk)), i * 200);
        });
      }
    });
  }
);
```

### 5.3 Activación en desarrollo

```typescript
// src/mocks/browser.ts
import { setupWorker } from "msw/browser";
import { handlers } from "./handlers";

export const worker = setupWorker(...handlers);


// src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import config from "./config/env";

async function prepare() {
  if (config.enableMockApi) {
    const { worker } = await import("./mocks/browser");
    await worker.start({
      onUnhandledRequest: "warn",    // avisar en consola si hay request sin handler
    });
  }
}

prepare().then(() => {
  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
});
```

### 5.4 Activación en tests (Vitest)

```typescript
// src/tests/setup.ts
import { setupServer } from "msw/node";
import { handlers } from "../mocks/handlers";
import { afterAll, afterEach, beforeAll } from "vitest";

export const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());   // limpiar overrides por test
afterAll(() => server.close());


// vitest.config.ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: ["./src/tests/setup.ts"],
    globals: true,
  },
});
```

### 5.5 Override de handlers en tests específicos

```typescript
// src/tests/components/LoginForm.test.tsx
import { server } from "../setup";
import { http, HttpResponse } from "msw";
import { render, screen, userEvent } from "@testing-library/react";
import { LoginForm } from "@/components/auth/LoginForm";

describe("LoginForm", () => {
  it("muestra error cuando las credenciales son incorrectas", async () => {
    // Override el handler de login para este test
    server.use(
      http.post("/api/v1/auth/login", () =>
        HttpResponse.json({ detail: "Credenciales incorrectas" }, { status: 401 })
      )
    );

    render(<LoginForm />);
    await userEvent.type(screen.getByLabelText("Email"), "wrong@test.com");
    await userEvent.type(screen.getByLabelText("Contraseña"), "wrongpass");
    await userEvent.click(screen.getByRole("button", { name: /iniciar sesión/i }));

    expect(await screen.findByText("Credenciales incorrectas")).toBeInTheDocument();
  });

  it("simula timeout de red", async () => {
    server.use(
      http.post("/api/v1/auth/login", () => HttpResponse.networkError("Timeout"))
    );
    // ...
  });
});
```

---

**Referencias internas**:
- `knowledge-base/03-seguridad/02_superficie_de_ataque.md` — guardrails del tutor LLM
- `knowledge-base/04-infraestructura/01_configuracion.md` — env vars de Anthropic
- `knowledge-base/04-infraestructura/02_dependencias.md` — versiones de paquetes
- `knowledge-base/02-arquitectura/04_flujos_principales.md` — flujo completo del tutor
