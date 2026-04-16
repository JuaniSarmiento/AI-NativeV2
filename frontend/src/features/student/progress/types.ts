export interface ProgressSession {
  session_id: string;
  exercise_id: string;
  n1_comprehension_score: number | null;
  n2_strategy_score: number | null;
  n3_validation_score: number | null;
  n4_ai_interaction_score: number | null;
  qe_score: number | null;
  autonomy_index: number | null;
  success_efficiency: number | null;
  computed_at: string | null;
}

export interface ProgressData {
  sessions: ProgressSession[];
  session_count: number;
  avg_n1: number | null;
  avg_n2: number | null;
  avg_n3: number | null;
  avg_n4: number | null;
  avg_qe: number | null;
}

export interface ScoreCardData {
  label: string;
  score: number | null;
  previousScore: number | null;
}
