import { useEffect, useState } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { useTeacherDashboardStore } from './store';
import { apiClient } from '@/shared/lib/api-client';
import type { StudentSummary, RiskLevel, SortField } from './types';
import { RISK_LABELS, RISK_DESCRIPTIONS } from './types';
import RiskBadge from './RiskBadge';

interface CommissionOption {
  id: string;
  name: string;
  year: number;
  semester: number;
}

interface ExerciseOption {
  id: string;
  title: string;
}

const EMPTY_COMMISSIONS: CommissionOption[] = [];
const EMPTY_EXERCISES: ExerciseOption[] = [];
const EMPTY_STUDENTS: StudentSummary[] = [];

function riskSortValue(level: string | null): number {
  const order: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
  return order[level ?? 'low'] ?? 4;
}

function formatScore(val: number | null): string {
  if (val === null || val === undefined) return '-';
  return val.toFixed(0);
}

function scoreColor(val: number | null): string {
  if (val === null) return 'text-[var(--color-text-tertiary)]';
  if (val >= 70) return 'text-[var(--color-success-600)] dark:text-[var(--color-success-400)]';
  if (val >= 40) return 'text-[var(--color-warning-600)] dark:text-[var(--color-warning-400)]';
  return 'text-[var(--color-error-600)] dark:text-[var(--color-error-400)]';
}

