import { create } from 'zustand';
import { apiClient } from '@/shared/lib/api-client';
import type { GovernanceEvent, PromptHistory } from './types';

const EMPTY_EVENTS: GovernanceEvent[] = [];
const EMPTY_PROMPTS: PromptHistory[] = [];

interface GovernanceState {
  events: GovernanceEvent[];
  eventsTotal: number;
  prompts: PromptHistory[];
  promptsTotal: number;
  isLoadingEvents: boolean;
  isLoadingPrompts: boolean;
  error: string | null;

  fetchEvents: (page?: number, eventType?: string) => Promise<void>;
  fetchPrompts: (page?: number) => Promise<void>;
}

export const useGovernanceStore = create<GovernanceState>((set) => ({
  events: EMPTY_EVENTS,
  eventsTotal: 0,
  prompts: EMPTY_PROMPTS,
  promptsTotal: 0,
  isLoadingEvents: false,
  isLoadingPrompts: false,
  error: null,

  fetchEvents: async (page = 1, eventType) => {
    set({ isLoadingEvents: true, error: null });
    try {
      let path = `/v1/governance/events?page=${page}&per_page=20`;
      if (eventType) path += `&event_type=${eventType}`;
      const res = await apiClient.get<GovernanceEvent[]>(path);
      set({
        events: res.data,
        eventsTotal: (res.meta as Record<string, number>)?.total ?? 0,
      });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Error cargando eventos' });
    } finally {
      set({ isLoadingEvents: false });
    }
  },

  fetchPrompts: async (page = 1) => {
    set({ isLoadingPrompts: true, error: null });
    try {
      const res = await apiClient.get<PromptHistory[]>(`/v1/governance/prompts?page=${page}&per_page=20`);
      set({
        prompts: res.data,
        promptsTotal: (res.meta as Record<string, number>)?.total ?? 0,
      });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Error cargando prompts' });
    } finally {
      set({ isLoadingPrompts: false });
    }
  },
}));
