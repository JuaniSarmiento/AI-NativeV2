import { useNavigate } from 'react-router-dom';
import { useTeacherDashboardStore } from './store';
import { apiClient } from '@/shared/lib/api-client';
import type { RiskAssessment, RiskLevel } from './types';
import { RISK_LABELS, RISK_FACTOR_LABELS } from './types';

const EMPTY_RISKS: RiskAssessment[] = [];

const RISK_ROW_CLASSES: Record<RiskLevel, string> = {
  critical:
    'border-l-2 border-l-[var(--color-error-500)] bg-[var(--color-error-50)]/30 dark:bg-[var(--color-error-900)]/10',
  high: 'border-l-2 border-l-[var(--color-warning-600)] bg-[var(--color-warning-50)]/20 dark:bg-[var(--color-warning-900)]/10',
  medium: 'border-l-2 border-l-[var(--color-warning-400)]',
  low: 'border-l-2 border-l-[var(--color-success-500)]',
};

function formatFactors(factors: Record<string, { score: number; [key: string]: unknown }>): string {
  return Object.entries(factors)
    .map(([key, val]) => {
      const label = RISK_FACTOR_LABELS[key] ?? key.charAt(0).toUpperCase() + key.slice(1);
      return `${label}: ${val.score.toFixed(2)}`;
    })
    .join(', ');
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function RiskAlertsTable() {
  const risks = useTeacherDashboardStore((s) => s.risks);
  const isLoadingRisks = useTeacherDashboardStore((s) => s.isLoadingRisks);
  const acknowledgeRisk = useTeacherDashboardStore((s) => s.acknowledgeRisk);
  const navigate = useNavigate();

  const items = risks.length > 0 ? risks : EMPTY_RISKS;

  const sorted = [...items].sort((a, b) => {
    const order: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
    return (order[a.risk_level] ?? 4) - (order[b.risk_level] ?? 4);
  });

  if (isLoadingRisks) {
    return (
      <p className="text-[0.875rem] text-[var(--color-text-tertiary)]">
        Cargando alertas de riesgo...
      </p>
    );
  }

  if (sorted.length === 0) {
    return (
      <div className="rounded-[var(--radius-lg)] border border-dashed border-[var(--color-border)] p-8 text-center">
        <p className="text-[0.875rem] text-[var(--color-text-tertiary)]">
          Sin alertas de riesgo para esta comision.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)]">
      <table className="w-full text-left text-[0.8125rem]">
        <thead>
          <tr className="border-b border-[var(--color-border)]">
            <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">
              Alumno
            </th>
            <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">
              Nivel
            </th>
            <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">
              Factores
            </th>
            <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">
              Recomendacion
            </th>
            <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">
              Fecha
            </th>
            <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">
              Accion
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((risk) => {
            const isAcknowledged = risk.acknowledged_at !== null;
            const rowClass = isAcknowledged
              ? 'opacity-60'
              : RISK_ROW_CLASSES[risk.risk_level] ?? '';

            return (
              <tr
                key={risk.id}
                className={`border-b border-[var(--color-border)]/50 ${rowClass}`}
              >
                <td className="px-4 py-3">
                  <span className="font-mono text-[0.75rem] text-[var(--color-text-tertiary)]">
                    {risk.student_id.slice(0, 8)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-block rounded-full px-2.5 py-0.5 text-[0.6875rem] font-semibold uppercase tracking-[0.08em] ${riskLevelClasses(risk.risk_level)}`}
                  >
                    {RISK_LABELS[risk.risk_level] ?? risk.risk_level}
                  </span>
                </td>
                <td className="max-w-[200px] px-4 py-3 text-[0.75rem] text-[var(--color-text-secondary)]">
                  {formatFactors(risk.risk_factors)}
                </td>
                <td className="max-w-[250px] px-4 py-3 text-[0.75rem] text-[var(--color-text-secondary)]">
                  {risk.recommendation ?? '-'}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-[0.75rem] tabular-nums text-[var(--color-text-tertiary)]">
                  {formatDate(risk.assessed_at)}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={async () => {
                        try {
                          const res = await apiClient.get<{ id: string }[]>(
                            `/v1/cognitive/sessions?commission_id=${risk.commission_id}&student_id=${risk.student_id}&per_page=1`,
                          );
                          if (res.data.length > 0) {
                            navigate(`/teacher/trace/${res.data[0].id}`);
                          }
                        } catch { /* no sessions */ }
                      }}
                      className="text-[0.75rem] font-medium text-[var(--color-accent-600)] transition-colors hover:text-[var(--color-accent-700)]"
                    >
                      Ver traza
                    </button>
                    {isAcknowledged ? (
                      <span className="text-[0.75rem] text-[var(--color-text-tertiary)]">
                        Revisada
                      </span>
                    ) : (
                      <button
                        onClick={() => acknowledgeRisk(risk.id)}
                        className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-[0.75rem] font-medium text-[var(--color-text-primary)] transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] hover:bg-[var(--color-neutral-50)] active:scale-[0.98] dark:hover:bg-[var(--color-neutral-800)]"
                      >
                        Reconocer
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function riskLevelClasses(level: RiskLevel): string {
  switch (level) {
    case 'critical':
      return 'bg-[var(--color-error-50)] text-[var(--color-error-700)] dark:bg-[var(--color-error-900)]/20 dark:text-[var(--color-error-400)]';
    case 'high':
      return 'bg-[var(--color-warning-50)] text-[var(--color-warning-700)] dark:bg-[var(--color-warning-900)]/20 dark:text-[var(--color-warning-400)]';
    case 'medium':
      return 'bg-[var(--color-warning-50)] text-[var(--color-warning-600)] dark:bg-[var(--color-warning-900)]/10 dark:text-[var(--color-warning-300)]';
    default:
      return 'bg-[var(--color-success-50)] text-[var(--color-success-700)] dark:bg-[var(--color-success-900)]/20 dark:text-[var(--color-success-400)]';
  }
}
