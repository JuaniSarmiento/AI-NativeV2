import { useEffect } from 'react';
import { useStudentProgressStore } from './store';
import EvolutionChart from './EvolutionChart';
import ScoreCard from './ScoreCard';
import type { ScoreCardData, ProgressSession } from './types';

const EMPTY_SESSIONS: ProgressSession[] = [];

const DIMENSION_LABELS: Record<string, string> = {
  n1: 'Comprension',
  n2: 'Estrategia',
  n3: 'Validacion',
  n4: 'Interaccion IA',
};

function getLastTwo(sessions: ProgressSession[]) {
  const sorted = [...sessions].sort((a, b) => {
    const da = a.computed_at ? new Date(a.computed_at).getTime() : 0;
    const db = b.computed_at ? new Date(b.computed_at).getTime() : 0;
    return db - da;
  });
  return { latest: sorted[0] ?? null, previous: sorted[1] ?? null };
}

export default function StudentProgress() {
  const progress = useStudentProgressStore((s) => s.progress);
  const isLoading = useStudentProgressStore((s) => s.isLoading);
  const error = useStudentProgressStore((s) => s.error);
  const fetchProgress = useStudentProgressStore((s) => s.fetchProgress);

  useEffect(() => {
    fetchProgress();
  }, [fetchProgress]);

  const sessions = progress?.sessions ?? EMPTY_SESSIONS;
  const { latest, previous } = getLastTwo(sessions);

  const cards: ScoreCardData[] = [
    {
      label: DIMENSION_LABELS.n1,
      score: progress?.avg_n1 ?? null,
      previousScore: previous?.n1_comprehension_score ?? null,
    },
    {
      label: DIMENSION_LABELS.n2,
      score: progress?.avg_n2 ?? null,
      previousScore: previous?.n2_strategy_score ?? null,
    },
    {
      label: DIMENSION_LABELS.n3,
      score: progress?.avg_n3 ?? null,
      previousScore: previous?.n3_validation_score ?? null,
    },
    {
      label: DIMENSION_LABELS.n4,
      score: progress?.avg_n4 ?? null,
      previousScore: previous?.n4_ai_interaction_score ?? null,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <span className="inline-block rounded-full bg-[var(--color-accent-50)] px-3 py-1 text-[0.6875rem] font-semibold uppercase tracking-[0.15em] text-[var(--color-accent-700)] dark:bg-[var(--color-accent-900)]/20 dark:text-[var(--color-accent-400)]">
          Mi Progreso
        </span>
        <h1 className="mt-3 text-[1.75rem] font-bold tracking-tight text-[var(--color-text-primary)]">
          Progreso Cognitivo
        </h1>
        <p className="mt-1 max-w-[55ch] text-[0.875rem] leading-relaxed text-[var(--color-text-secondary)]">
          Tu evolucion en las cuatro dimensiones del modelo N4. Cada dimension refleja un aspecto diferente de tu proceso de aprendizaje.
        </p>
      </div>

      {/* Loading / Error */}
      {isLoading && (
        <p className="text-[0.875rem] text-[var(--color-text-tertiary)]">
          Cargando progreso...
        </p>
      )}
      {error && (
        <p className="text-[0.875rem] text-[var(--color-error-600)]">{error}</p>
      )}

      {/* Empty state */}
      {!isLoading && !error && sessions.length === 0 && (
        <div className="rounded-[var(--radius-lg)] border border-dashed border-[var(--color-border)] p-12 text-center">
          <p className="text-[1.0625rem] font-medium text-[var(--color-text-secondary)]">
            Aun no tenes datos de progreso.
          </p>
          <p className="mt-2 text-[0.875rem] text-[var(--color-text-tertiary)]">
            Completa ejercicios para ver tu evolucion.
          </p>
        </div>
      )}

      {/* Content */}
      {!isLoading && sessions.length > 0 && (
        <>
          {/* Score cards */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {cards.map((card) => (
              <ScoreCard key={card.label} data={card} />
            ))}
          </div>

          {/* Evolution chart */}
          <EvolutionChart sessions={sessions} />

          {/* Session count */}
          <p className="text-[0.75rem] text-[var(--color-text-tertiary)]">
            Basado en {progress?.session_count ?? 0} sesiones cognitivas.
          </p>
        </>
      )}
    </div>
  );
}
