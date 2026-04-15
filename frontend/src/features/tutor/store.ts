import { create } from 'zustand';
import type { TutorMessage, ConnectionStatus } from './types';

interface TutorState {
  messages: TutorMessage[];
  connectionStatus: ConnectionStatus;
  isStreaming: boolean;
  remainingMessages: number | null;
  resetAt: string | null;
  currentExerciseId: string | null;
  sessionId: string | null;

  addMessage: (msg: TutorMessage) => void;
  appendToLastMessage: (content: string) => void;
  finishStreaming: (interactionId: string) => void;
  setStreaming: (streaming: boolean) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  setRateLimit: (remaining: number, resetAt: string) => void;
  setExerciseId: (id: string) => void;
  setSessionId: (id: string) => void;
  clearMessages: () => void;
}

export const useTutorStore = create<TutorState>((set) => ({
  messages: [],
  connectionStatus: 'disconnected',
  isStreaming: false,
  remainingMessages: null,
  resetAt: null,
  currentExerciseId: null,
  sessionId: null,

  addMessage: (msg) =>
    set((state) => ({ messages: [...state.messages, msg] })),

  appendToLastMessage: (content) =>
    set((state) => {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === 'assistant' && last.isStreaming) {
        msgs[msgs.length - 1] = { ...last, content: last.content + content };
      }
      return { messages: msgs };
    }),

  finishStreaming: (interactionId) =>
    set((state) => {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.isStreaming) {
        msgs[msgs.length - 1] = { ...last, id: interactionId, isStreaming: false };
      }
      return { messages: msgs, isStreaming: false };
    }),

  setStreaming: (streaming) => set({ isStreaming: streaming }),

  setConnectionStatus: (status) => set({ connectionStatus: status }),

  setRateLimit: (remaining, resetAt) =>
    set({ remainingMessages: remaining, resetAt }),

  setExerciseId: (id) =>
    set((state) =>
      state.currentExerciseId !== id
        ? { currentExerciseId: id, messages: [], sessionId: null }
        : {},
    ),

  setSessionId: (id) => set({ sessionId: id }),

  clearMessages: () => set({ messages: [], sessionId: null }),
}));
