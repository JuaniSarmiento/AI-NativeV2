import { useNavigate } from 'react-router-dom';
import { useTeacherDashboardStore } from './store';
import type { StudentSummary, SortField, RiskLevel } from './types';
import { RISK_LABELS } from './types';
import RiskBadge from './RiskBadge';
import { apiClient } from '@/shared/lib/api-client';

const EMPTY_STUDENTS: StudentSummary[] = [];

const COLUMNS: { key: SortField; label: string }[] = [
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

function formatScore(val: number | null): string {
  if (val === null) return '-';
  return val.toFixed(1);
}

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
    const aVal = a[sortField] ?? 0;
    const bVal = b[sortField] ?? 0;
    return ((aVal as number) - (bVal as number)) * dir;
  });

  return (
    <div className="overflow-x-auto rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)]">
      <table className="w-full text-left text-[0.8125rem]">
        <thead>
          <tr className="border-b border-[var(--color-border)]">
            <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">
              Alumno
            </th>
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                className="cursor-pointer px-4 py-3 font-semibold text-[var(--color-text-secondary)] transition-colors hover:text-[var(--color-text-primary)]"
                onClick={() => setSort(col.key)}
              >
                {col.label}
                {sortField === col.key && (
                  <span className="ml-1 text-[0.625rem]">
                    {sortDirection === 'asc' ? '\u2191' : '\u2193'}
                  </span>
                )}
              </th>
            ))}
            <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">
              Accion
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((student) => (
            <tr
              key={student.student_id}
              className={`cursor-pointer border-b border-[var(--color-border)]/50 transition-colors hover:bg-[var(--color-neutral-50)] dark:hover:bg-[var(--color-neutral-800)]/30 ${
                selectedStudentId === student.student_id
                  ? 'bg-[var(--color-accent-50)]/50 dark:bg-[var(--color-accent-900)]/10'
                  : ''
              }`}
              onClick={() =>
                setSelectedStudent(
                  selectedStudentId === student.student_id ? null : student.student_id,
                )
              }
            >
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
              <td className="px-4 py-3 tabular-nums text-[var(--color-text-primary)]">
                {formatScore(student.latest_n1)}
              </td>
              <td className="px-4 py-3 tabular-nums text-[var(--color-text-primary)]">
                {formatScore(student.latest_n2)}
              </td>
              <td className="px-4 py-3 tabular-nums text-[var(--color-text-primary)]">
                {formatScore(student.latest_n3)}
              </td>
              <td className="px-4 py-3 tabular-nums text-[var(--color-text-primary)]">
                {formatScore(student.latest_n4)}
              </td>
              <td className="px-4 py-3 tabular-nums text-[var(--color-text-primary)]">
                {formatScore(student.latest_qe)}
              </td>
              <td className="px-4 py-3">
                <span className={riskBadgeClasses(student.latest_risk_level)}>
                  {RISK_LABELS[(student.latest_risk_level ?? 'low') as keyof typeof RISK_LABELS] ?? '-'}
                </span>
              </td>
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
                    } catch { /* no sessions */ }
                  }}
                  className="text-[0.75rem] font-medium text-[var(--color-accent-600)] transition-colors hover:text-[var(--color-accent-700)]"
                >
                  Ver traza
                </button>
              </td>
            </tr>
          ))}
          {sorted.length === 0 && (
            <tr>
              <td
                colSpan={8}
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
