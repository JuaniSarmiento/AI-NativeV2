import type { ScoreCondition } from '@/features/teacher/dashboard/types';

interface ScoreBreakdownProps {
  dimension: string;
  conditions: ScoreCondition[];
}

export default function ScoreBreakdown({ dimension, conditions }: ScoreBreakdownProps) {
  if (conditions.length === 0) {
    return (
      <p className="text-xs text-[var(--color-text-tertiary)]">
        Sin condiciones registradas para {dimension}.
      </p>
    );
  }

  const earned = conditions.filter((c) => c.met).reduce((s, c) => s + c.points, 0);
  const total = conditions.reduce((s, c) => s + c.points, 0);

  return (
    <div className="space-y-0.5">
      <div className="mb-2 flex items-baseline justify-between">
        <span className="text-[0.625rem] font-semibold uppercase tracking-wider text-[var(--color-text-tertiary)]">
          {dimension}
        </span>
        <span className="text-[0.625rem] tabular-nums text-[var(--color-text-tertiary)]">
          {earned}/{total} pts
        </span>
      </div>
      {conditions.map((cond, idx) => (
        <div
          key={idx}
          className="flex items-start gap-2 rounded-md px-2 py-1.5"
        >
          {/* Icon */}
          <span
            className={`mt-px flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[0.5rem] font-bold ${
              cond.met
                ? 'bg-[var(--color-success-100)] text-[var(--color-success-700)] dark:bg-[var(--color-success-900)]/30 dark:text-[var(--color-success-400)]'
                : 'bg-[var(--color-neutral-100)] text-[var(--color-text-tertiary)] dark:bg-[var(--color-neutral-800)]'
            }`}
            aria-hidden="true"
          >
            {cond.met ? '✓' : '✗'}
          </span>

          {/* Condition text */}
          <span
            className={`flex-1 text-[0.6875rem] leading-snug ${
              cond.met
                ? 'text-[var(--color-success-700)] dark:text-[var(--color-success-400)]'
                : 'text-[var(--color-text-tertiary)]'
            }`}
          >
            {cond.condition}
          </span>

          {/* Points */}
          <span
            className={`shrink-0 text-[0.625rem] tabular-nums font-medium ${
              cond.met
                ? 'text-[var(--color-success-600)] dark:text-[var(--color-success-400)]'
                : 'text-[var(--color-text-tertiary)] line-through'
            }`}
          >
            +{cond.points}
          </span>
        </div>
      ))}
    </div>
  );
}
