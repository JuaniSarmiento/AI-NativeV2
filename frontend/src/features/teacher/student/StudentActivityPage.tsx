import { useEffect, useState } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { apiClient } from '@/shared/lib/api-client';

interface ReportData {
  id: string;
  student_id: string;
  activity_id: string;
  narrative_md: string;
  structured_analysis: {
    student_name?: string;
    activity_title?: string;
    sessions_analyzed?: number;
    overall_scores?: Record<string, number | null>;
    risk_level?: string | null;
    patterns?: Array<{ type: string; severity: string; evidence: string }>;
    strengths?: Array<{ dimension: string; description: string; evidence: string }>;
    weaknesses?: Array<{ dimension: string; description: string; evidence: string }>;
    evolution?: { trend: string; detail: string };
    anomalies?: Array<{ type: string; detail?: string }>;
  };
  llm_provider: string;
  model_used: string;
  generated_at: string;
}

function renderMarkdown(md: string): string {
  let html = md
    .replace(/^## (.+)$/gm, '<h2 class="text-lg font-semibold mt-6 mb-3 text-[var(--color-text-primary)]">$1</h2>')
    .replace(/^### (.+)$/gm, '<h3 class="text-base font-medium mt-4 mb-2 text-[var(--color-text-primary)]">$1</h3>')
    .replace(/^\* (.+)$/gm, '<li class="ml-4 mb-1 list-disc text-[var(--color-text-secondary)]">$1</li>')
    .replace(/^\- (.+)$/gm, '<li class="ml-4 mb-1 list-disc text-[var(--color-text-secondary)]">$1</li>')
    .replace(/^\d+\.\s+(.+)$/gm, '<li class="ml-4 mb-1 list-decimal text-[var(--color-text-secondary)]">$1</li>')
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-[var(--color-text-primary)]">$1</strong>')
    .replace(/\n\n/g, '</p><p class="mb-3 text-sm leading-relaxed text-[var(--color-text-secondary)]">')
    .replace(/\n/g, '<br/>');
  return `<div class="text-sm leading-relaxed text-[var(--color-text-secondary)]">${html}</div>`;
}

export default function StudentActivityPage() {
  const { studentId } = useParams<{ studentId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const commissionId = searchParams.get('commission') ?? '';
  const activityId = searchParams.get('activity_id') ?? '';

  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!studentId || !commissionId) {
      setError('Faltan parámetros de navegación');
      setLoading(false);
      return;
    }
    if (!activityId) {
      setError('Seleccioná una actividad en el dashboard para ver el informe del alumno.');
      setLoading(false);
      return;
    }

    generateOrFetchReport();
  }, [studentId, commissionId, activityId]);

  async function generateOrFetchReport() {
    setLoading(true);
    setError(null);

    try {
      const res = await apiClient.get<ReportData | null>(
        `/v1/reports?student_id=${studentId}&activity_id=${activityId}`,
      );

      if (res.data) {
        setReport(res.data);
        setLoading(false);
        return;
      }

      const genRes = await apiClient.post<ReportData>('/v1/reports/generate', {
        student_id: studentId,
        activity_id: activityId,
        commission_id: commissionId,
      });
      setReport(genRes.data);
    } catch (err: unknown) {
      const detail = err instanceof Error ? err.message : 'Error al generar el informe';
      setError(detail);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-[var(--color-accent-500)] border-t-transparent" />
          <p className="text-sm font-medium text-[var(--color-text-secondary)]">
            Generando informe cognitivo...
          </p>
          <p className="text-xs text-[var(--color-text-tertiary)]">
            Analizando sesiones y generando narrativa con IA
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-10">
        <button
          onClick={() => navigate(-1)}
          className="mb-4 text-xs font-medium text-[var(--color-accent-600)] hover:underline"
        >
          ← Volver al dashboard
        </button>
        <div className="rounded-xl border border-[var(--color-error-200)] bg-[var(--color-error-50)] p-6 dark:border-[var(--color-error-800)] dark:bg-[var(--color-error-900)]/20">
          <h2 className="text-lg font-semibold text-[var(--color-error-700)] dark:text-[var(--color-error-400)]">
            No se pudo generar el informe
          </h2>
          <p className="mt-2 text-sm text-[var(--color-error-600)] dark:text-[var(--color-error-300)]">
            {error}
          </p>
        </div>
      </div>
    );
  }

  if (!report) return null;

  const { structured_analysis: analysis } = report;

  return (
    <div className="mx-auto max-w-4xl px-4 py-6">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate(-1)}
          className="mb-3 text-xs font-medium text-[var(--color-accent-600)] hover:underline"
        >
          ← Volver al dashboard
        </button>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-[var(--color-text-primary)]">
              Informe Cognitivo
            </h1>
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
              {analysis.student_name}
            </p>
            <p className="text-xs text-[var(--color-text-tertiary)]">
              {analysis.activity_title}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-[var(--color-text-tertiary)]">
              {analysis.sessions_analyzed} sesiones analizadas
            </p>
            <p className="text-xs text-[var(--color-text-tertiary)]">
              {new Date(report.generated_at).toLocaleDateString('es-AR', {
                day: 'numeric',
                month: 'short',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </p>
          </div>
        </div>
      </div>

      {/* Score cards */}
      {analysis.overall_scores && (
        <div className="mb-6 grid grid-cols-5 gap-3">
          {(['n1', 'n2', 'n3', 'n4', 'qe'] as const).map((key) => {
            const val = analysis.overall_scores?.[`${key}_avg`] ?? null;
            return (
              <div
                key={key}
                className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 text-center"
              >
                <p className="text-[0.625rem] font-semibold uppercase tracking-wider text-[var(--color-text-tertiary)]">
                  {key.toUpperCase()}
                </p>
                <p
                  className={`mt-1 text-2xl font-bold tabular-nums ${
                    val === null
                      ? 'text-[var(--color-text-tertiary)]'
                      : val >= 70
                        ? 'text-[var(--color-success-600)]'
                        : val >= 40
                          ? 'text-[var(--color-warning-600)]'
                          : 'text-[var(--color-error-600)]'
                  }`}
                >
                  {val !== null ? val.toFixed(0) : '—'}
                </p>
              </div>
            );
          })}
        </div>
      )}

      {/* Risk + evolution summary */}
      <div className="mb-6 flex items-center gap-4">
        {analysis.risk_level && (
          <span
            className={`inline-block rounded-full px-3 py-1 text-xs font-semibold ${
              analysis.risk_level === 'critical'
                ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                : analysis.risk_level === 'high'
                  ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'
                  : analysis.risk_level === 'medium'
                    ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300'
                    : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
            }`}
          >
            Riesgo: {analysis.risk_level}
          </span>
        )}
        {analysis.evolution && (
          <span className="text-xs text-[var(--color-text-secondary)]">
            Tendencia:{' '}
            <strong>
              {analysis.evolution.trend === 'improving'
                ? '↑ Mejorando'
                : analysis.evolution.trend === 'declining'
                  ? '↓ Declinando'
                  : analysis.evolution.trend === 'stable'
                    ? '→ Estable'
                    : '↕ Mixta'}
            </strong>
          </span>
        )}
      </div>

      {/* AI Narrative */}
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
        <div dangerouslySetInnerHTML={{ __html: renderMarkdown(report.narrative_md) }} />
      </div>

      {/* Footer */}
      <div className="mt-6 flex items-center justify-between border-t border-[var(--color-border)] pt-4">
        <p className="text-[0.625rem] text-[var(--color-text-tertiary)]">
          Generado con {report.llm_provider}/{report.model_used}
        </p>
        <button
          onClick={generateOrFetchReport}
          className="rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-xs font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-neutral-50)] dark:hover:bg-[var(--color-neutral-800)]"
        >
          Regenerar informe
        </button>
      </div>
    </div>
  );
}
