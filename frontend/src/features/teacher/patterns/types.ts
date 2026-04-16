export interface PatternSession {
  id: string;
  student_id: string;
  exercise_id: string;
  started_at: string;
  closed_at: string | null;
  status: string;
}

export interface PatternMetrics {
  session_id: string;
  n1_comprehension_score: number | null;
  n2_strategy_score: number | null;
  n3_validation_score: number | null;
  n4_ai_interaction_score: number | null;
  qe_score: number | null;
  success_efficiency: number | null;
  risk_level: string | null;
  total_interactions: number;
}
