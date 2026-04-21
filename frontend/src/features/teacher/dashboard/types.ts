export type AppropriationType = 'Delegacion' | 'Superficial' | 'Reflexiva' | 'Autonomo';

/** Individual condition within a score dimension breakdown */
export interface ScoreCondition {
  condition: string;
  met: boolean;
  points: number;
}

/** Condition-list breakdown returned by the backend as latest_score_breakdown */
export interface ScoreBreakdown {
  n1: ScoreCondition[];
  n2: ScoreCondition[];
  n3: ScoreCondition[];
  n4: ScoreCondition[];
  qe: ScoreCondition[];
}

export interface StudentSummary {
  student_id: string;
  student_name: string | null;
  student_email: string | null;
  session_count: number;
  latest_n1: number | null;
  latest_n2: number | null;
  latest_n3: number | null;
  latest_n4: number | null;
  latest_qe: number | null;
  latest_risk_level: string | null;
  avg_dependency: number | null;
  // Phase 7 — new backend fields
  latest_temporal_coherence: number | null;
  latest_code_discourse: number | null;
  latest_inter_iteration: number | null;
  latest_appropriation_type: AppropriationType | null;
  latest_score_breakdown: ScoreBreakdown | null;
}

export interface DashboardData {
  commission_id: string;
  exercise_id: string | null;
  student_count: number;
  avg_n1: number | null;
  avg_n2: number | null;
  avg_n3: number | null;
  avg_n4: number | null;
  avg_qe: number | null;
  avg_dependency: number | null;
  risk_distribution: Record<string, number>;
  students: StudentSummary[];
}

export interface RadarDataPoint {
  dimension: string;
  score: number;
  studentScore?: number;
  fullMark: number;
}

export const N4_LABELS: Record<'n1' | 'n2' | 'n3' | 'n4', string> = {
  n1: 'Comprension',
  n2: 'Estrategia',
  n3: 'Validacion',
  n4: 'Interaccion IA',
};

export type SortField =
  | 'student_name'
  | 'session_count'
  | 'latest_n1'
  | 'latest_n2'
  | 'latest_n3'
  | 'latest_n4'
  | 'latest_qe'
  | 'latest_risk_level'
  | 'latest_appropriation_type';
export type SortDirection = 'asc' | 'desc';

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export const RISK_COLORS: Record<RiskLevel, string> = {
  low: 'var(--color-success-600)',
  medium: 'var(--color-warning-500)',
  high: 'var(--color-warning-700)',
  critical: 'var(--color-error-600)',
};

export const RISK_LABELS: Record<RiskLevel, string> = {
  low: 'Bajo',
  medium: 'Medio',
  high: 'Alto',
  critical: 'Critico',
};

export const RISK_DESCRIPTIONS: Record<RiskLevel, string> = {
  low: 'Buen proceso cognitivo',
  medium: 'Necesita seguimiento',
  high: 'Requiere intervencion',
  critical: 'Alerta inmediata',
};

export interface RiskAssessment {
  id: string;
  student_id: string;
  commission_id: string;
  risk_level: RiskLevel;
  risk_factors: Record<string, { score: number; [key: string]: unknown }>;
  recommendation: string | null;
  triggered_by: string;
  assessed_at: string;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
}

export const RISK_FACTOR_LABELS: Record<string, string> = {
  dependency: 'Dependencia de IA',
  disengagement: 'Desvinculacion',
  stagnation: 'Estancamiento',
};

// Appropriation type display config
export const APPROPRIATION_LABELS: Record<AppropriationType, string> = {
  Delegacion: 'Delegacion',
  Superficial: 'Superficial',
  Reflexiva: 'Reflexiva',
  Autonomo: 'Autonomo',
};

// Badge classes per appropriation type (uses existing CSS var pattern)
export const APPROPRIATION_BADGE_CLASSES: Record<AppropriationType, string> = {
  Delegacion:
    'bg-[var(--color-error-50)] text-[var(--color-error-700)] dark:bg-[var(--color-error-900)]/20 dark:text-[var(--color-error-400)]',
  Superficial:
    'bg-[var(--color-warning-50)] text-[var(--color-warning-700)] dark:bg-[var(--color-warning-900)]/20 dark:text-[var(--color-warning-400)]',
  Reflexiva:
    'bg-[var(--color-success-50)] text-[var(--color-success-700)] dark:bg-[var(--color-success-900)]/20 dark:text-[var(--color-success-400)]',
  Autonomo:
    'bg-[var(--color-neutral-100)] text-[var(--color-neutral-600)] dark:bg-[var(--color-neutral-800)] dark:text-[var(--color-neutral-400)]',
};
