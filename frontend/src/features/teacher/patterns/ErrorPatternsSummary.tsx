import type { RiskLevel } from '@/features/teacher/dashboard/types';
import { RISK_LABELS } from '@/features/teacher/dashboard/types';

interface ErrorPatternsSummaryProps {
  avgCodeRuns: number;
  lowEfficiencyPct: number;
  riskDistribution: Record<string, number>;
}

export default function ErrorPatternsSummary({
  avgCodeRuns,
  lowEfficiencyPct,
  riskDistribution,
}: ErrorPatternsSummaryProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        <p className="text-[0.6875rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
          Ejecuciones promedio
        </p>
        <p className="mt-1 text-[1.5rem] font-bold tabular-nums tracking-tight text-[var(--color-text-primary)]">
          {avgCodeRuns.toFixed(1)}
        </p>
      </div>
      <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        <p className="text-[0.6875rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
          Baja eficiencia (&lt;50%)
        </p>
        <p className="mt-1 text-[1.5rem] font-bold tabular-nums tracking-tight text-[var(--color-text-primary)]">
          {lowEfficiencyPct.toFixed(0)}%
        </p>
      </div>
      <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        <p className="text-[0.6875rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
          Distribucion de riesgo
        </p>
        <div className="mt-1 flex flex-wrap gap-2">
          {(['low', 'medium', 'high', 'critical'] as RiskLevel[]).map((level) => {
            const count = riskDistribution[level] ?? 0;
            if (count === 0) return null;
            return (
              <span key={level} className="text-[0.75rem] text-[var(--color-text-secondary)]">
                {RISK_LABELS[level]}: {count}
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
}
