import { create } from 'zustand';
import { apiClient } from '@/shared/lib/api-client';
import type { Activity, LLMConfig, LLMConfigSaveData } from './types';

interface ActivitiesState {
  activities: Activity[];
  currentActivity: Activity | null;
  llmConfig: LLMConfig | null;
  totalActivities: number;
  isLoading: boolean;
  isGenerating: boolean;

  fetchActivities: (page?: number) => Promise<void>;
  fetchActivity: (id: string) => Promise<void>;
  generateActivity: (courseId: string, prompt: string) => Promise<Activity>;
  publishActivity: (id: string) => Promise<void>;
  deleteActivity: (id: string) => Promise<void>;
  fetchLLMConfig: () => Promise<void>;
  saveLLMConfig: (data: LLMConfigSaveData) => Promise<void>;
}

export const useActivitiesStore = create<ActivitiesState>((set, get) => ({
  activities: [],
  currentActivity: null,
  llmConfig: null,
  totalActivities: 0,
  isLoading: false,
  isGenerating: false,

  fetchActivities: async (page = 1) => {
    set({ isLoading: true });
    try {
      const res = await apiClient.get<Activity[]>(`/v1/activities?page=${page}`);
      set({ activities: res.data, totalActivities: res.meta?.total ?? 0 });
    } finally {
      set({ isLoading: false });
    }
  },

  fetchActivity: async (id) => {
    set({ isLoading: true });
    try {
      const res = await apiClient.get<Activity>(`/v1/activities/${id}`);
      set({ currentActivity: res.data });
    } finally {
      set({ isLoading: false });
    }
  },

  generateActivity: async (courseId, prompt) => {
    set({ isGenerating: true });
    try {
      const res = await apiClient.post<Activity>('/v1/activities/generate', {
        course_id: courseId,
        prompt,
      });
      return res.data;
    } finally {
      set({ isGenerating: false });
    }
  },

  publishActivity: async (id) => {
    await apiClient.post(`/v1/activities/${id}/publish`, {});
  },

  deleteActivity: async (id) => {
    await apiClient.delete(`/v1/activities/${id}`);
  },

  fetchLLMConfig: async () => {
    try {
      const res = await apiClient.get<LLMConfig | null>('/v1/settings/llm');
      set({ llmConfig: res.data });
    } catch {
      set({ llmConfig: null });
    }
  },

  saveLLMConfig: async (data) => {
    await apiClient.put('/v1/settings/llm', data);
    set({
      llmConfig: { provider: data.provider, model_name: data.model_name, has_key: true },
    });
  },
}));
