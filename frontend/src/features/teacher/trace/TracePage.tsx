import { useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useTraceStore } from './store';
import EventTimeline from './EventTimeline';
import CodeEvolutionPanel from './CodeEvolutionPanel';
import ChatPanel from './ChatPanel';
import MetricsSummaryCard from './MetricsSummaryCard';
import IntegrityIndicator from './IntegrityIndicator';

export default function TracePage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const session = useTraceStore((s) => s.session);
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
      <div className="space-y-4">
        <p className="text-[0.875rem] text-[var(--color-text-tertiary)]">
          Cargando traza cognitiva...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <p className="text-[0.875rem] text-[var(--color-error-600)]">{error}</p>
      </div>
    );
  }

  if (!session) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          to={-1 as unknown as string}
          className="text-[0.75rem] font-medium text-[var(--color-accent-600)] hover:text-[var(--color-accent-700)]"
          onClick={(e) => {
            e.preventDefault();
            window.history.back();
          }}
        >
          Volver
        </Link>
        <span className="mt-2 inline-block rounded-full bg-[var(--color-accent-50)] px-3 py-1 text-[0.6875rem] font-semibold uppercase tracking-[0.15em] text-[var(--color-accent-700)] dark:bg-[var(--color-accent-900)]/20 dark:text-[var(--color-accent-400)]">
          Traza Cognitiva
        </span>
        <h1 className="mt-2 text-[1.75rem] font-bold tracking-tight text-[var(--color-text-primary)]">
          Sesion {session.id.slice(0, 8)}
        </h1>
        <div className="mt-1 flex flex-wrap items-center gap-4 text-[0.8125rem] text-[var(--color-text-secondary)]">
          <span>Alumno: <span className="font-mono">{session.student_id.slice(0, 8)}</span></span>
          <span>Ejercicio: <span className="font-mono">{session.exercise_id.slice(0, 8)}</span></span>
          <span className={`rounded-full px-2.5 py-0.5 text-[0.6875rem] font-semibold uppercase ${
            session.status === 'closed'
              ? 'bg-[var(--color-success-50)] text-[var(--color-success-700)] dark:bg-[var(--color-success-900)]/20 dark:text-[var(--color-success-400)]'
              : session.status === 'open'
                ? 'bg-[var(--color-info-50)] text-[var(--color-info-700)] dark:bg-[var(--color-info-900)]/20 dark:text-[var(--color-info-400)]'
                : 'bg-[var(--color-error-50)] text-[var(--color-error-700)] dark:bg-[var(--color-error-900)]/20 dark:text-[var(--color-error-400)]'
          }`}>
            {session.status}
          </span>
        </div>
      </div>

      {/* Metrics + Integrity */}
      <div className="flex flex-wrap items-start gap-4">
        <div className="flex-1">
          <MetricsSummaryCard />
        </div>
        <div className="flex items-center pt-3">
          <IntegrityIndicator />
        </div>
      </div>

      {/* 3-column layout: Timeline | Code | Chat */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div>
          <h2 className="mb-3 text-[0.8125rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-secondary)]">
            Timeline
          </h2>
          <div className="max-h-[600px] overflow-y-auto">
            <EventTimeline />
          </div>
        </div>
        <div>
          <h2 className="mb-3 text-[0.8125rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-secondary)]">
            Codigo
          </h2>
          <div className="max-h-[600px] overflow-y-auto">
            <CodeEvolutionPanel />
          </div>
        </div>
        <div>
          <h2 className="mb-3 text-[0.8125rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-secondary)]">
            Chat con el Tutor
          </h2>
          <div className="max-h-[600px] overflow-y-auto">
            <ChatPanel />
          </div>
        </div>
      </div>
    </div>
  );
}
