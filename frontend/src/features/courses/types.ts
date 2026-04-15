export interface Course {
  id: string;
  name: string;
  description: string | null;
  topic_taxonomy: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Commission {
  id: string;
  course_id: string;
  teacher_id: string;
  name: string;
  year: number;
  semester: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Enrollment {
  id: string;
  student_id: string;
  commission_id: string;
  enrolled_at: string;
  is_active: boolean;
}

export interface StudentCourse {
  course_id: string;
  course_name: string;
  commission_id: string;
  commission_name: string;
  teacher_name: string;
  year: number;
  semester: number;
  enrolled_at: string;
}

export interface CourseCreateData {
  name: string;
  description?: string;
  topic_taxonomy?: Record<string, unknown>;
}

export interface CommissionCreateData {
  name: string;
  teacher_id: string;
  year: number;
  semester: number;
}
