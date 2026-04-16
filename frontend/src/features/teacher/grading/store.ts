import { create } from 'zustand';
import { apiClient } from '@/shared/lib/api-client';
import type { ActivitySubmission, ActivityEvaluation } from './types';

const EMPTY_SUBMISSIONS: ActivitySubmission[] = [];

interface GradingState {
  submissions: ActivitySubmission[];
  isLoading: boolean;
  error: string | null;
  currentEvaluation: ActivityEvaluation | null;
  isEvaluating: boolean;

  fetchSubmissions: (activityId: string) => Promise<void>;
  evaluateActivity: (activitySubmissionId: string) => Promise<void>;
  confirmGrade: (
    activitySubmissionId: string,
    generalScore: number,
    generalFeedback: string,
    exercises: { submission_id: string; score: number; feedback: string }[],
  ) => Promise<void>;
  clearEvaluation: () => void;
}

export const useGradingStore = create<GradingState>((set, get) => ({
  submissions: EMPTY_SUBMISSIONS,
  isLoading: false,
  error: null,
  currentEvaluation: null,
  isEvaluating: false,

  fetchSubmissions: async (activityId) => {
    set({ isLoading: true, error: null });
    try {
      const res = await apiClient.get<ActivitySubmission[]>(
        `/v1/teacher/activities/${activityId}/pending`,
      );
      set({ submissions: res.data });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Error cargando submissions' });
    } finally {
      set({ isLoading: false });
    }
  },

  evaluateActivity: async (activitySubmissionId) => {
    set({ isEvaluating: true, error: null, currentEvaluation: null });
    try {
      const res = await apiClient.post<ActivityEvaluation>(
        `/v1/teacher/activity-submissions/${activitySubmissionId}/evaluate`,
        {},
      );
      set({ currentEvaluation: res.data });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Error al evaluar con IA' });
    } finally {
      set({ isEvaluating: false });
    }
  },

  confirmGrade: async (activitySubmissionId, generalScore, generalFeedback, exercises) => {
    try {
      await apiClient.patch(
        `/v1/teacher/activity-submissions/${activitySubmissionId}/grade`,
        { general_score: generalScore, general_feedback: generalFeedback, exercises },
      );
      // Refresh
      const { submissions } = get();
      set({
        submissions: submissions.map((s) =>
          s.id === activitySubmissionId
            ? { ...s, status: 'evaluated', total_score: generalScore }
            : s,
        ),
        currentEvaluation: null,
      });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Error al confirmar nota' });
    }
  },

  clearEvaluation: () => set({ currentEvaluation: null }),
}));
