import { useEffect, useState } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { apiClient } from '@/shared/lib/api-client';
import RiskBadge from '@/features/teacher/dashboard/RiskBadge';
import type { RiskLevel } from '@/features/teacher/dashboard/types';

interface SessionSummary {
  id: string;
  exercise_id: string;
  exercise_title: string | null;
  status: string;
  started_at: string;
  closed_at: string | null;
}

interface TraceData {
  session: { id: string; status: string; started_at: string; closed_at: string | null };
  student_name: string | null;
  student_email: string | null;
  exercise_title: string | null;
  timeline: Array<{
    id: string;
    event_type: string;
    sequence_number: number;
    n4_level: number | null;
    payload: Record<string, unknown>;
    created_at: string;
  }>;
  code_evolution: Array<{
    snapshot_id: string | null;
    code: string;
    snapshot_at: string;
  }>;
  chat: Array<{
    id: string;
    role: string;
    content: string;
    created_at: string;
    n4_level: number | null;
  }>;
  metrics: {
    n1_comprehension_score: number | null;
    n2_strategy_score: number | null;
    n3_validation_score: number | null;
    n4_ai_interaction_score: number | null;
    qe_score: number | null;
    risk_level: string | null;
    [key: string]: unknown;
  } | null;
  verification: { valid: boolean; events_checked: number | null } | null;
}

function scoreColor(val: number | null): string {
  if (val === null) return 'text-[var(--color-text-tertiary)]';
  if (val >= 70) return 'text-[var(--color-success-600)] dark:text-[var(--color-success-400)]';
  if (val >= 40) return 'text-[var(--color-warning-600)] dark:text-[var(--color-warning-400)]';
  return 'text-[var(--color-error-600)] dark:text-[var(--color-error-400)]';
}

function barColor(val: number | null): string {
  if (val === null) return 'bg-[var(--color-neutral-300)]';
  if (val >= 70) return 'bg-[var(--color-success-500)]';
  if (val >= 40) return 'bg-[var(--color-warning-500)]';
  return 'bg-[var(--color-error-500)]';
}

