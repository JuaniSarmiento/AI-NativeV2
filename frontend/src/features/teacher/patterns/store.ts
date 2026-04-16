import { create } from 'zustand';
import { apiClient } from '@/shared/lib/api-client';
import type { PatternSession } from './types';

const EMPTY_SESSIONS: PatternSession[] = [];

interface PatternsState {
  sessions: PatternSession[];
  isLoading: boolean;
  error: string | null;

  fetchSessions: (commissionId: string, exerciseId: string) => Promise<void>;
}

export const usePatternsStore = create<PatternsState>((set) => ({
  sessions: EMPTY_SESSIONS,
  isLoading: false,
  error: null,

  fetchSessions: async (commissionId, exerciseId) => {
    set({ isLoading: true, error: null });
    try {
      const res = await apiClient.get<PatternSession[]>(
        `/v1/cognitive/sessions?commission_id=${commissionId}&exercise_id=${exerciseId}&per_page=100`,
      );
      set({ sessions: res.data });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Error cargando patrones' });
    } finally {
      set({ isLoading: false });
    }
  },
}));
