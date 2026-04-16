import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { usePatternsStore } from './store';
import { apiClient } from '@/shared/lib/api-client';
import StrategyDistribution from './StrategyDistribution';
import ErrorPatternsSummary from './ErrorPatternsSummary';
import type { PatternSession } from './types';
import { RISK_LABELS, type RiskLevel } from '@/features/teacher/dashboard/types';

interface CommissionOption { id: string; name: string; year: number; semester: number; }

const EMPTY_SESSIONS: PatternSession[] = [];
const EMPTY_COMMISSIONS: CommissionOption[] = [];

export default function ExercisePatternsPage() {
  const { courseId, exerciseId } = useParams<{ courseId: string; exerciseId: string }>();
  const sessions = usePatternsStore((s) => s.sessions);
  const isLoading = usePatternsStore((s) => s.isLoading);
  const error = usePatternsStore((s) => s.error);
  const fetchSessions = usePatternsStore((s) => s.fetchSessions);
  const navigate = useNavigate();

  const [commissions, setCommissions] = useState<CommissionOption[]>(EMPTY_COMMISSIONS);
  const [commissionId, setCommissionId] = useState('');

  useEffect(() => {
    if (!courseId) return;
    apiClient.get<CommissionOption[]>(`/v1/courses/${courseId}/commissions?per_page=50`).then((res) => {
      const items = Array.isArray(res.data) ? res.data : [];
      setCommissions(items);
      if (items.length > 0 && !commissionId) setCommissionId(items[0].id);
    }).catch(() => setCommissions(EMPTY_COMMISSIONS));
  }, [courseId]);

  useEffect(() => {
    if (commissionId && exerciseId) {
      fetchSessions(commissionId, exerciseId);
    }
  }, [commissionId, exerciseId, fetchSessions]);

  const items = sessions.length > 0 ? sessions : EMPTY_SESSIONS;

  // Mock N2 scores — in real use these come from metrics endpoint
  const n2Scores: number[] = [];
  const riskDistribution: Record<string, number> = {};

  return (
    <div className="space-y-6">
      <div>
        <span className="inline-block rounded-full bg-[var(--color-accent-50)] px-3 py-1 text-[0.6875rem] font-semibold uppercase tracking-[0.15em] text-[var(--color-accent-700)] dark:bg-[var(--color-accent-900)]/20 dark:text-[var(--color-accent-400)]">
          Patrones de Ejercicio
        </span>
        <h1 className="mt-3 text-[1.75rem] font-bold tracking-tight text-[var(--color-text-primary)]">
          Ejercicio {exerciseId?.slice(0, 8)}
        </h1>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-[0.6875rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
          Comision
        </label>
        <select
          value={commissionId}
          onChange={(e) => setCommissionId(e.target.value)}
          className="max-w-md rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[0.8125rem] text-[var(--color-text-primary)] outline-none transition-colors focus:border-[var(--color-accent-500)]"
        >
          <option value="">Seleccionar comision</option>
          {commissions.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} ({c.year} S{c.semester})
            </option>
          ))}
        </select>
      </div>

      {isLoading && (
        <p className="text-[0.875rem] text-[var(--color-text-tertiary)]">Cargando patrones...</p>
      )}
      {error && <p className="text-[0.875rem] text-[var(--color-error-600)]">{error}</p>}

      {items.length > 0 && (
        <>
          <div className="grid gap-6 lg:grid-cols-2">
            <StrategyDistribution n2Scores={n2Scores} />
            <ErrorPatternsSummary
              avgCodeRuns={0}
              lowEfficiencyPct={0}
              riskDistribution={riskDistribution}
            />
          </div>

          <div className="overflow-x-auto rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)]">
            <table className="w-full text-left text-[0.8125rem]">
              <thead>
                <tr className="border-b border-[var(--color-border)]">
                  <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">Alumno</th>
                  <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">Estado</th>
                  <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">Inicio</th>
                  <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">Accion</th>
                </tr>
              </thead>
              <tbody>
                {items.map((s) => (
                  <tr
                    key={s.id}
                    className="cursor-pointer border-b border-[var(--color-border)]/50 transition-colors hover:bg-[var(--color-neutral-50)] dark:hover:bg-[var(--color-neutral-800)]/30"
                    onClick={() => navigate(`/teacher/trace/${s.id}`)}
                  >
                    <td className="px-4 py-3 font-mono text-[0.75rem] text-[var(--color-text-tertiary)]">
                      {s.student_id.slice(0, 8)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-[0.6875rem] font-semibold uppercase ${
                        s.status === 'closed'
                          ? 'bg-[var(--color-success-50)] text-[var(--color-success-700)]'
                          : 'bg-[var(--color-info-50)] text-[var(--color-info-700)]'
                      }`}>
                        {s.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-[0.75rem] tabular-nums text-[var(--color-text-tertiary)]">
                      {new Date(s.started_at).toLocaleDateString('es-AR')}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[0.75rem] font-medium text-[var(--color-accent-600)]">
                        Ver traza
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
