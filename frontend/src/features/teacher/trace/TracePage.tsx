import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTraceStore } from './store';
import EventTimeline from './EventTimeline';
import CodeEvolutionPanel from './CodeEvolutionPanel';
import ChatPanel from './ChatPanel';
import MetricsSummaryCard from './MetricsSummaryCard';
import IntegrityIndicator from './IntegrityIndicator';

export default function TracePage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const session = useTraceStore((s) => s.session);
  const studentName = useTraceStore((s) => s.studentName);
  const studentEmail = useTraceStore((s) => s.studentEmail);
  const exerciseTitle = useTraceStore((s) => s.exerciseTitle);
  const isLoading = useTraceStore((s) => s.isLoading);
  const error = useTraceStore((s) => s.error);
  const fetchTrace = useTraceStore((s) => s.fetchTrace);
  const clear = useTraceStore((s) => s.clear);

  useEffect(() => {
    if (sessionId) {
      fetchTrace(sessionId);
    }
    return () => {
      clear();
    };
  }, [sessionId, fetchTrace, clear]);

  if (isLoading) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-6">
        <div className="flex items-center gap-3">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--color-accent-500)] border-t-transparent" />
          <span className="text-sm text-[var(--color-text-secondary)]">Cargando traza cognitiva...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-6">
        <div className="rounded-xl border border-[var(--color-error-200)] bg-[var(--color-error-50)] p-4 dark:border-[var(--color-error-800)] dark:bg-[var(--color-error-900)]/20">
          <p className="text-sm text-[var(--color-error-700)] dark:text-[var(--color-error-400)]">{error}</p>
        </div>
      </div>
    );
  }

  if (!session) {
    return null;
  }

  const statusLabel = session.status === 'closed' ? 'Cerrada' : session.status === 'open' ? 'En curso' : 'Invalidada';
  const statusClass = session.status === 'closed'
    ? 'bg-[var(--color-success-50)] text-[var(--color-success-700)] dark:bg-[var(--color-success-900)]/20 dark:text-[var(--color-success-400)]'
    : session.status === 'open'
      ? 'bg-[var(--color-info-50)] text-[var(--color-info-700)] dark:bg-[var(--color-info-900)]/20 dark:text-[var(--color-info-400)]'
      : 'bg-[var(--color-error-50)] text-[var(--color-error-700)] dark:bg-[var(--color-error-900)]/20 dark:text-[var(--color-error-400)]';

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
          Traza Cognitiva
        </h1>

        <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-[var(--color-text-secondary)]">Alumno:</span>
            <span className="font-medium text-[var(--color-text-primary)]">
              {studentName ?? session.student_id.slice(0, 12)}
            </span>
            {studentEmail && (
              <span className="text-xs text-[var(--color-text-tertiary)]">({studentEmail})</span>
            )}
          </div>
          <span className="text-[var(--color-text-tertiary)]">|</span>
          <div className="flex items-center gap-2">
            <span className="text-[var(--color-text-secondary)]">Actividad:</span>
            <span className="font-medium text-[var(--color-text-primary)]">
              {exerciseTitle ?? session.exercise_id.slice(0, 12)}
            </span>
          </div>
          <span className={`rounded-full px-2.5 py-0.5 text-[0.6875rem] font-semibold ${statusClass}`}>
            {statusLabel}
          </span>
        </div>

        {session.started_at && (
          <p className="mt-1 text-xs text-[var(--color-text-tertiary)]">
            Inicio: {new Date(session.started_at).toLocaleString('es-AR')}
            {session.closed_at && (
              <> — Fin: {new Date(session.closed_at).toLocaleString('es-AR')}</>
            )}
          </p>
        )}
      </div>

      {/* Metrics */}
      <MetricsSummaryCard />

      {/* Integrity */}
      <IntegrityIndicator />

      {/* 3-column layout: Timeline | Code | Chat */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div>
          <h2 className="mb-3 text-sm font-semibold text-[var(--color-text-primary)]">
            Timeline de eventos
          </h2>
          <p className="mb-3 text-xs text-[var(--color-text-tertiary)]">
            Secuencia cronologica del proceso cognitivo.
          </p>
          <div className="max-h-[600px] overflow-y-auto">
            <EventTimeline />
          </div>
        </div>
        <div>
          <h2 className="mb-3 text-sm font-semibold text-[var(--color-text-primary)]">
            Evolucion del codigo
          </h2>
          <p className="mb-3 text-xs text-[var(--color-text-tertiary)]">
            Como fue cambiando el codigo a lo largo de la sesion.
          </p>
          <div className="max-h-[600px] overflow-y-auto">
            <CodeEvolutionPanel />
          </div>
        </div>
        <div>
          <h2 className="mb-3 text-sm font-semibold text-[var(--color-text-primary)]">
            Chat con el Tutor
          </h2>
          <p className="mb-3 text-xs text-[var(--color-text-tertiary)]">
            Conversacion del alumno con el tutor IA.
          </p>
          <div className="max-h-[600px] overflow-y-auto">
            <ChatPanel />
          </div>
        </div>
      </div>
    </div>
  );
}
