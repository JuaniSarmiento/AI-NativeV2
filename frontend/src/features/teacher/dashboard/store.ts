import { create } from 'zustand';
import { apiClient } from '@/shared/lib/api-client';
import type { DashboardData, RiskAssessment, SortField, SortDirection } from './types';

const EMPTY_RISKS: RiskAssessment[] = [];

interface TeacherDashboardState {
  dashboard: DashboardData | null;
  isLoading: boolean;
  error: string | null;
  selectedStudentId: string | null;
  sortField: SortField;
  sortDirection: SortDirection;
  riskFilter: string | null;

  risks: RiskAssessment[];
  isLoadingRisks: boolean;

  fetchDashboard: (courseId: string, commissionId: string, exerciseId?: string) => Promise<void>;
  setSelectedStudent: (id: string | null) => void;
  setSort: (field: SortField) => void;
  setRiskFilter: (level: string | null) => void;

  fetchRisks: (commissionId: string) => Promise<void>;
  acknowledgeRisk: (riskId: string) => Promise<void>;
  triggerAssessment: (commissionId: string) => Promise<void>;
}

export const useTeacherDashboardStore = create<TeacherDashboardState>((set, get) => ({
  dashboard: null,
  isLoading: false,
  error: null,
  selectedStudentId: null,
  sortField: 'student_name',
  sortDirection: 'asc',
  riskFilter: null,

  risks: EMPTY_RISKS,
  isLoadingRisks: false,

  fetchDashboard: async (courseId, commissionId, exerciseId) => {
    set({ isLoading: true, error: null, dashboard: null });
    try {
      let path = `/v1/teacher/courses/${courseId}/dashboard?commission_id=${commissionId}`;
      if (exerciseId) path += `&exercise_id=${exerciseId}`;
      const res = await apiClient.get<DashboardData>(path);
      set({ dashboard: res.data });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Error cargando dashboard' });
    } finally {
      set({ isLoading: false });
    }
  },

  setSelectedStudent: (id) => set({ selectedStudentId: id }),

  setSort: (field) => {
    const { sortField, sortDirection } = get();
    if (sortField === field) {
      set({ sortDirection: sortDirection === 'asc' ? 'desc' : 'asc' });
    } else {
      set({ sortField: field, sortDirection: 'desc' });
    }
  },

  setRiskFilter: (level) => set({ riskFilter: level }),

  fetchRisks: async (commissionId) => {
    set({ isLoadingRisks: true, risks: EMPTY_RISKS, error: null });
    try {
      const res = await apiClient.get<RiskAssessment[]>(
        `/v1/teacher/commissions/${commissionId}/risks?per_page=100`,
      );
      set({ risks: res.data });
    } catch {
      set({ risks: EMPTY_RISKS });
    } finally {
      set({ isLoadingRisks: false });
    }
  },

  acknowledgeRisk: async (riskId) => {
    try {
      const res = await apiClient.patch<RiskAssessment>(
        `/v1/teacher/risks/${riskId}/acknowledge`,
        {},
      );
      const updated = res.data;
      set((state) => ({
        risks: state.risks.map((r) => (r.id === riskId ? updated : r)),
      }));
    } catch {
      // silent
    }
  },

  triggerAssessment: async (commissionId) => {
    try {
      await apiClient.post(`/v1/teacher/commissions/${commissionId}/risks/assess`, {});
      await get().fetchRisks(commissionId);
    } catch {
      // silent
    }
  },
}));
