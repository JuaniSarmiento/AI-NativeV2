import { create } from 'zustand';
import { apiClient } from '@/shared/lib/api-client';
import type { ProgressData } from './types';

interface StudentProgressState {
  progress: ProgressData | null;
  isLoading: boolean;
  error: string | null;

  fetchProgress: (page?: number, perPage?: number) => Promise<void>;
}

export const useStudentProgressStore = create<StudentProgressState>((set) => ({
  progress: null,
  isLoading: false,
  error: null,

  fetchProgress: async (page = 1, perPage = 50) => {
    set({ isLoading: true, error: null });
    try {
      const res = await apiClient.get<ProgressData>(
        `/v1/student/me/progress?page=${page}&per_page=${perPage}`,
      );
      set({ progress: res.data });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Error cargando progreso' });
    } finally {
      set({ isLoading: false });
    }
  },
}));
