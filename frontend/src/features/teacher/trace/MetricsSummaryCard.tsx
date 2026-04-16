import { useTraceStore } from './store';
import type { RiskLevel } from '@/features/teacher/dashboard/types';
import { RISK_LABELS } from '@/features/teacher/dashboard/types';

function riskBadgeClasses(level: string): string {
  const base = 'inline-block rounded-full px-2.5 py-0.5 text-[0.6875rem] font-semibold uppercase tracking-[0.08em]';
  switch (level) {
    case 'critical':
      return `${base} bg-[var(--color-error-50)] text-[var(--color-error-700)] dark:bg-[var(--color-error-900)]/20 dark:text-[var(--color-error-400)]`;
    case 'high':
      return `${base} bg-[var(--color-warning-50)] text-[var(--color-warning-700)] dark:bg-[var(--color-warning-900)]/20 dark:text-[var(--color-warning-400)]`;
    case 'medium':
      return `${base} bg-[var(--color-warning-50)] text-[var(--color-warning-600)] dark:bg-[var(--color-warning-900)]/10 dark:text-[var(--color-warning-300)]`;
    default:
      return `${base} bg-[var(--color-success-50)] text-[var(--color-success-700)] dark:bg-[var(--color-success-900)]/20 dark:text-[var(--color-success-400)]`;
  }
}

function ScoreItem({ label, value }: { label: string; value: number | null }) {
  return (
    <div>
      <p className="text-[0.6875rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
        {label}
      </p>
      <p className="mt-0.5 text-[1.25rem] font-bold tabular-nums tracking-tight text-[var(--color-text-primary)]">
        {value !== null ? value.toFixed(1) : '-'}
      </p>
    </div>
  );
}

export default function MetricsSummaryCard() {
  const metrics = useTraceStore((s) => s.metrics);

  if (!metrics) {
    return (
      <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        <p className="text-[0.875rem] text-[var(--color-text-tertiary)]">
          Metricas pendientes
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <div className="flex flex-wrap items-center gap-6">
        <ScoreItem label="N1" value={metrics.n1_comprehension_score} />
        <ScoreItem label="N2" value={metrics.n2_strategy_score} />
        <ScoreItem label="N3" value={metrics.n3_validation_score} />
        <ScoreItem label="N4" value={metrics.n4_ai_interaction_score} />
        <ScoreItem label="Qe" value={metrics.qe_score} />
        <ScoreItem label="Dep." value={metrics.dependency_score} />
        {metrics.risk_level && (
          <div>
            <p className="text-[0.6875rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
              Riesgo
            </p>
            <span className={`mt-1 ${riskBadgeClasses(metrics.risk_level)}`}>
              {RISK_LABELS[metrics.risk_level as RiskLevel] ?? metrics.risk_level}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
