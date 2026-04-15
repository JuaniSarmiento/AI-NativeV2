export type ExerciseDifficulty = 'easy' | 'medium' | 'hard';

export interface TestCase {
  id: string;
  description: string;
  input: string;
  expected_output: string;
  is_hidden: boolean;
  weight: number;
}

export interface TestCaseSet {
  language: string;
  timeout_ms: number;
  memory_limit_mb: number;
  cases: TestCase[];
}

export interface Exercise {
  id: string;
  course_id: string;
  title: string;
  description: string;
  test_cases: TestCaseSet;
  difficulty: ExerciseDifficulty;
  topic_tags: string[];
  language: string;
  starter_code: string;
  max_attempts: number;
  time_limit_minutes: number;
  order_index: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ExerciseSummary {
  id: string;
  course_id: string;
  title: string;
  difficulty: ExerciseDifficulty;
  topic_tags: string[];
  language: string;
  order_index: number;
}
