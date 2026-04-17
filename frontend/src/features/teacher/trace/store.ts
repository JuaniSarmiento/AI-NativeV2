import { create } from 'zustand';
import { apiClient } from '@/shared/lib/api-client';
import type { TraceData, TraceSession, TraceMetrics, TraceEvent, VerifyResult, CodeSnapshot, ChatMessage } from './types';

const EMPTY_EVENTS: TraceEvent[] = [];
const EMPTY_SNAPSHOTS: CodeSnapshot[] = [];
const EMPTY_MESSAGES: ChatMessage[] = [];

interface TraceState {
  session: TraceSession | null;
  studentName: string | null;
  studentEmail: string | null;
  exerciseTitle: string | null;
  events: TraceEvent[];
  metrics: TraceMetrics | null;
  verification: VerifyResult | null;
  snapshots: CodeSnapshot[];
  chatMessages: ChatMessage[];
  isLoading: boolean;
  error: string | null;

  fetchTrace: (sessionId: string) => Promise<void>;
  clear: () => void;
}

export const useTraceStore = create<TraceState>((set) => ({
  session: null,
  studentName: null,
  studentEmail: null,
  exerciseTitle: null,
  events: EMPTY_EVENTS,
  metrics: null,
  verification: null,
  snapshots: EMPTY_SNAPSHOTS,
  chatMessages: EMPTY_MESSAGES,
  isLoading: false,
  error: null,

  fetchTrace: async (sessionId) => {
    set({ isLoading: true, error: null });
    try {
      const traceRes = await apiClient.get<TraceData>(`/v1/cognitive/sessions/${sessionId}/trace`);
      const trace = traceRes.data;

      set({
        session: trace.session,
        studentName: trace.student_name,
        studentEmail: trace.student_email,
        exerciseTitle: trace.exercise_title,
        events: trace.timeline ?? trace.session.events ?? EMPTY_EVENTS,
        metrics: trace.metrics,
        verification: trace.verification,
        snapshots: trace.code_evolution ?? EMPTY_SNAPSHOTS,
        chatMessages: trace.chat ?? EMPTY_MESSAGES,
      });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Error cargando traza' });
    } finally {
      set({ isLoading: false });
    }
  },

  clear: () =>
    set({
      session: null,
      studentName: null,
      studentEmail: null,
      exerciseTitle: null,
      events: EMPTY_EVENTS,
      metrics: null,
      verification: null,
      snapshots: EMPTY_SNAPSHOTS,
      chatMessages: EMPTY_MESSAGES,
      isLoading: false,
      error: null,
    }),
}));
