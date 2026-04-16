import type { RiskLevel } from './types';
import { RISK_LABELS } from './types';

interface RiskDistributionCardProps {
  distribution: Record<string, number>;
}

const RISK_ORDER: RiskLevel[] = ['low', 'medium', 'high', 'critical'];

const RISK_DOT_CLASSES: Record<RiskLevel, string> = {
  low: 'bg-[var(--color-success-500)]',
  medium: 'bg-[var(--color-warning-400)]',
  high: 'bg-[var(--color-warning-600)]',
  critical: 'bg-[var(--color-error-500)]',
};

export default function RiskDistributionCard({ distribution }: RiskDistributionCardProps) {
  const total = Object.values(distribution).reduce((sum, n) => sum + n, 0);

  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
      <h3 className="mb-4 text-[0.8125rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-secondary)]">
        Distribucion de riesgo
      </h3>
      <div className="space-y-3">
        {RISK_ORDER.map((level) => {
          const count = distribution[level] ?? 0;
          const pct = total > 0 ? (count / total) * 100 : 0;
          return (
            <div key={level} className="flex items-center gap-3">
              <span
                className={`h-2.5 w-2.5 shrink-0 rounded-full ${RISK_DOT_CLASSES[level]}`}
              />
              <span className="w-16 text-[0.8125rem] font-medium text-[var(--color-text-primary)]">
                {RISK_LABELS[level]}
              </span>
              <div className="flex-1">
                <div className="h-2 overflow-hidden rounded-full bg-[var(--color-neutral-100)] dark:bg-[var(--color-neutral-800)]">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ease-[cubic-bezier(0.32,0.72,0,1)] ${RISK_DOT_CLASSES[level]}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
              <span className="w-8 text-right font-mono text-[0.75rem] tabular-nums text-[var(--color-text-tertiary)]">
                {count}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
