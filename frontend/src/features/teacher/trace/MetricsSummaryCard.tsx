import { useTraceStore } from './store';
import RiskBadge from '@/features/teacher/dashboard/RiskBadge';
import type { RiskLevel } from '@/features/teacher/dashboard/types';
import { RISK_DESCRIPTIONS } from '@/features/teacher/dashboard/types';

function scoreColor(val: number | null): string {
  if (val === null) return 'text-[var(--color-text-tertiary)]';
  if (val >= 70) return 'text-[var(--color-success-600)] dark:text-[var(--color-success-400)]';
  if (val >= 40) return 'text-[var(--color-warning-600)] dark:text-[var(--color-warning-400)]';
  return 'text-[var(--color-error-600)] dark:text-[var(--color-error-400)]';
}

function barColor(val: number | null): string {
  if (val === null || val === undefined) return 'bg-[var(--color-neutral-300)]';
  if (val >= 70) return 'bg-[var(--color-success-500)]';
  if (val >= 40) return 'bg-[var(--color-warning-500)]';
  return 'bg-[var(--color-error-500)]';
}

const DIMENSIONS = [
  { key: 'n1', field: 'n1_comprehension_score' as const, label: 'Comprension', desc: 'Entiende el problema?' },
  { key: 'n2', field: 'n2_strategy_score' as const, label: 'Estrategia', desc: 'Planifica antes de codear?' },
  { key: 'n3', field: 'n3_validation_score' as const, label: 'Validacion', desc: 'Verifica y corrige?' },
  { key: 'n4', field: 'n4_ai_interaction_score' as const, label: 'Uso de IA', desc: 'Usa IA criticamente?' },
];

export default function MetricsSummaryCard() {
  const metrics = useTraceStore((s) => s.metrics);

  if (!metrics) {
    return (
      <div className="rounded-xl border border-dashed border-[var(--color-border)] p-6 text-center">
        <p className="text-sm text-[var(--color-text-tertiary)]">
          Las metricas se calculan cuando la sesion se cierra.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Qe + Risk row */}
      <div className="flex flex-wrap items-center gap-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        <div>
          <p className="text-xs font-medium text-[var(--color-text-tertiary)]">Calidad Epistemica</p>
          <p className={`text-2xl font-bold tabular-nums ${scoreColor(metrics.qe_score)}`}>
            {metrics.qe_score != null ? metrics.qe_score.toFixed(0) : '-'}
          </p>
        </div>
        {metrics.risk_level && (
          <div className="flex items-center gap-2">
            <RiskBadge level={metrics.risk_level as RiskLevel} />
            <span className="text-xs text-[var(--color-text-secondary)]">
              {RISK_DESCRIPTIONS[metrics.risk_level as RiskLevel] ?? ''}
            </span>
          </div>
        )}
      </div>

      {/* N1-N4 grid */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {DIMENSIONS.map((dim) => {
          const val = metrics[dim.field] as number | null;
          return (
            <div key={dim.key} className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
              <div className="flex items-baseline justify-between">
                <span className="text-xs font-medium text-[var(--color-text-secondary)]">{dim.label}</span>
                <span className={`text-lg font-bold tabular-nums ${scoreColor(val)}`}>
                  {val != null ? val.toFixed(0) : '-'}
                </span>
              </div>
              <p className="mt-0.5 text-[0.625rem] text-[var(--color-text-tertiary)]">{dim.desc}</p>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[var(--color-neutral-100)] dark:bg-[var(--color-neutral-800)]">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${barColor(val)}`}
                  style={{ width: `${val ?? 0}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
