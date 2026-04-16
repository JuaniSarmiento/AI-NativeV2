export interface ExerciseSubmission {
  id: string;
  student_id: string;
  exercise_id: string;
  code: string;
  status: string;
  score: number | null;
  feedback: string | null;
  attempt_number: number;
  submitted_at: string;
  evaluated_at: string | null;
}

export interface ActivitySubmission {
  id: string;
  activity_id: string;
  student_id: string;
  student_name: string;
  attempt_number: number;
  status: string;
  total_score: number | null;
  submitted_at: string;
  submissions: ExerciseSubmission[];
}

export interface ExerciseEvaluation {
  submission_id: string;
  exercise_id: string;
  exercise_title: string;
  score: number;
  feedback: string;
  strengths: string[];
  improvements: string[];
}

export interface ActivityEvaluation {
  activity_submission_id: string;
  general_score: number;
  general_feedback: string;
  exercises: ExerciseEvaluation[];
}