export default function TeacherDashboard() {
  const { courseId } = useParams<{ courseId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const dashboard = useTeacherDashboardStore((s) => s.dashboard);
  const isLoading = useTeacherDashboardStore((s) => s.isLoading);
  const error = useTeacherDashboardStore((s) => s.error);
  const selectedStudentId = useTeacherDashboardStore((s) => s.selectedStudentId);
  const riskFilter = useTeacherDashboardStore((s) => s.riskFilter);
  const sortField = useTeacherDashboardStore((s) => s.sortField);
  const sortDirection = useTeacherDashboardStore((s) => s.sortDirection);
  const fetchDashboard = useTeacherDashboardStore((s) => s.fetchDashboard);
  const fetchRisks = useTeacherDashboardStore((s) => s.fetchRisks);
  const setRiskFilter = useTeacherDashboardStore((s) => s.setRiskFilter);
  const setSort = useTeacherDashboardStore((s) => s.setSort);
  const setSelectedStudent = useTeacherDashboardStore((s) => s.setSelectedStudent);
  const triggerAssessment = useTeacherDashboardStore((s) => s.triggerAssessment);

  const [commissions, setCommissions] = useState<CommissionOption[]>(EMPTY_COMMISSIONS);
  const [exercises, setExercises] = useState<ExerciseOption[]>(EMPTY_EXERCISES);
  const [commissionId, setCommissionId] = useState(searchParams.get('commission') ?? '');
  const [exerciseId, setExerciseId] = useState('');
  const [isAssessing, setIsAssessing] = useState(false);

  useEffect(() => {
    if (!courseId) return;
    setCommissionId(searchParams.get('commission') ?? '');
    setExerciseId('');
  }, [courseId]);

  useEffect(() => {
    if (!courseId) return;
    apiClient
      .get(`/v1/courses/${courseId}/commissions?per_page=50`)
      .then((res) => {
        const envelope = res.data as { data?: CommissionOption[] };
        const items = Array.isArray(envelope.data) ? envelope.data : Array.isArray(res.data) ? res.data as unknown as CommissionOption[] : [];
        setCommissions(items);
        if (items.length > 0) {
          setCommissionId((prev) => {
            if (prev && items.some((c) => c.id === prev)) return prev;
            return items[0].id;
          });
        }
      })
      .catch(() => setCommissions(EMPTY_COMMISSIONS));

    apiClient
      .get(`/v1/courses/${courseId}/exercises?per_page=100`)
      .then((res) => {
        const envelope = res.data as { data?: ExerciseOption[] };
        const all = Array.isArray(envelope.data) ? envelope.data : Array.isArray(res.data) ? res.data as unknown as ExerciseOption[] : [];
        setExercises(all);
      })
      .catch(() => setExercises(EMPTY_EXERCISES));
  }, [courseId]);

  useEffect(() => {
    if (courseId && commissionId) {
      fetchDashboard(courseId, commissionId, exerciseId || undefined);
      fetchRisks(commissionId);
    }
  }, [courseId, commissionId, exerciseId, fetchDashboard, fetchRisks]);

  const students = dashboard?.students ?? EMPTY_STUDENTS;
  const filtered = riskFilter
    ? students.filter((s) => s.latest_risk_level === riskFilter)
    : students;

  const sorted = [...filtered].sort((a, b) => {
    const dir = sortDirection === 'asc' ? 1 : -1;
    if (sortField === 'latest_risk_level') {
      return (riskSortValue(a.latest_risk_level) - riskSortValue(b.latest_risk_level)) * dir;
    }
    if (sortField === 'student_name') {
      const aName = a.student_name ?? a.student_id;
      const bName = b.student_name ?? b.student_id;
      return aName.localeCompare(bName) * dir;
    }
    if (sortField === 'session_count') {
      return (a.session_count - b.session_count) * dir;
    }
    if (sortField === 'latest_qe') {
      return ((a.latest_qe ?? 0) - (b.latest_qe ?? 0)) * dir;
    }
    return 0;
  });

  const selectedStudent = students.find((s) => s.student_id === selectedStudentId) ?? null;

  const riskDist = dashboard?.risk_distribution ?? {};
  const totalRisk = Object.values(riskDist).reduce((s, n) => s + n, 0);

  const handleAssess = async () => {
    if (!commissionId) return;
    setIsAssessing(true);
    await triggerAssessment(commissionId);
    setIsAssessing(false);
  };

  const handleViewTrace = (studentId: string) => {
    if (!commissionId) return;
    navigate(`/teacher/students/${studentId}/activity?commission=${commissionId}`);
  };

  const commissionName = commissions.find((c) => c.id === commissionId)?.name ?? '';

  return (
    <div className="mx-auto max-w-6xl space-y-8 px-4 py-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-[var(--color-text-primary)]">
          Seguimiento Cognitivo
        </h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
          Observa como aprenden tus alumnos: su proceso de pensamiento, no solo el resultado.
        </p>
      </div>

      {/* Selectors */}
      <div className="flex flex-wrap items-end gap-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        <div className="flex min-w-[180px] flex-col gap-1.5">
          <label className="text-xs font-medium text-[var(--color-text-secondary)]">
            Comision
          </label>
          <select
            value={commissionId}
            onChange={(e) => setCommissionId(e.target.value)}
            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent-500)] focus:ring-1 focus:ring-[var(--color-accent-500)]"
          >
            <option value="">Seleccionar comision</option>
            {commissions.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.year}-S{c.semester})
              </option>
            ))}
          </select>
        </div>

        <div className="flex min-w-[200px] flex-col gap-1.5">
          <label className="text-xs font-medium text-[var(--color-text-secondary)]">
            Actividad
          </label>
          <select
            value={exerciseId}
            onChange={(e) => setExerciseId(e.target.value)}
            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent-500)] focus:ring-1 focus:ring-[var(--color-accent-500)]"
          >
            <option value="">Todas las actividades</option>
            {exercises.map((e) => (
              <option key={e.id} value={e.id}>
                {e.title}
              </option>
            ))}
          </select>
        </div>

        <div className="flex min-w-[140px] flex-col gap-1.5">
          <label className="text-xs font-medium text-[var(--color-text-secondary)]">
            Filtrar por riesgo
          </label>
          <select
            value={riskFilter ?? ''}
            onChange={(e) => setRiskFilter(e.target.value || null)}
            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent-500)] focus:ring-1 focus:ring-[var(--color-accent-500)]"
          >
            <option value="">Todos</option>
            {(['critical', 'high', 'medium', 'low'] as const).map((level) => (
              <option key={level} value={level}>
                {RISK_LABELS[level]}
              </option>
            ))}
          </select>
        </div>

        {commissionId && (
          <button
            onClick={handleAssess}
            disabled={isAssessing}
            className="rounded-lg bg-[var(--color-accent-600)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--color-accent-700)] disabled:opacity-50"
          >
            {isAssessing ? 'Evaluando...' : 'Evaluar Riesgo'}
          </button>
        )}
      </div>

      {/* Loading / Error */}
      {isLoading && (
        <div className="flex items-center gap-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--color-accent-500)] border-t-transparent" />
          <span className="text-sm text-[var(--color-text-secondary)]">Cargando metricas...</span>
        </div>
      )}
      {error && (
        <div className="rounded-xl border border-[var(--color-error-200)] bg-[var(--color-error-50)] p-4 dark:border-[var(--color-error-800)] dark:bg-[var(--color-error-900)]/20">
          <p className="text-sm text-[var(--color-error-700)] dark:text-[var(--color-error-400)]">{error}</p>
        </div>
      )}

      {/* Dashboard content */}
      {dashboard && !isLoading && (
        <>
          {/* Overview cards */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <OverviewCard
              label="Alumnos"
              value={String(dashboard.student_count)}
              description="en esta comision"
            />
            <OverviewCard
              label="Calidad Epistemica"
              value={dashboard.avg_qe != null ? dashboard.avg_qe.toFixed(0) : '-'}
              description="promedio Qe (0-100)"
              valueColor={scoreColor(dashboard.avg_qe ?? null)}
            />
            <OverviewCard
              label="Sesiones totales"
              value={String(students.reduce((sum, s) => sum + s.session_count, 0))}
              description="sesiones cognitivas"
            />
            <RiskOverviewCard distribution={riskDist} total={totalRisk} />
          </div>

          {/* Explanation */}
          <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
            <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
              Como leer este dashboard
            </h2>
            <p className="mt-2 text-xs leading-relaxed text-[var(--color-text-secondary)]">
              Este panel analiza el <strong>proceso cognitivo</strong> de cada alumno, no solo si el codigo funciona.
              La <strong>Calidad Epistemica (Qe)</strong> mide que tan bien razona el alumno: si comprende el problema,
              planifica una estrategia, valida sus soluciones y usa la IA como herramienta de aprendizaje (no como oraculo).
              El <strong>nivel de riesgo</strong> indica si un alumno necesita atencion: un riesgo alto puede significar
              dependencia excesiva de la IA, desvinculacion del proceso, o estancamiento. Hace click en un alumno para
              ver el detalle de su traza cognitiva.
            </p>
          </div>

          {/* Students table */}
          <div className="overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)]">
            <div className="border-b border-[var(--color-border)] px-5 py-3">
              <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                Alumnos
              </h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--color-border)] bg-[var(--color-neutral-50)] dark:bg-[var(--color-neutral-800)]/30">
                    <SortHeader field="student_name" label="Alumno" current={sortField} direction={sortDirection} onSort={setSort} />
                    <SortHeader field="session_count" label="Sesiones" current={sortField} direction={sortDirection} onSort={setSort} />
                    <SortHeader field="latest_qe" label="Qe" current={sortField} direction={sortDirection} onSort={setSort} />
                    <SortHeader field="latest_risk_level" label="Riesgo" current={sortField} direction={sortDirection} onSort={setSort} />
                    <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-[var(--color-text-tertiary)]">
                      Accion
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((student) => (
                    <tr
                      key={student.student_id}
                      className={`cursor-pointer border-b border-[var(--color-border)]/50 transition-colors hover:bg-[var(--color-neutral-50)] dark:hover:bg-[var(--color-neutral-800)]/20 ${
                        selectedStudentId === student.student_id
                          ? 'bg-[var(--color-accent-50)]/60 dark:bg-[var(--color-accent-900)]/10'
                          : ''
                      }`}
                      onClick={() =>
                        setSelectedStudent(
                          selectedStudentId === student.student_id ? null : student.student_id,
                        )
                      }
                    >
                      <td className="px-4 py-3">
                        <div className="flex flex-col">
                          <span className="font-medium text-[var(--color-text-primary)]">
                            {student.student_name ?? 'Sin nombre'}
                          </span>
                          <span className="text-xs text-[var(--color-text-tertiary)]">
                            {student.student_email ?? student.student_id.slice(0, 12)}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3 tabular-nums text-[var(--color-text-primary)]">
                        {student.session_count}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-lg font-bold tabular-nums ${scoreColor(student.latest_qe)}`}>
                          {formatScore(student.latest_qe)}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {student.latest_risk_level ? (
                          <RiskBadge level={student.latest_risk_level as RiskLevel} />
                        ) : (
                          <span className="text-xs text-[var(--color-text-tertiary)]">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleViewTrace(student.student_id);
                          }}
                          className="rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-xs font-medium text-[var(--color-accent-600)] transition-colors hover:bg-[var(--color-accent-50)] dark:hover:bg-[var(--color-accent-900)]/10"
                        >
                          Ver traza
                        </button>
                      </td>
                    </tr>
                  ))}
                  {sorted.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-4 py-12 text-center text-sm text-[var(--color-text-tertiary)]">
                        {riskFilter
                          ? `Sin alumnos con riesgo "${RISK_LABELS[riskFilter as RiskLevel] ?? riskFilter}".`
                          : 'Sin datos de alumnos para esta comision.'}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Selected student detail */}
          {selectedStudent && (
            <StudentDetailCard student={selectedStudent} commissionId={commissionId} />
          )}
        </>
      )}

      {/* Empty state */}
      {!dashboard && !isLoading && !error && (
        <div className="rounded-xl border border-dashed border-[var(--color-border)] p-16 text-center">
          <p className="text-base font-medium text-[var(--color-text-secondary)]">
            Selecciona una comision para ver el seguimiento cognitivo de tus alumnos.
          </p>
          <p className="mt-2 text-sm text-[var(--color-text-tertiary)]">
            El sistema analiza automaticamente como piensan y aprenden.
          </p>
        </div>
      )}
    </div>
  );
}

function OverviewCard({
  label,
  value,
  description,
  valueColor,
}: {
  label: string;
  value: string;
  description: string;
  valueColor?: string;
}) {
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <p className="text-xs font-medium text-[var(--color-text-tertiary)]">{label}</p>
      <p className={`mt-1 text-2xl font-bold tabular-nums tracking-tight ${valueColor ?? 'text-[var(--color-text-primary)]'}`}>
        {value}
      </p>
      <p className="mt-0.5 text-xs text-[var(--color-text-tertiary)]">{description}</p>
    </div>
  );
}

function RiskOverviewCard({
  distribution,
  total,
}: {
  distribution: Record<string, number>;
  total: number;
}) {
  const levels: RiskLevel[] = ['critical', 'high', 'medium', 'low'];

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <p className="text-xs font-medium text-[var(--color-text-tertiary)]">Distribucion de riesgo</p>
      <div className="mt-2 flex items-end gap-1">
        {levels.map((level) => {
          const count = distribution[level] ?? 0;
          const pct = total > 0 ? (count / total) * 100 : 0;
          const colorMap: Record<RiskLevel, string> = {
            critical: 'bg-[var(--color-error-500)]',
            high: 'bg-[var(--color-warning-600)]',
            medium: 'bg-[var(--color-warning-400)]',
            low: 'bg-[var(--color-success-500)]',
          };
          return (
            <div key={level} className="flex flex-1 flex-col items-center gap-1" title={`${RISK_LABELS[level]}: ${count}`}>
              <div className="flex h-12 w-full items-end justify-center">
                <div
                  className={`w-full rounded-t ${colorMap[level]} transition-all duration-500`}
                  style={{ height: `${Math.max(pct, count > 0 ? 15 : 0)}%` }}
                />
              </div>
              <span className="text-[0.625rem] font-medium text-[var(--color-text-tertiary)]">{count}</span>
            </div>
          );
        })}
      </div>
      <div className="mt-1 flex justify-between px-0.5">
        <span className="text-[0.5rem] text-[var(--color-text-tertiary)]">Crit</span>
        <span className="text-[0.5rem] text-[var(--color-text-tertiary)]">Alto</span>
        <span className="text-[0.5rem] text-[var(--color-text-tertiary)]">Med</span>
        <span className="text-[0.5rem] text-[var(--color-text-tertiary)]">Bajo</span>
      </div>
    </div>
  );
}

function SortHeader({
  field,
  label,
  current,
  direction,
  onSort,
}: {
  field: SortField;
  label: string;
  current: SortField;
  direction: 'asc' | 'desc';
  onSort: (field: SortField) => void;
}) {
  const isActive = current === field;
  return (
    <th
      className="cursor-pointer px-4 py-3 text-xs font-medium uppercase tracking-wider text-[var(--color-text-tertiary)] transition-colors hover:text-[var(--color-text-primary)]"
      onClick={() => onSort(field)}
    >
      {label}
      {isActive && (
        <span className="ml-1">{direction === 'asc' ? '\u2191' : '\u2193'}</span>
      )}
    </th>
  );
}

interface SessionItem {
  id: string;
  exercise_id: string;
  status: string;
  started_at: string;
  closed_at: string | null;
}

function StudentDetailCard({
  student,
  commissionId,
}: {
  student: StudentSummary;
  commissionId: string;
}) {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);

  useEffect(() => {
    if (!commissionId || !student.student_id) return;
    setLoadingSessions(true);
    apiClient
      .get(
        `/v1/cognitive/sessions?commission_id=${commissionId}&student_id=${student.student_id}&per_page=20`,
      )
      .then((res) => {
        const envelope = res.data as { data?: SessionItem[] };
        const items = Array.isArray(envelope.data) ? envelope.data : Array.isArray(res.data) ? res.data as unknown as SessionItem[] : [];
        setSessions(items);
      })
      .catch(() => setSessions([]))
      .finally(() => setLoadingSessions(false));
  }, [commissionId, student.student_id]);

  const dimensions = [
    { key: 'n1', label: 'Comprension', value: student.latest_n1, description: 'Entiende el problema antes de escribir codigo?' },
    { key: 'n2', label: 'Estrategia', value: student.latest_n2, description: 'Planifica su solucion o va directo al codigo?' },
    { key: 'n3', label: 'Validacion', value: student.latest_n3, description: 'Prueba y corrige su propio razonamiento?' },
    { key: 'n4', label: 'Uso de IA', value: student.latest_n4, description: 'Usa la IA criticamente o como oraculo?' },
  ];

  return (
    <div className="rounded-xl border border-[var(--color-accent-200)] bg-[var(--color-accent-50)]/30 p-5 dark:border-[var(--color-accent-800)] dark:bg-[var(--color-accent-900)]/10">
      <div>
        <h3 className="text-base font-semibold text-[var(--color-text-primary)]">
          {student.student_name ?? 'Alumno'}
        </h3>
        <p className="text-xs text-[var(--color-text-secondary)]">
          {student.student_email ?? student.student_id.slice(0, 12)} — {student.session_count} sesiones
        </p>
      </div>

      {/* N1-N4 detail */}
      <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {dimensions.map((dim) => (
          <div key={dim.key} className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
            <div className="flex items-baseline justify-between">
              <span className="text-xs font-medium text-[var(--color-text-secondary)]">{dim.label}</span>
              <span className={`text-lg font-bold tabular-nums ${scoreColor(dim.value)}`}>
                {formatScore(dim.value)}
              </span>
            </div>
            <p className="mt-1 text-[0.625rem] leading-snug text-[var(--color-text-tertiary)]">{dim.description}</p>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[var(--color-neutral-100)] dark:bg-[var(--color-neutral-800)]">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  (dim.value ?? 0) >= 70 ? 'bg-[var(--color-success-500)]'
                    : (dim.value ?? 0) >= 40 ? 'bg-[var(--color-warning-500)]'
                      : 'bg-[var(--color-error-500)]'
                }`}
                style={{ width: `${dim.value ?? 0}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      {student.latest_risk_level && (
        <div className="mt-3 flex items-center gap-2">
          <RiskBadge level={student.latest_risk_level as RiskLevel} />
          <span className="text-xs text-[var(--color-text-secondary)]">
            {RISK_DESCRIPTIONS[student.latest_risk_level as RiskLevel] ?? ''}
          </span>
        </div>
      )}

      {/* Sessions list */}
      <div className="mt-4">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-tertiary)]">
          Sesiones cognitivas
        </h4>
        {loadingSessions ? (
          <p className="mt-2 text-xs text-[var(--color-text-tertiary)]">Cargando sesiones...</p>
        ) : sessions.length === 0 ? (
          <p className="mt-2 text-xs text-[var(--color-text-tertiary)]">Sin sesiones registradas.</p>
        ) : (
          <div className="mt-2 space-y-1.5">
            {sessions.map((s) => (
              <button
                key={s.id}
                onClick={() => navigate(`/teacher/students/${student.student_id}/activity?commission=${commissionId}`)}
                className="flex w-full items-center justify-between rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-left transition-colors hover:bg-[var(--color-neutral-50)] dark:hover:bg-[var(--color-neutral-800)]/20"
              >
                <div>
                  <span className="text-xs font-medium text-[var(--color-text-primary)]">
                    {new Date(s.started_at).toLocaleString('es-AR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                  </span>
                  <span className={`ml-2 rounded-full px-2 py-0.5 text-[0.5625rem] font-semibold ${
                    s.status === 'closed'
                      ? 'bg-[var(--color-success-50)] text-[var(--color-success-700)] dark:bg-[var(--color-success-900)]/20 dark:text-[var(--color-success-400)]'
                      : 'bg-[var(--color-info-50)] text-[var(--color-info-700)] dark:bg-[var(--color-info-900)]/20 dark:text-[var(--color-info-400)]'
                  }`}>
                    {s.status === 'closed' ? 'Cerrada' : 'En curso'}
                  </span>
                </div>
                <span className="text-xs font-medium text-[var(--color-accent-600)]">Ver actividad completa →</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