const EVENT_TYPE_LABELS: Record<string, string> = {
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

const N4_COLORS: Record<number, string> = {
  1: 'bg-blue-500',
  2: 'bg-emerald-500',
  3: 'bg-amber-500',
  4: 'bg-purple-500',
};

const N4_LABELS: Record<number, string> = {
  1: 'Comprension',
  2: 'Estrategia',
  3: 'Validacion',
  4: 'Interaccion IA',
};

export default function StudentActivityPage() {
  const { studentId } = useParams<{ studentId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const commissionId = searchParams.get('commission') ?? '';

  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [studentName, setStudentName] = useState<string | null>(null);
  const [studentEmail, setStudentEmail] = useState<string | null>(null);

  const [expandedSession, setExpandedSession] = useState<string | null>(null);
  const [traceData, setTraceData] = useState<Record<string, TraceData>>({});
  const [loadingTrace, setLoadingTrace] = useState<string | null>(null);

  useEffect(() => {
    if (!studentId || !commissionId) return;
    setLoading(true);
    apiClient
      .get<{ data: SessionSummary[]; meta: unknown }>(
        `/v1/cognitive/sessions?commission_id=${commissionId}&student_id=${studentId}&per_page=50`,
      )
      .then((res) => {
        const payload = res.data as unknown as { data?: SessionSummary[] };
        const items = Array.isArray(payload.data) ? payload.data : Array.isArray(res.data) ? res.data as unknown as SessionSummary[] : [];
        setSessions(items);
        if (items.length > 0) {
          loadTrace(items[0].id);
          setExpandedSession(items[0].id);
        }
      })
      .catch(() => setSessions([]))
      .finally(() => setLoading(false));
  }, [studentId, commissionId]);

  const loadTrace = async (sessionId: string) => {
    if (traceData[sessionId]) return;
    setLoadingTrace(sessionId);
    try {
      const res = await apiClient.get<{ data: TraceData }>(`/v1/cognitive/sessions/${sessionId}/trace`);
      const payload = res.data as unknown as { data?: TraceData };
      const trace = payload.data ?? res.data as unknown as TraceData;
      setTraceData((prev) => ({ ...prev, [sessionId]: trace }));
      if (!studentName && trace.student_name) {
        setStudentName(trace.student_name);
        setStudentEmail(trace.student_email);
      }
    } catch {
      // silent
    } finally {
      setLoadingTrace(null);
    }
  };

  const toggleSession = (sessionId: string) => {
    if (expandedSession === sessionId) {
      setExpandedSession(null);
    } else {
      setExpandedSession(sessionId);
      loadTrace(sessionId);
    }
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-6">
        <div className="flex items-center gap-3">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--color-accent-500)] border-t-transparent" />
          <span className="text-sm text-[var(--color-text-secondary)]">Cargando actividad del alumno...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-6">
      {/* Header */}
      <div>
        <button
          onClick={() => navigate(-1)}
          className="text-xs font-medium text-[var(--color-accent-600)] transition-colors hover:text-[var(--color-accent-700)]"
        >
          ← Volver al dashboard
        </button>
        <h1 className="mt-3 text-2xl font-bold tracking-tight text-[var(--color-text-primary)]">
          {studentName ?? `Alumno ${studentId?.slice(0, 8)}`}
        </h1>
        {studentEmail && (
          <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{studentEmail}</p>
        )}
        <p className="mt-1 text-sm text-[var(--color-text-tertiary)]">
          {sessions.length} sesiones cognitivas registradas
        </p>
      </div>

      {/* Sessions */}
      {sessions.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[var(--color-border)] p-12 text-center">
          <p className="text-sm text-[var(--color-text-tertiary)]">
            Este alumno no tiene sesiones cognitivas en esta comision.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {sessions.map((session, idx) => {
            const trace = traceData[session.id];
            const isExpanded = expandedSession === session.id;
            const isLoading = loadingTrace === session.id;

            return (
              <div
                key={session.id}
                className="overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)]"
              >
                {/* Session header — clickable */}
                <button
                  onClick={() => toggleSession(session.id)}
                  className="flex w-full items-center justify-between px-5 py-4 text-left transition-colors hover:bg-[var(--color-neutral-50)] dark:hover:bg-[var(--color-neutral-800)]/20"
                >
                  <div className="flex items-center gap-3">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--color-accent-100)] text-sm font-bold text-[var(--color-accent-700)] dark:bg-[var(--color-accent-900)]/30 dark:text-[var(--color-accent-400)]">
                      {sessions.length - idx}
                    </span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-[var(--color-text-primary)]">
                          {session.exercise_title ?? trace?.exercise_title ?? `Actividad ${session.exercise_id.slice(0, 8)}`}
                        </span>
                        <span className={`rounded-full px-2 py-0.5 text-[0.5625rem] font-semibold ${
                          session.status === 'closed'
                            ? 'bg-[var(--color-success-50)] text-[var(--color-success-700)] dark:bg-[var(--color-success-900)]/20 dark:text-[var(--color-success-400)]'
                            : 'bg-[var(--color-info-50)] text-[var(--color-info-700)] dark:bg-[var(--color-info-900)]/20 dark:text-[var(--color-info-400)]'
                        }`}>
                          {session.status === 'closed' ? 'Cerrada' : 'En curso'}
                        </span>
                      </div>
                      <span className="text-xs text-[var(--color-text-tertiary)]">
                        {new Date(session.started_at).toLocaleString('es-AR')}
                        {session.closed_at && (
                          <> — {new Date(session.closed_at).toLocaleString('es-AR')}</>
                        )}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {trace?.metrics && (
                      <div className="flex items-center gap-2">
                        <span className={`text-lg font-bold tabular-nums ${scoreColor(trace.metrics.qe_score)}`}>
                          Qe {trace.metrics.qe_score != null ? trace.metrics.qe_score.toFixed(0) : '-'}
                        </span>
                        {trace.metrics.risk_level && (
                          <RiskBadge level={trace.metrics.risk_level as RiskLevel} />
                        )}
                      </div>
                    )}
                    <span className="text-lg text-[var(--color-text-tertiary)]">
                      {isExpanded ? '▾' : '▸'}
                    </span>
                  </div>
                </button>

                {/* Expanded trace */}
                {isExpanded && (
                  <div className="border-t border-[var(--color-border)] px-5 py-4">
                    {isLoading && !trace ? (
                      <div className="flex items-center gap-3 py-4">
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--color-accent-500)] border-t-transparent" />
                        <span className="text-xs text-[var(--color-text-secondary)]">Cargando traza...</span>
                      </div>
                    ) : trace ? (
                      <SessionDetail trace={trace} />
                    ) : (
                      <p className="py-4 text-xs text-[var(--color-text-tertiary)]">Error cargando la traza.</p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function SessionDetail({ trace }: { trace: TraceData }) {
  const metrics = trace.metrics;
  const timeline = trace.timeline ?? [];
  const chat = trace.chat ?? [];
  const code = trace.code_evolution ?? [];

  const dimensions = [
    { label: 'Comprension', value: metrics?.n1_comprehension_score ?? null, desc: 'Entiende el problema?' },
    { label: 'Estrategia', value: metrics?.n2_strategy_score ?? null, desc: 'Planifica la solucion?' },
    { label: 'Validacion', value: metrics?.n3_validation_score ?? null, desc: 'Verifica y corrige?' },
    { label: 'Uso de IA', value: metrics?.n4_ai_interaction_score ?? null, desc: 'Usa IA criticamente?' },
  ];

  return (
    <div className="space-y-4">
      {/* Metrics */}
      {metrics && (
        <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
          {dimensions.map((dim) => (
            <div key={dim.label} className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] p-2.5">
              <div className="flex items-baseline justify-between">
                <span className="text-[0.625rem] font-medium text-[var(--color-text-tertiary)]">{dim.label}</span>
                <span className={`text-base font-bold tabular-nums ${scoreColor(dim.value)}`}>
                  {dim.value != null ? dim.value.toFixed(0) : '-'}
                </span>
              </div>
              <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-[var(--color-neutral-100)] dark:bg-[var(--color-neutral-800)]">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${barColor(dim.value)}`}
                  style={{ width: `${dim.value ?? 0}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Integrity */}
      {trace.verification && (
        <div className="flex items-center gap-2 text-xs">
          {trace.verification.valid ? (
            <>
              <span className="text-[var(--color-success-600)]">✓</span>
              <span className="text-[var(--color-text-secondary)]">
                Cadena integra ({trace.verification.events_checked} eventos verificados)
              </span>
            </>
          ) : (
            <>
              <span className="text-[var(--color-error-600)]">✗</span>
              <span className="text-[var(--color-text-secondary)]">Cadena comprometida</span>
            </>
          )}
        </div>
      )}

      {/* 3-column content */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Timeline */}
        <div>
          <h4 className="mb-2 text-xs font-semibold text-[var(--color-text-secondary)]">
            Timeline ({timeline.length} eventos)
          </h4>
          {timeline.length === 0 ? (
            <p className="text-xs text-[var(--color-text-tertiary)]">Sin eventos.</p>
          ) : (
            <div className="max-h-[400px] space-y-1.5 overflow-y-auto">
              {timeline.map((evt) => (
                <div key={evt.id} className="flex items-start gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] p-2">
                  {evt.n4_level && (
                    <span className={`mt-0.5 h-2 w-2 shrink-0 rounded-full ${N4_COLORS[evt.n4_level] ?? 'bg-gray-400'}`} title={N4_LABELS[evt.n4_level] ?? ''} />
                  )}
                  <div className="min-w-0 flex-1">
                    <span className="text-xs font-medium text-[var(--color-text-primary)]">
                      {EVENT_TYPE_LABELS[evt.event_type] ?? evt.event_type}
                    </span>

                    {(() => {
                      const rawStatus = evt.payload.status;
                      const status = typeof rawStatus === 'string' ? rawStatus : null;
                      if (evt.event_type !== 'code.run' || !status) return null;
                      return (
                      <span className={`ml-1.5 text-[0.625rem] ${
                        status === 'ok' || status === 'success'
                          ? 'text-[var(--color-success-600)]'
                          : 'text-[var(--color-error-600)]'
                      }`}>
                        {status}
                      </span>
                      );
                    })()}
                    <p className="text-[0.625rem] text-[var(--color-text-tertiary)]">
                      {new Date(evt.created_at).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      {' — seq #{' + evt.sequence_number + '}'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Code */}
        <div>
          <h4 className="mb-2 text-xs font-semibold text-[var(--color-text-secondary)]">
            Codigo ({code.length} snapshots)
          </h4>
          {code.length === 0 ? (
            <p className="text-xs text-[var(--color-text-tertiary)]">Sin snapshots de codigo.</p>
          ) : (
            <div className="max-h-[400px] space-y-2 overflow-y-auto">
              {code.map((snap, i) => (
                <div key={snap.snapshot_id ?? i} className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] p-2">
                  <p className="mb-1 text-[0.625rem] text-[var(--color-text-tertiary)]">
                    {new Date(snap.snapshot_at).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })}
                  </p>
                  <pre className="max-h-[200px] overflow-auto whitespace-pre-wrap rounded bg-[var(--color-neutral-100)] p-2 font-mono text-[0.625rem] leading-relaxed text-[var(--color-text-primary)] dark:bg-[var(--color-neutral-800)]">
                    {snap.code}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Chat */}
        <div>
          <h4 className="mb-2 text-xs font-semibold text-[var(--color-text-secondary)]">
            Chat con tutor ({chat.length} mensajes)
          </h4>
          {chat.length === 0 ? (
            <p className="text-xs text-[var(--color-text-tertiary)]">Sin mensajes del tutor.</p>
          ) : (
            <div className="max-h-[400px] space-y-1.5 overflow-y-auto">
              {chat.map((msg) => (
                <div
                  key={msg.id}
                  className={`rounded-lg p-2 text-xs ${
                    msg.role === 'user'
                      ? 'ml-4 bg-[var(--color-accent-50)] text-[var(--color-text-primary)] dark:bg-[var(--color-accent-900)]/20'
                      : 'mr-4 border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text-primary)]'
                  }`}
                >
                  <p className="mb-0.5 text-[0.5625rem] font-medium text-[var(--color-text-tertiary)]">
                    {msg.role === 'user' ? 'Alumno' : 'Tutor'}
                    {' — '}
                    {new Date(msg.created_at).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })}
                  </p>
                  <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
