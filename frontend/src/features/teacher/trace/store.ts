import { create } from 'zustand';
import { apiClient } from '@/shared/lib/api-client';
import type { TraceData, TraceSession, TraceMetrics, TraceEvent, VerifyResult, CodeSnapshot, ChatMessage } from './types';

const EMPTY_EVENTS: TraceEvent[] = [];
const EMPTY_SNAPSHOTS: CodeSnapshot[] = [];
const EMPTY_MESSAGES: ChatMessage[] = [];

interface TraceState {
  session: TraceSession | null;
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
      // Fetch trace, code evolution, and chat in parallel
      const [traceRes, codeRes] = await Promise.all([
        apiClient.get<TraceData>(`/v1/cognitive/sessions/${sessionId}/trace`),
        apiClient.get<CodeSnapshot[]>(`/v1/cognitive/sessions/${sessionId}/code-evolution`),
      ]);

      const trace = traceRes.data;
      const exerciseId = trace.session.exercise_id;

      // Chat fetched via teacher endpoint (docente can read any student's chat)
      const studentId = trace.session.student_id;
      let chatMessages: ChatMessage[] = EMPTY_MESSAGES;
      try {
        const chatRes = await apiClient.get<ChatMessage[]>(
          `/v1/teacher/students/${studentId}/exercises/${exerciseId}/messages`,
        );
        chatMessages = chatRes.data;
      } catch {
        // Chat may not exist for all sessions
      }

      set({
        session: trace.session,
        events: trace.session.events ?? EMPTY_EVENTS,
        metrics: trace.metrics,
        verification: trace.verification,
        snapshots: codeRes.data ?? EMPTY_SNAPSHOTS,
        chatMessages,
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
      events: EMPTY_EVENTS,
      metrics: null,
      verification: null,
      snapshots: EMPTY_SNAPSHOTS,
      chatMessages: EMPTY_MESSAGES,
      isLoading: false,
      error: null,
    }),
}));
