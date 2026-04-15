import { create } from 'zustand';
import { apiClient } from '@/shared/lib/api-client';
import type { Exercise, ExerciseSummary, ExerciseDifficulty, TestCaseSet } from './types';

interface ExercisesState {
  exercises: ExerciseSummary[];
  currentExercise: Exercise | null;
  totalExercises: number;
  isLoading: boolean;

  fetchCourseExercises: (courseId: string, page?: number, difficulty?: ExerciseDifficulty, topic?: string) => Promise<void>;
  fetchStudentExercises: (page?: number, difficulty?: ExerciseDifficulty, topic?: string) => Promise<void>;
  fetchExercise: (id: string) => Promise<void>;
  createExercise: (courseId: string, data: {
    title: string;
    description: string;
    test_cases: TestCaseSet;
    difficulty: ExerciseDifficulty;
    topic_tags: string[];
    starter_code?: string;
  }) => Promise<void>;
  updateExercise: (id: string, data: Record<string, unknown>) => Promise<void>;
  deleteExercise: (id: string) => Promise<void>;
}

export const useExercisesStore = create<ExercisesState>((set) => ({
  exercises: [],
  currentExercise: null,
  totalExercises: 0,
  isLoading: false,

  fetchCourseExercises: async (courseId, page = 1, difficulty, topic) => {
    set({ isLoading: true });
    try {
      let url = `/v1/courses/${courseId}/exercises?page=${page}`;
      if (difficulty) url += `&difficulty=${difficulty}`;
      if (topic) url += `&topic=${topic}`;
      const res = await apiClient.get<ExerciseSummary[]>(url);
      set({ exercises: res.data, totalExercises: res.meta?.total ?? 0 });
    } finally {
      set({ isLoading: false });
    }
  },

  fetchStudentExercises: async (page = 1, difficulty, topic) => {
    set({ isLoading: true });
    try {
      let url = `/v1/student/exercises?page=${page}`;
      if (difficulty) url += `&difficulty=${difficulty}`;
      if (topic) url += `&topic=${topic}`;
      const res = await apiClient.get<ExerciseSummary[]>(url);
      set({ exercises: res.data, totalExercises: res.meta?.total ?? 0 });
    } finally {
      set({ isLoading: false });
    }
  },

  fetchExercise: async (id) => {
    set({ isLoading: true });
    try {
      const res = await apiClient.get<Exercise>(`/v1/exercises/${id}`);
      set({ currentExercise: res.data });
    } finally {
      set({ isLoading: false });
    }
  },

  createExercise: async (courseId, data) => {
    await apiClient.post(`/v1/courses/${courseId}/exercises`, data);
  },

  updateExercise: async (id, data) => {
    await apiClient.put(`/v1/exercises/${id}`, data);
  },

  deleteExercise: async (id) => {
    await apiClient.delete(`/v1/exercises/${id}`);
  },
}));
