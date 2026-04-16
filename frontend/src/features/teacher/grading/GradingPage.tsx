import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useGradingStore } from './store';
import type { ActivitySubmission, ActivityEvaluation } from './types';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('es-AR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function StatusBadge({ status, score }: { status: string; score: number | null }) {
  const isEvaluated = status === 'evaluated';
  return (
    <div className="flex items-center gap-2">
      <span className={`inline-block rounded-full px-2.5 py-0.5 text-[0.6875rem] font-semibold uppercase tracking-[0.08em] ${
        isEvaluated
          ? 'bg-[var(--color-success-50)] text-[var(--color-success-700)] dark:bg-[var(--color-success-900)]/20'
          : 'bg-[var(--color-warning-50)] text-[var(--color-warning-700)] dark:bg-[var(--color-warning-900)]/20'
      }`}>
        {isEvaluated ? 'Evaluado' : 'Pendiente'}
      </span>
      {score !== null && (
        <span className="text-[1.125rem] font-bold tabular-nums text-[var(--color-text-primary)]">
          {score}/100
        </span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Evaluation panel (AI result review)
// ---------------------------------------------------------------------------

function EvaluationPanel({
  evaluation,
  onConfirm,
  onCancel,
}: {
  evaluation: ActivityEvaluation;
  onConfirm: (score: number, feedback: string, exercises: { submission_id: string; score: number; feedback: string }[]) => void;
  onCancel: () => void;
}) {
  const [generalScore, setGeneralScore] = useState(evaluation.general_score);
  const [generalFeedback, setGeneralFeedback] = useState(evaluation.general_feedback);
  const [exScores, setExScores] = useState(
    evaluation.exercises.map((e) => ({ submission_id: e.submission_id, score: e.score, feedback: e.feedback })),
  );

  return (
    <div className="rounded-[var(--radius-lg)] border-2 border-[var(--color-accent-300)] bg-[var(--color-accent-50)]/20 p-6 dark:border-[var(--color-accent-700)] dark:bg-[var(--color-accent-900)]/10">
      <h3 className="text-[0.9375rem] font-bold text-[var(--color-accent-700)] dark:text-[var(--color-accent-400)]">
        Evaluacion IA — Revision del docente
      </h3>

      <div className="mt-4 flex items-start gap-4">
        <div>
          <label className="text-[0.6875rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">Nota General</label>
          <input type="number" min={0} max={100} value={generalScore}
            onChange={(e) => setGeneralScore(Number(e.target.value))}
            className="mt-1 block w-24 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[1.5rem] font-bold tabular-nums text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent-500)]"
          />
        </div>
        <div className="flex-1">
          <label className="text-[0.6875rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">Feedback General</label>
          <textarea rows={2} value={generalFeedback} onChange={(e) => setGeneralFeedback(e.target.value)}
            className="mt-1 w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[0.875rem] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent-500)]"
          />
        </div>
      </div>

      <div className="mt-4 space-y-3">
        {evaluation.exercises.map((ex, i) => (
          <div key={ex.submission_id} className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
            <div className="flex items-center justify-between">
              <span className="text-[0.875rem] font-semibold text-[var(--color-text-primary)]">
                {ex.exercise_title || `Ejercicio ${i + 1}`}
              </span>
              <input type="number" min={0} max={100} value={exScores[i]?.score ?? ex.score}
                onChange={(e) => { const u = [...exScores]; u[i] = { ...u[i], score: Number(e.target.value) }; setExScores(u); }}
                className="w-20 rounded-[var(--radius-sm)] border border-[var(--color-border)] px-2 py-1 text-center text-[0.875rem] font-bold tabular-nums outline-none focus:border-[var(--color-accent-500)]"
              />
            </div>
            <p className="mt-1 text-[0.8125rem] text-[var(--color-text-secondary)]">{ex.feedback}</p>
            {ex.strengths.length > 0 && (
              <p className="mt-1 text-[0.75rem] text-[var(--color-success-600)]">Fortalezas: {ex.strengths.join(', ')}</p>
            )}
            {ex.improvements.length > 0 && (
              <p className="mt-1 text-[0.75rem] text-[var(--color-warning-600)]">Mejoras: {ex.improvements.join(', ')}</p>
            )}
          </div>
        ))}
      </div>

      <div className="mt-4 flex gap-3">
        <button onClick={() => onConfirm(generalScore, generalFeedback, exScores)}
          className="rounded-[var(--radius-md)] bg-[var(--color-accent-600)] px-5 py-2.5 text-[0.8125rem] font-semibold text-white transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-[var(--color-accent-700)] active:scale-[0.98]">
          Confirmar Notas
        </button>
        <button onClick={onCancel}
          className="rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 py-2.5 text-[0.8125rem] font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-neutral-50)] dark:hover:bg-[var(--color-neutral-800)]">
          Cancelar
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Detail view — exercises inside a submission
// ---------------------------------------------------------------------------

function SubmissionDetail({
  submission,
  onBack,
}: {
  submission: ActivitySubmission;
  onBack: () => void;
}) {
  const currentEvaluation = useGradingStore((s) => s.currentEvaluation);
  const isEvaluating = useGradingStore((s) => s.isEvaluating);
  const evaluateActivity = useGradingStore((s) => s.evaluateActivity);
  const confirmGrade = useGradingStore((s) => s.confirmGrade);
  const clearEvaluation = useGradingStore((s) => s.clearEvaluation);

  return (
    <div className="space-y-6">
      <button onClick={onBack}
        className="text-[0.75rem] font-medium text-[var(--color-accent-600)] hover:text-[var(--color-accent-700)]">
        Volver a la lista
      </button>

      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-[1.25rem] font-bold text-[var(--color-text-primary)]">
            {submission.student_name || `Alumno ${submission.student_id.slice(0, 8)}`}
          </h2>
          <p className="mt-0.5 text-[0.8125rem] text-[var(--color-text-tertiary)]">
            Intento #{submission.attempt_number} — {formatDate(submission.submitted_at)}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={submission.status} score={submission.total_score} />
          {submission.status === 'pending' && (
            <button onClick={() => evaluateActivity(submission.id)} disabled={isEvaluating}
              className="rounded-[var(--radius-md)] bg-[var(--color-accent-600)] px-5 py-2 text-[0.8125rem] font-semibold text-white transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-[var(--color-accent-700)] active:scale-[0.98] disabled:opacity-50">
              {isEvaluating ? 'Evaluando con IA...' : 'Corregir con IA'}
            </button>
          )}
        </div>
      </div>

      {currentEvaluation && currentEvaluation.activity_submission_id === submission.id && (
        <EvaluationPanel
          evaluation={currentEvaluation}
          onConfirm={(score, feedback, exercises) => {
            confirmGrade(currentEvaluation.activity_submission_id, score, feedback, exercises);
            onBack();
          }}
          onCancel={clearEvaluation}
        />
      )}

      <div className="space-y-3">
        {submission.submissions.map((sub, i) => (
          <div key={sub.id} className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
            <div className="flex items-center justify-between">
              <span className="text-[0.875rem] font-medium text-[var(--color-text-primary)]">
                Ejercicio {i + 1}
              </span>
              {sub.score !== null && (
                <span className="text-[0.875rem] font-bold tabular-nums text-[var(--color-text-primary)]">
                  {sub.score}/100
                </span>
              )}
            </div>
            <pre className="mt-2 max-h-[150px] overflow-auto rounded-[var(--radius-md)] bg-[var(--color-neutral-50)] p-3 font-mono text-[0.75rem] leading-relaxed text-[var(--color-text-secondary)] dark:bg-[var(--color-neutral-900)]">
              {sub.code}
            </pre>
            {sub.feedback && (
              <div className="mt-2 rounded-[var(--radius-md)] border border-[var(--color-success-200)] bg-[var(--color-success-50)]/30 px-3 py-2 text-[0.8125rem] text-[var(--color-text-secondary)] dark:border-[var(--color-success-800)] dark:bg-[var(--color-success-900)]/10">
                {sub.feedback}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page — list of activity submissions as cards
// ---------------------------------------------------------------------------

export default function GradingPage() {
  const { activityId } = useParams<{ activityId: string }>();
  const submissions = useGradingStore((s) => s.submissions);
  const isLoading = useGradingStore((s) => s.isLoading);
  const error = useGradingStore((s) => s.error);
  const fetchSubmissions = useGradingStore((s) => s.fetchSubmissions);

  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (activityId) fetchSubmissions(activityId);
  }, [activityId, fetchSubmissions]);

  const selectedSubmission = submissions.find((s) => s.id === selectedId) ?? null;

  // Detail view
  if (selectedSubmission) {
    return (
      <div>
        <div className="mb-4">
          <span className="inline-block rounded-full bg-[var(--color-accent-50)] px-3 py-1 text-[0.6875rem] font-semibold uppercase tracking-[0.15em] text-[var(--color-accent-700)] dark:bg-[var(--color-accent-900)]/20 dark:text-[var(--color-accent-400)]">
            Correccion
          </span>
        </div>
        <SubmissionDetail submission={selectedSubmission} onBack={() => setSelectedId(null)} />
      </div>
    );
  }

  // List view
  return (
    <div className="space-y-6">
      <div>
        <button onClick={() => window.history.back()}
          className="text-[0.75rem] font-medium text-[var(--color-accent-600)] hover:text-[var(--color-accent-700)]">
          Volver
        </button>
        <span className="mt-2 inline-block rounded-full bg-[var(--color-accent-50)] px-3 py-1 text-[0.6875rem] font-semibold uppercase tracking-[0.15em] text-[var(--color-accent-700)] dark:bg-[var(--color-accent-900)]/20 dark:text-[var(--color-accent-400)]">
          Correccion
        </span>
        <h1 className="mt-2 text-[1.75rem] font-bold tracking-tight text-[var(--color-text-primary)]">
          Entregas de la Actividad
        </h1>
        <p className="mt-1 text-[0.875rem] text-[var(--color-text-secondary)]">
          Selecciona una entrega para ver los ejercicios y corregir con IA.
        </p>
      </div>

      {isLoading && <p className="text-[0.875rem] text-[var(--color-text-tertiary)]">Cargando entregas...</p>}
      {error && <p className="text-[0.875rem] text-[var(--color-error-600)]">{error}</p>}

      {submissions.length === 0 && !isLoading ? (
        <div className="rounded-[var(--radius-lg)] border border-dashed border-[var(--color-border)] p-12 text-center">
          <p className="text-[0.9375rem] text-[var(--color-text-tertiary)]">No hay entregas para esta actividad.</p>
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {submissions.map((as, i) => (
            <button
              key={as.id}
              onClick={() => setSelectedId(as.id)}
              className="w-full text-left rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] hover:border-[var(--color-accent-300)] hover:shadow-sm active:scale-[0.99] animate-[slideIn_400ms_cubic-bezier(0.32,0.72,0,1)_both]"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[1rem] font-semibold text-[var(--color-text-primary)]">
                    {as.student_name || `Alumno ${as.student_id.slice(0, 8)}`}
                  </p>
                  <p className="mt-1 text-[0.75rem] text-[var(--color-text-tertiary)]">
                    Intento #{as.attempt_number} — {formatDate(as.submitted_at)}
                  </p>
                  <p className="mt-1 text-[0.75rem] text-[var(--color-text-tertiary)]">
                    {as.submissions.length} ejercicio{as.submissions.length !== 1 ? 's' : ''}
                  </p>
                </div>
                <StatusBadge status={as.status} score={as.total_score} />
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
