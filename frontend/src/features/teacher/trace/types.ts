export interface TraceEvent {
  id: string;
  event_type: string;
  sequence_number: number;
  n4_level: number | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface TraceSession {
  id: string;
  student_id: string;
  exercise_id: string;
  commission_id: string;
  started_at: string;
  closed_at: string | null;
  genesis_hash: string | null;
  session_hash: string | null;
  status: string;
  events: TraceEvent[];
}

export interface TraceMetrics {
  id: string;
  session_id: string;
  n1_comprehension_score: number | null;
  n2_strategy_score: number | null;
  n3_validation_score: number | null;
  n4_ai_interaction_score: number | null;
  qe_score: number | null;
  dependency_score: number | null;
  risk_level: string | null;
  [key: string]: unknown;
}

export interface VerifyResult {
  valid: boolean;
  events_checked: number | null;
  failed_at_sequence: number | null;
}

export interface CodeSnapshot {
  snapshot_id: string | null;
  code: string;
  snapshot_at: string;
}

export interface ChatMessage {
  id: string;
  role: string;
  content: string;
  created_at: string;
  n4_level: number | null;
}

export interface TraceAnomaly {
  code: string;
  message: string;
  severity?: 'low' | 'medium' | 'high';
}

export interface TraceData {
  session: TraceSession;
  student_name: string | null;
  student_email: string | null;
  exercise_title: string | null;
  timeline: TraceEvent[];
  code_evolution: CodeSnapshot[];
  chat: ChatMessage[];
  metrics: TraceMetrics | null;
  verification: VerifyResult | null;
  anomalies?: TraceAnomaly[] | null;
}

export const N4_LEVEL_COLORS: Record<number, string> = {
  1: 'var(--color-info-500)',
  2: 'var(--color-success-500)',
  3: 'var(--color-warning-500)',
  4: 'var(--color-accent-500)',
};

export const N4_LEVEL_LABELS: Record<number, string> = {
  1: 'Comprension',
  2: 'Estrategia',
  3: 'Validacion',
  4: 'Interaccion IA',
};

export const EVENT_TYPE_LABELS: Record<string, string> = {
  reads_problem: 'Lectura del problema',
  'code.snapshot': 'Snapshot de codigo',
  'code.run': 'Ejecucion de codigo',
  'submission.created': 'Entrega creada',
  'tutor.question_asked': 'Pregunta al tutor',
  'tutor.response_received': 'Respuesta del tutor',
  'session.started': 'Sesion iniciada',
  'session.closed': 'Sesion cerrada',
  'reflection.submitted': 'Reflexion enviada',
};
