---
name: zustand-store-pattern
description: >
  Impone patrones de Zustand 5 con selectores individuales, useShallow para
  objetos y arrays, refs estables como fallback, un store por dominio y acciones
  dentro del store. Previene re-renders innecesarios y suscripciones globales al
  store. Trigger: al trabajar con Zustand stores, componentes React que consumen
  stores, o gestión de estado en la plataforma AI-Native.
license: Apache-2.0
metadata:
  author: ai-native
  version: "1.0"
---

## Cuándo Usar

- Al crear un nuevo store de Zustand para un dominio (tutor, evaluaciones, CTR)
- Al consumir un store en un componente React
- Al integrar WebSocket con estado de la UI
- Al persistir estado offline con middleware `persist`
- Al revisar un componente que se re-renderiza en exceso

## Patrones Críticos

### 1. Store con estado tipado, acciones y selectores externos

El store exporta el hook y selectores individuales. Las acciones viven dentro
del store. Nunca se exporta el `set` crudo ni se muta estado fuera del store.

```typescript
// stores/tutor-store.ts
import { create } from "zustand";

interface Interaction {
  id: string;
  question: string;
  hint: string;
  timestamp: number;
}

interface TutorState {
  sessionId: string | null;
  interactions: Interaction[];
  isLoading: boolean;
  error: string | null;
}

interface TutorActions {
  setSession: (id: string) => void;
  addInteraction: (item: Interaction) => void;
  setLoading: (loading: boolean) => void;
  setError: (msg: string | null) => void;
  reset: () => void;
}

const initialState: TutorState = {
  sessionId: null,
  interactions: [],
  isLoading: false,
  error: null,
};

export const useTutorStore = create<TutorState & TutorActions>((set) => ({
  ...initialState,
  setSession: (id) => set({ sessionId: id }),
  addInteraction: (item) =>
    set((s) => ({ interactions: [...s.interactions, item] })),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (msg) => set({ error: msg }),
  reset: () => set(initialState),
}));

// Selectores externos — un selector por campo atómico
export const selectSessionId = (s: TutorState & TutorActions) => s.sessionId;
export const selectIsLoading = (s: TutorState & TutorActions) => s.isLoading;
export const selectInteractions = (s: TutorState & TutorActions) =>
  s.interactions;
export const selectError = (s: TutorState & TutorActions) => s.error;
```

### 2. Componente usando useShallow + ref estable como fallback

`useShallow` se usa cuando se selecciona un objeto o array para que Zustand
haga comparación estructural superficial y no dispare un re-render por nueva
referencia. El fallback de arrays vacíos se declara fuera del componente para
no crear una referencia nueva en cada render.

```typescript
// components/InteractionList.tsx
import { useShallow } from "zustand/react/shallow";
import { useTutorStore, selectInteractions } from "@/stores/tutor-store";

// Ref estable — declarada fuera del componente, nunca inline
const EMPTY_INTERACTIONS: Interaction[] = [];

export function InteractionList() {
  // useShallow para array: evita re-render cuando la referencia cambia
  // pero el contenido es el mismo
  const interactions = useTutorStore(
    useShallow((s) => s.interactions ?? EMPTY_INTERACTIONS)
  );

  // Selector atómico (primitivo) — no necesita useShallow
  const isLoading = useTutorStore((s) => s.isLoading);

  if (isLoading) return <LoadingSpinner />;
  return (
    <ul>
      {interactions.map((i) => (
        <li key={i.id}>{i.hint}</li>
      ))}
    </ul>
  );
}
```

### 3. Integración WebSocket via ref que actualiza el store por acciones

El WebSocket vive en un `ref` para no causar re-renders. Actualiza el store
únicamente a través de las acciones exportadas, nunca accediendo a `setState`
directamente.

