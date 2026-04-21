import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTeacherDashboardStore } from './store';
import type { StudentSummary, SortField, RiskLevel, AppropriationType } from './types';
import {
  RISK_LABELS,
  APPROPRIATION_LABELS,
  APPROPRIATION_BADGE_CLASSES,
} from './types';
import RiskBadge from './RiskBadge';
import { apiClient } from '@/shared/lib/api-client';
import { CoherenceSemaphores } from './CoherenceSemaphores';
import { ScoreBreakdown } from './ScoreBreakdown';

const EMPTY_STUDENTS: StudentSummary[] = [];

// Columns that map 1:1 to a SortField
const SCORE_COLUMNS: { key: SortField; label: string }[] = [
  { key: 'latest_n1', label: 'N1' },
  { key: 'latest_n2', label: 'N2' },
  { key: 'latest_n3', label: 'N3' },
  { key: 'latest_n4', label: 'N4' },
  { key: 'latest_qe', label: 'Qe' },
  { key: 'latest_risk_level', label: 'Riesgo' },
];

function riskSortValue(level: string | null): number {
  const order: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
  return order[level ?? 'low'] ?? 4;
}

function riskBadgeClasses(level: string | null): string {
  const base =
    'inline-block rounded-full px-2.5 py-0.5 text-[0.6875rem] font-semibold uppercase tracking-[0.08em]';
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

function formatScore(val: number | null): string {
  if (val === null) return '-';
  return val.toFixed(1);
}

function scoreColor(val: number | null): string {
  if (val === null) return 'text-[var(--color-text-tertiary)]';
  if (val >= 70) return 'text-[var(--color-success-600)] dark:text-[var(--color-success-400)]';
  if (val >= 40) return 'text-[var(--color-warning-600)] dark:text-[var(--color-warning-400)]';
  return 'text-[var(--color-error-600)] dark:text-[var(--color-error-400)]';
}

function scoreBarColor(val: number | null): string {
  if (val === null) return 'bg-[var(--color-neutral-200)] dark:bg-[var(--color-neutral-700)]';
  if (val >= 70) return 'bg-[var(--color-success-500)]';
  if (val >= 40) return 'bg-[var(--color-warning-500)]';
  return 'bg-[var(--color-error-500)]';
}

// ── N1-N4 mini-bar strip ─────────────────────────────────────────────────────

const N_DIMENSIONS: {
  key: 'latest_n1' | 'latest_n2' | 'latest_n3' | 'latest_n4';
  label: string;
}[] = [
  { key: 'latest_n1', label: 'N1' },
  { key: 'latest_n2', label: 'N2' },
  { key: 'latest_n3', label: 'N3' },
  { key: 'latest_n4', label: 'N4' },
];

function N1N4MiniBars({ student }: { student: StudentSummary }) {
  return (
    <div className="flex flex-col gap-0.5" aria-label="Puntajes N1 a N4">
      {N_DIMENSIONS.map((dim) => {
        const val = student[dim.key];
        const isN4 = dim.key === 'latest_n4';
        const title =
          isN4 && val === null
            ? `${dim.label}: Sin interaccion con tutor`
            : `${dim.label}: ${val != null ? val.toFixed(1) : 'Sin datos'}`;
        return (
          <div key={dim.key} className="flex items-center gap-1.5" title={title}>
            <span className="w-4 shrink-0 text-[0.5625rem] font-medium text-[var(--color-text-tertiary)]">
              {dim.label}
            </span>
            <div className="h-1.5 w-14 overflow-hidden rounded-full bg-[var(--color-neutral-100)] dark:bg-[var(--color-neutral-800)]">
              {isN4 && val === null ? (
                <div className="h-full w-full rounded-full bg-[var(--color-neutral-200)] dark:bg-[var(--color-neutral-700)]" />
              ) : (
                <div
                  className={`h-full rounded-full transition-all duration-500 ${scoreBarColor(val)}`}
                  style={{ width: `${val ?? 0}%` }}
                />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Appropriation badge ──────────────────────────────────────────────────────

function AppropriationBadge({ type }: { type: AppropriationType | null | undefined }) {
  if (!type) {
    return <span className="text-[0.6875rem] text-[var(--color-text-tertiary)]">Sin datos</span>;
  }
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-[0.6875rem] font-semibold uppercase tracking-[0.08em] ${APPROPRIATION_BADGE_CLASSES[type]}`}
    >
      {APPROPRIATION_LABELS[type]}
    </span>
  );
}

// ── N4 cell with "Sin interaccion" fallback ──────────────────────────────────

function N4Cell({ value }: { value: number | null }) {
  if (value === null) {
    return (
      <span className="text-[0.625rem] font-medium italic text-[var(--color-text-tertiary)]">
        Sin interaccion
      </span>
    );
  }
  return (
    <span className={`tabular-nums ${scoreColor(value)}`}>{formatScore(value)}</span>
  );
}

// ── Main table ───────────────────────────────────────────────────────────────

export default function StudentScoresTable() {
  const dashboard = useTeacherDashboardStore((s) => s.dashboard);
  const sortField = useTeacherDashboardStore((s) => s.sortField);
  const sortDirection = useTeacherDashboardStore((s) => s.sortDirection);
  const riskFilter = useTeacherDashboardStore((s) => s.riskFilter);
  const selectedStudentId = useTeacherDashboardStore((s) => s.selectedStudentId);
  const setSort = useTeacherDashboardStore((s) => s.setSort);
  const setSelectedStudent = useTeacherDashboardStore((s) => s.setSelectedStudent);
  const risks = useTeacherDashboardStore((s) => s.risks);
  const navigate = useNavigate();
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const students = dashboard?.students ?? EMPTY_STUDENTS;

  const riskByStudent = new Map(
    risks
      .filter((r) => r.acknowledged_at === null)
      .map((r) => [r.student_id, r.risk_level]),
  );

  const filtered = riskFilter
    ? students.filter((s) => s.latest_risk_level === riskFilter)
    : students;

  const sorted = [...filtered].sort((a, b) => {
    const dir = sortDirection === 'asc' ? 1 : -1;
    if (sortField === 'latest_risk_level') {
      return (riskSortValue(a.latest_risk_level) - riskSortValue(b.latest_risk_level)) * dir;
    }
    const numericFields: SortField[] = ['latest_n1', 'latest_n2', 'latest_n3', 'latest_n4', 'latest_qe'];
    if (numericFields.includes(sortField)) {
      return (
        ((a[sortField] as number | null) ?? 0) - ((b[sortField] as number | null) ?? 0)
      ) * dir;
    }
    return 0;
  });

  // Column count: student + mini-bars + N1 + N2 + N3 + N4 + Qe + Coherencia + Apropiacion + Riesgo + Accion = 11
  const totalCols = 11;

  return (
    <div className="overflow-x-auto rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)]">
      <table className="w-full text-left text-[0.8125rem]">
        <thead>
          <tr className="border-b border-[var(--color-border)]">
            <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">Alumno</th>
            {/* Static N1-N4 bars column */}
            <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">
              N1&#8211;N4
            </th>
            {/* Sortable score columns */}
            {SCORE_COLUMNS.map((col) => (
              <th
                key={col.key}
                className="cursor-pointer px-4 py-3 font-semibold text-[var(--color-text-secondary)] transition-colors hover:text-[var(--color-text-primary)]"
                onClick={() => setSort(col.key)}
              >
                {col.label}
                {sortField === col.key && (
                  <span className="ml-1 text-[0.625rem]" aria-hidden="true">
                    {sortDirection === 'asc' ? '\u2191' : '\u2193'}
                  </span>
                )}
              </th>
            ))}
            {/* Apropiacion */}
            <th
              className="cursor-pointer px-4 py-3 font-semibold text-[var(--color-text-secondary)] transition-colors hover:text-[var(--color-text-primary)]"
              onClick={() => setSort('latest_appropriation_type')}
            >
              Apropiacion
              {sortField === 'latest_appropriation_type' && (
                <span className="ml-1 text-[0.625rem]" aria-hidden="true">
                  {sortDirection === 'asc' ? '\u2191' : '\u2193'}
                </span>
              )}
            </th>
            <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">Coherencia</th>
            <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">Accion</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((student) => (
            <React.Fragment key={student.student_id}>
            <tr
              className={`cursor-pointer border-b border-[var(--color-border)]/50 transition-colors hover:bg-[var(--color-neutral-50)] dark:hover:bg-[var(--color-neutral-800)]/30 ${
                selectedStudentId === student.student_id
                  ? 'bg-[var(--color-accent-50)]/50 dark:bg-[var(--color-accent-900)]/10'
                  : ''
              }`}
              onClick={() => {
                setSelectedStudent(
                  selectedStudentId === student.student_id ? null : student.student_id,
                );
                setExpandedRow(
                  expandedRow === student.student_id ? null : student.student_id,
                );
              }}
            >
              {/* Alumno */}
              <td className="px-4 py-3 font-medium text-[var(--color-text-primary)]">
                <span className="font-mono text-[0.75rem] text-[var(--color-text-tertiary)]">
                  {student.student_id.slice(0, 8)}
                </span>
                {riskByStudent.has(student.student_id) && (
                  <span className="ml-2">
                    <RiskBadge level={riskByStudent.get(student.student_id)! as RiskLevel} />
                  </span>
                )}
              </td>
              {/* Mini-bars */}
              <td className="px-4 py-3">
                <N1N4MiniBars student={student} />
              </td>
              {/* N1 */}
              <td className="px-4 py-3 tabular-nums text-[var(--color-text-primary)]">
                <span className={scoreColor(student.latest_n1)}>{formatScore(student.latest_n1)}</span>
              </td>
              {/* N2 */}
              <td className="px-4 py-3 tabular-nums text-[var(--color-text-primary)]">
                <span className={scoreColor(student.latest_n2)}>{formatScore(student.latest_n2)}</span>
              </td>
              {/* N3 */}
              <td className="px-4 py-3 tabular-nums text-[var(--color-text-primary)]">
                <span className={scoreColor(student.latest_n3)}>{formatScore(student.latest_n3)}</span>
              </td>
              {/* N4 — "Sin interaccion" when null */}
              <td className="px-4 py-3 tabular-nums">
                <N4Cell value={student.latest_n4} />
              </td>
              {/* Qe */}
              <td className="px-4 py-3 tabular-nums text-[var(--color-text-primary)]">
                {formatScore(student.latest_qe)}
              </td>
              {/* Riesgo */}
              <td className="px-4 py-3">
                <span className={riskBadgeClasses(student.latest_risk_level)}>
                  {RISK_LABELS[(student.latest_risk_level ?? 'low') as keyof typeof RISK_LABELS] ??
                    '-'}
                </span>
              </td>
              {/* Apropiacion */}
              <td className="px-4 py-3">
                <AppropriationBadge type={student.latest_appropriation_type} />
              </td>
              {/* Coherencia semaphores */}
              <td className="px-4 py-3">
                <CoherenceSemaphores
                  temporal={student.latest_temporal_coherence}
                  codeDiscourse={student.latest_code_discourse}
                  interIteration={student.latest_inter_iteration}
                />
              </td>
              {/* Accion */}
              <td className="px-4 py-3">
                <button
                  onClick={async (e) => {
                    e.stopPropagation();
                    const commId = dashboard?.commission_id;
                    if (!commId) return;
                    try {
                      const res = await apiClient.get<{ id: string }[]>(
                        `/v1/cognitive/sessions?commission_id=${commId}&student_id=${student.student_id}&per_page=1`,
                      );
                      const sessions = res.data;
                      if (sessions.length > 0) {
                        navigate(`/teacher/trace/${sessions[0].id}`);
                      }
                    } catch {
                      /* no sessions */
                    }
                  }}
                  className="min-h-11 min-w-11 text-[0.75rem] font-medium text-[var(--color-accent-600)] transition-colors hover:text-[var(--color-accent-700)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent-500)]"
                >
                  Ver traza
                </button>
              </td>
            </tr>
            {expandedRow === student.student_id && (
              <tr className="border-b border-[var(--color-border)]/50 bg-[var(--color-surface-alt)]">
                <td colSpan={totalCols} className="px-6 py-2">
                  <ScoreBreakdown breakdown={student.latest_score_breakdown} />
                </td>
              </tr>
            )}
            </React.Fragment>
          ))}
          {sorted.length === 0 && (
            <tr>
              <td
                colSpan={totalCols}
                className="px-4 py-8 text-center text-[var(--color-text-tertiary)]"
              >
                Sin datos de alumnos para esta comision.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
