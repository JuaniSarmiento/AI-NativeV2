import { useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { useTeacherDashboardStore } from './store';
import { apiClient } from '@/shared/lib/api-client';
import N4RadarChart from './N4RadarChart';
import StudentScoresTable from './StudentScoresTable';
import RiskDistributionCard from './RiskDistributionCard';
import RiskAlertsTable from './RiskAlertsTable';
import type { StudentSummary, RiskLevel } from './types';
import { RISK_LABELS } from './types';

interface CommissionOption {
  id: string;
  name: string;
  year: number;
  semester: number;
}

interface ActivityOption {
  id: string;
  title: string;
  status: string;
}

const EMPTY_DISTRIBUTION: Record<string, number> = {};
const EMPTY_COMMISSIONS: CommissionOption[] = [];
const EMPTY_ACTIVITIES: ActivityOption[] = [];

export default function TeacherDashboard() {
  const { courseId } = useParams<{ courseId: string }>();
  const [searchParams] = useSearchParams();
  const dashboard = useTeacherDashboardStore((s) => s.dashboard);
  const isLoading = useTeacherDashboardStore((s) => s.isLoading);
  const error = useTeacherDashboardStore((s) => s.error);
  const selectedStudentId = useTeacherDashboardStore((s) => s.selectedStudentId);
  const riskFilter = useTeacherDashboardStore((s) => s.riskFilter);
  const fetchDashboard = useTeacherDashboardStore((s) => s.fetchDashboard);
  const setRiskFilter = useTeacherDashboardStore((s) => s.setRiskFilter);
  const fetchRisks = useTeacherDashboardStore((s) => s.fetchRisks);
  const triggerAssessment = useTeacherDashboardStore((s) => s.triggerAssessment);

  const [commissions, setCommissions] = useState<CommissionOption[]>(EMPTY_COMMISSIONS);
  const [activities, setActivities] = useState<ActivityOption[]>(EMPTY_ACTIVITIES);
  const [commissionId, setCommissionId] = useState(searchParams.get('commission') ?? '');
  const [exerciseId, setExerciseId] = useState('');

  // Fetch commissions and exercises for the course
  useEffect(() => {
    if (!courseId) return;
    apiClient
      .get<CommissionOption[]>(`/v1/courses/${courseId}/commissions?per_page=50`)
      .then((res) => {
        const items = Array.isArray(res.data) ? res.data : [];
        setCommissions(items);
        if (!commissionId && items.length > 0) {
          const fromUrl = searchParams.get('commission');
          setCommissionId(fromUrl && items.some((c) => c.id === fromUrl) ? fromUrl : items[0].id);
        }
      })
      .catch(() => setCommissions(EMPTY_COMMISSIONS));

    apiClient
      .get<ActivityOption & { course_id: string }[]>('/v1/activities')
      .then((res) => {
        const all = Array.isArray(res.data) ? res.data : [];
        setActivities(
          (all as (ActivityOption & { course_id: string })[])
            .filter((a) => a.course_id === courseId && a.status === 'published'),
        );
      })
      .catch(() => setActivities(EMPTY_ACTIVITIES));
  }, [courseId]);
  const [isAssessing, setIsAssessing] = useState(false);

  useEffect(() => {
    if (courseId && commissionId) {
      fetchDashboard(courseId, commissionId, exerciseId || undefined);
      fetchRisks(commissionId);
    }
  }, [courseId, commissionId, exerciseId, fetchDashboard, fetchRisks]);

  const selectedStudent: StudentSummary | null =
    dashboard?.students.find((s) => s.student_id === selectedStudentId) ?? null;

  const riskDistribution = dashboard?.risk_distribution ?? EMPTY_DISTRIBUTION;

  const handleTriggerAssessment = async () => {
    if (!commissionId) return;
    setIsAssessing(true);
    await triggerAssessment(commissionId);
    setIsAssessing(false);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <span className="inline-block rounded-full bg-[var(--color-accent-50)] px-3 py-1 text-[0.6875rem] font-semibold uppercase tracking-[0.15em] text-[var(--color-accent-700)] dark:bg-[var(--color-accent-900)]/20 dark:text-[var(--color-accent-400)]">
          Dashboard Cognitivo
        </span>
        <h1 className="mt-3 text-[1.75rem] font-bold tracking-tight text-[var(--color-text-primary)]">
          Metricas de la Actividad
        </h1>
        <p className="mt-1 text-[0.875rem] text-[var(--color-text-secondary)]">
          Perfil N1-N4, calidad epistemica y distribucion de riesgo por actividad.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-end gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-[0.6875rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
            Comision
          </label>
          <select
            value={commissionId}
            onChange={(e) => setCommissionId(e.target.value)}
            className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[0.8125rem] text-[var(--color-text-primary)] outline-none transition-colors focus:border-[var(--color-accent-500)]"
          >
            <option value="">Seleccionar comision</option>
            {commissions.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.year} S{c.semester})
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-[0.6875rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
            Actividad
          </label>
          <select
            value={exerciseId}
            onChange={(e) => setExerciseId(e.target.value)}
            className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[0.8125rem] text-[var(--color-text-primary)] outline-none transition-colors focus:border-[var(--color-accent-500)]"
          >
            <option value="">Todas las actividades</option>
            {activities.map((a) => (
              <option key={a.id} value={a.id}>
                {a.title}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-[0.6875rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
            Filtrar riesgo
          </label>
          <select
            value={riskFilter ?? ''}
            onChange={(e) => setRiskFilter(e.target.value || null)}
            className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[0.8125rem] text-[var(--color-text-primary)] outline-none transition-colors focus:border-[var(--color-accent-500)]"
          >
            <option value="">Todos</option>
            {(['low', 'medium', 'high', 'critical'] as RiskLevel[]).map((level) => (
              <option key={level} value={level}>
                {RISK_LABELS[level]}
              </option>
            ))}
          </select>
        </div>
        {commissionId && (
          <button
            onClick={handleTriggerAssessment}
            disabled={isAssessing}
            className="rounded-[var(--radius-md)] bg-[var(--color-accent-600)] px-4 py-2 text-[0.8125rem] font-semibold text-white transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-[var(--color-accent-700)] active:scale-[0.98] disabled:opacity-50"
          >
            {isAssessing ? 'Evaluando...' : 'Evaluar Riesgo'}
          </button>
        )}
      </div>

      {/* Loading / Error */}
      {isLoading && (
        <p className="text-[0.875rem] text-[var(--color-text-tertiary)]">
          Cargando metricas...
        </p>
      )}
      {error && (
        <p className="text-[0.875rem] text-[var(--color-error-600)]">{error}</p>
      )}

      {/* Dashboard content */}
      {dashboard && !isLoading && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <SummaryCard label="Alumnos" value={String(dashboard.student_count)} />
            <SummaryCard label="Qe promedio" value={dashboard.avg_qe?.toFixed(1) ?? '-'} />
            <SummaryCard label="N1 promedio" value={dashboard.avg_n1?.toFixed(1) ?? '-'} />
            <SummaryCard label="Dep. promedio" value={dashboard.avg_dependency?.toFixed(3) ?? '-'} />
          </div>

          {/* Charts row */}
          <div className="grid gap-6 lg:grid-cols-2">
            <N4RadarChart dashboard={dashboard} selectedStudent={selectedStudent} />
            <RiskDistributionCard distribution={riskDistribution} />
          </div>

          {/* Students table */}
          <StudentScoresTable />

          {/* Risk alerts */}
          <div>
            <h2 className="mb-3 text-[0.9375rem] font-bold tracking-tight text-[var(--color-text-primary)]">
              Alertas de Riesgo
            </h2>
            <RiskAlertsTable />
          </div>
        </>
      )}

      {!dashboard && !isLoading && !error && (
        <div className="rounded-[var(--radius-lg)] border border-dashed border-[var(--color-border)] p-12 text-center">
          <p className="text-[0.9375rem] text-[var(--color-text-tertiary)]">
            Selecciona una comision para ver las metricas.
          </p>
        </div>
      )}
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <p className="text-[0.6875rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
        {label}
      </p>
      <p className="mt-1 text-[1.5rem] font-bold tabular-nums tracking-tight text-[var(--color-text-primary)]">
        {value}
      </p>
    </div>
  );
}
