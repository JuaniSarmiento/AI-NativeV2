import { create } from 'zustand';
import { apiClient } from '@/shared/lib/api-client';
import type {
  Course,
  Commission,
  StudentCourse,
  CourseCreateData,
  CommissionCreateData,
} from './types';

interface CoursesState {
  courses: Course[];
  commissions: Commission[];
  studentCourses: StudentCourse[];
  totalCourses: number;
  totalCommissions: number;
  isLoading: boolean;

  fetchCourses: (page?: number, perPage?: number) => Promise<void>;
  createCourse: (data: CourseCreateData) => Promise<void>;
  updateCourse: (id: string, data: Partial<CourseCreateData>) => Promise<void>;
  deleteCourse: (id: string) => Promise<void>;
  fetchCommissions: (courseId: string, page?: number, perPage?: number) => Promise<void>;
  createCommission: (courseId: string, data: CommissionCreateData) => Promise<void>;
  updateCommission: (id: string, data: Partial<CommissionCreateData>) => Promise<void>;
  deleteCommission: (id: string) => Promise<void>;
  enroll: (commissionId: string) => Promise<void>;
  fetchStudentCourses: () => Promise<void>;
}

export const useCoursesStore = create<CoursesState>((set) => ({
  courses: [],
  commissions: [],
  studentCourses: [],
  totalCourses: 0,
  totalCommissions: 0,
  isLoading: false,

  fetchCourses: async (page = 1, perPage = 20) => {
    set({ isLoading: true });
    try {
      const res = await apiClient.get<Course[]>(
        `/v1/courses?page=${page}&per_page=${perPage}`,
      );
      set({
        courses: res.data,
        totalCourses: res.meta?.total ?? 0,
      });
    } finally {
      set({ isLoading: false });
    }
  },

  createCourse: async (data) => {
    await apiClient.post('/v1/courses', data);
  },

  updateCourse: async (id, data) => {
    await apiClient.put(`/v1/courses/${id}`, data);
  },

  deleteCourse: async (id) => {
    await apiClient.delete(`/v1/courses/${id}`);
  },

  fetchCommissions: async (courseId, page = 1, perPage = 20) => {
    set({ isLoading: true });
    try {
      const res = await apiClient.get<Commission[]>(
        `/v1/courses/${courseId}/commissions?page=${page}&per_page=${perPage}`,
      );
      set({
        commissions: res.data,
        totalCommissions: res.meta?.total ?? 0,
      });
    } finally {
      set({ isLoading: false });
    }
  },

  createCommission: async (courseId, data) => {
    await apiClient.post(`/v1/courses/${courseId}/commissions`, data);
  },

  updateCommission: async (id, data) => {
    await apiClient.put(`/v1/commissions/${id}`, data);
  },

  deleteCommission: async (id) => {
    await apiClient.delete(`/v1/commissions/${id}`);
  },

  enroll: async (commissionId) => {
    await apiClient.post(`/v1/commissions/${commissionId}/enroll`, {});
  },

  fetchStudentCourses: async () => {
    set({ isLoading: true });
    try {
      const res = await apiClient.get<StudentCourse[]>('/v1/student/courses');
      set({ studentCourses: Array.isArray(res.data) ? res.data : [] });
    } finally {
      set({ isLoading: false });
    }
  },
}));
