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
  };
  llm_provider: string;
  model_used: string;
  generated_at: string;
}

function renderMarkdown(md: string): string {
  let html = md
    .replace(/^## (.+)$/gm, '<h2 class="text-lg font-semibold mt-6 mb-2 text-[var(--color-text-primary)]">$1</h2>')
    .replace(/^### (.+)$/gm, '<h3 class="text-base font-medium mt-4 mb-1 text-[var(--color-text-primary)]">$1</h3>')
    .replace(/^\- (.+)$/gm, '<li class="ml-4 list-disc text-[var(--color-text-secondary)]">$1</li>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n\n/g, '</p><p class="mb-2 text-[var(--color-text-secondary)]">')
    .replace(/\n/g, '<br/>');
  return `<p class="mb-2 text-[var(--color-text-secondary)]">${html}</p>`;
}

export default function ReportView() {
  const { studentId, activityId } = useParams<{ studentId: string; activityId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const commissionId = searchParams.get('commission') ?? '';

  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!studentId || !activityId || !commissionId) return;

    setLoading(true);
    setError(null);

    apiClient
      .get<{ data: ReportData | null }>(`/v1/reports?student_id=${studentId}&activity_id=${activityId}`)
      .then((res) => {
        const envelope = res.data as unknown as { data?: ReportData | null };
        const existing = envelope.data ?? null;
        if (existing) {
          setReport(existing);
          setLoading(false);
        } else {
          return generateReport();
        }
      })
      .catch(() => {
        return generateReport();
      });
  }, [studentId, activityId, commissionId]);

  async function generateReport() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.post<{ data: ReportData }>('/v1/reports/generate', {
        student_id: studentId,
        activity_id: activityId,
        commission_id: commissionId,
      });
      const envelope = res.data as unknown as { data?: ReportData };
      setReport(envelope.data ?? (res.data as unknown as ReportData));
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Error al generar el informe';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-10">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--color-accent-600)] border-t-transparent" />
          <p className="text-[var(--color-text-secondary)]">Generando informe cognitivo...</p>
          <p className="text-sm text-[var(--color-text-tertiary)]">Esto puede tardar unos segundos</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-10">
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 dark:border-red-800 dark:bg-red-900/20">
          <h2 className="text-lg font-semibold text-red-700 dark:text-red-400">Error al generar informe</h2>
          <p className="mt-2 text-red-600 dark:text-red-300">{error}</p>
          <button
            onClick={() => navigate(-1)}
            className="mt-4 rounded bg-[var(--color-accent-600)] px-4 py-2 text-white hover:opacity-90"
          >
            Volver
          </button>
        </div>
      </div>
    );
  }

  if (!report) return null;

  const { structured_analysis: analysis } = report;

  return (
    <div className="mx-auto max-w-4xl px-4 py-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <button
            onClick={() => navigate(-1)}
            className="mb-2 text-sm text-[var(--color-accent-600)] hover:underline"
          >
            ← Volver
          </button>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
            Informe Cognitivo
          </h1>
          <p className="text-sm text-[var(--color-text-secondary)]">
            {analysis.student_name} — {analysis.activity_title}
          </p>
        </div>
        <div className="text-right text-xs text-[var(--color-text-tertiary)]">
          <p>{analysis.sessions_analyzed} sesiones analizadas</p>
          <p>Generado: {new Date(report.generated_at).toLocaleDateString('es-AR')}</p>
          <p>{report.llm_provider}/{report.model_used}</p>
        </div>
      </div>

      {/* Score summary */}
      {analysis.overall_scores && (
        <div className="mb-6 grid grid-cols-5 gap-3">
          {Object.entries(analysis.overall_scores).map(([key, val]) => (
            <div
              key={key}
              className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-3 text-center"
            >
              <p className="text-xs uppercase text-[var(--color-text-tertiary)]">
                {key.replace('_avg', '')}
              </p>
              <p className="text-xl font-bold text-[var(--color-text-primary)]">
                {val !== null ? val.toFixed(0) : '—'}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Risk badge */}
      {analysis.risk_level && (
        <div className="mb-4">
          <span
            className={`inline-block rounded-full px-3 py-1 text-xs font-medium ${
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
        </div>
      )}

      {/* Narrative */}
      <div
        className="prose prose-sm max-w-none dark:prose-invert"
        dangerouslySetInnerHTML={{ __html: renderMarkdown(report.narrative_md) }}
      />

      {/* Regenerate button */}
      <div className="mt-8 border-t border-[var(--color-border)] pt-4">
        <button
          onClick={generateReport}
          className="rounded bg-[var(--color-accent-600)] px-4 py-2 text-sm text-white hover:opacity-90"
        >
          Regenerar informe
        </button>
      </div>
    </div>
  );
}