```typescript
// hooks/useTutorSocket.ts
import { useEffect, useRef } from "react";
import { useTutorStore } from "@/stores/tutor-store";

export function useTutorSocket(sessionId: string) {
  const wsRef = useRef<WebSocket | null>(null);

  // Extraer acciones estables (no son estado, no cambian entre renders)
  const addInteraction = useTutorStore((s) => s.addInteraction);
  const setError = useTutorStore((s) => s.setError);

  useEffect(() => {
    const ws = new WebSocket(`${import.meta.env.VITE_WS_URL}/tutor/${sessionId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data) as Interaction;
      addInteraction(data);   // store actualizado por acción, no por setState
    };

    ws.onerror = () => setError("Conexión interrumpida");

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [sessionId, addInteraction, setError]);

  return wsRef;
}
```

### 4. Persist middleware con partialize para offline

Solo se persiste la parte del estado necesaria para la experiencia offline.
Las acciones nunca se serializan. Se usa `partialize` para excluirlas.

```typescript
// stores/evaluation-store.ts
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface EvaluationState {
  pendingSubmissions: PendingEvaluation[];
  lastSyncAt: number | null;
}

interface EvaluationActions {
  queueSubmission: (eval: PendingEvaluation) => void;
  clearQueue: () => void;
  markSynced: () => void;
}

export const useEvaluationStore = create<EvaluationState & EvaluationActions>()(
  persist(
    (set) => ({
      pendingSubmissions: [],
      lastSyncAt: null,
      queueSubmission: (e) =>
        set((s) => ({ pendingSubmissions: [...s.pendingSubmissions, e] })),
      clearQueue: () => set({ pendingSubmissions: [] }),
      markSynced: () => set({ lastSyncAt: Date.now() }),
    }),
    {
      name: "ai-native-evaluations",
      storage: createJSONStorage(() => localStorage),
      // Solo persistir estado, nunca acciones
      partialize: (s) => ({
        pendingSubmissions: s.pendingSubmissions,
        lastSyncAt: s.lastSyncAt,
      }),
    }
  )
);
```

## Anti-patrones

### Desestructurar el store (suscripción a todo el estado)

```typescript
// NO — suscribe el componente a CUALQUIER cambio del store
const { sessionId, interactions, isLoading } = useTutorStore();

// SI — selector individual, re-render solo cuando cambia ese campo
const sessionId = useTutorStore((s) => s.sessionId);
const interactions = useTutorStore(useShallow((s) => s.interactions));
const isLoading = useTutorStore((s) => s.isLoading);
```

### Fallback inline de array vacío (nueva referencia en cada render)

```typescript
// NO — [] nuevo en cada render dispara re-render aunque no haya cambios
const interactions = useTutorStore((s) => s.interactions ?? []);

// SI — referencia estable fuera del componente
const EMPTY: Interaction[] = [];
const interactions = useTutorStore(useShallow((s) => s.interactions ?? EMPTY));
```

### Estado de formulario en Zustand

```typescript
// NO — Zustand no es el lugar para estado efímero de formularios
const useTutorStore = create((set) => ({
  questionDraft: "",          // ← estado local de formulario en store global
  setQuestionDraft: (v) => set({ questionDraft: v }),
}));

// SI — estado local con useState o React Hook Form para formularios
function AskForm() {
  const [draft, setDraft] = useState("");
  // o: const { register, handleSubmit } = useForm();
}
```

## Checklist

- [ ] Cada dominio tiene su propio store (`tutor-store`, `evaluation-store`, etc.)
- [ ] Las acciones están definidas dentro del `create()`, no fuera
- [ ] Los selectores de objetos/arrays usan `useShallow`
- [ ] Los fallbacks de arrays vacíos son refs estables fuera del componente
- [ ] El WebSocket vive en un `useRef`, no en estado de Zustand
- [ ] `partialize` excluye todas las funciones/acciones al persistir
- [ ] Ningún componente desestructura el store sin selector
- [ ] Estado de formularios usa `useState` o React Hook Form, no el store global
