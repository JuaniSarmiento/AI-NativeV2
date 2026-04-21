import { useEffect, useRef, useState } from 'react';
import { apiClient } from '@/shared/lib/api-client';

// ─── Types ────────────────────────────────────────────────────────────────────

interface EvolutionItem {
  session_id: string;
  exercise_id: string;
  exercise_title: string | null;
  started_at: string;
  n1: number | null;
  n2: number | null;
  n3: number | null;
  n4: number | null;
  qe: number | null;
  risk_level: string | null;
}

interface EvolutionResponse {
  student_id: string;
  commission_id: string;
  items: EvolutionItem[];
}

interface Props {
  studentId: string;
  commissionId: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const LINES = [
  { key: 'n1' as const, label: 'N1 Comprension', color: 'var(--color-info-500, #3b82f6)' },
  { key: 'n2' as const, label: 'N2 Estrategia', color: 'var(--color-success-500, #22c55e)' },
  { key: 'n3' as const, label: 'N3 Validacion', color: 'var(--color-warning-500, #f59e0b)' },
  { key: 'n4' as const, label: 'N4 Interaccion IA', color: 'var(--color-accent-500, #8b5cf6)' },
] as const;

const CHART_H = 220;
const CHART_PADDING = { top: 16, right: 24, bottom: 40, left: 36 };

// ─── Helpers ─────────────────────────────────────────────────────────────────

function toX(index: number, total: number, w: number): number {
  if (total <= 1) return w / 2;
  return CHART_PADDING.left + (index / (total - 1)) * (w - CHART_PADDING.left - CHART_PADDING.right);
}

function toY(value: number): number {
  const h = CHART_H - CHART_PADDING.top - CHART_PADDING.bottom;
  return CHART_PADDING.top + h - (value / 100) * h;
}

function buildPath(
  items: EvolutionItem[],
  key: 'n1' | 'n2' | 'n3' | 'n4',
  w: number,
): string {
  const pts = items
    .map((item, i) => {
      const v = item[key];
      if (v === null) return null;
      return `${toX(i, items.length, w)},${toY(v)}`;
    })
    .filter(Boolean);

  if (pts.length === 0) return '';
  return 'M ' + pts.join(' L ');
}

function formatLabel(item: EvolutionItem): string {
  const title = item.exercise_title;
  if (title) return title.length > 14 ? title.slice(0, 12) + '…' : title;
  return new Date(item.started_at).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit' });
}

// ─── Tooltip ─────────────────────────────────────────────────────────────────

interface TooltipState {
  x: number;
  y: number;
  item: EvolutionItem;
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function EvolutionChart({ studentId, commissionId }: Props) {
  const [data, setData] = useState<EvolutionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(560);

  // Responsive width
  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w && w > 0) setWidth(w);
    });
    ro.observe(containerRef.current);
    setWidth(containerRef.current.clientWidth || 560);
    return () => ro.disconnect();
  }, []);

  // Fetch
  useEffect(() => {
    if (!studentId || !commissionId) return;
    setLoading(true);
    setError(null);
    apiClient
      .get<{ data: EvolutionResponse }>(
        `/v1/cognitive/students/${studentId}/evolution?commission_id=${commissionId}`,
      )
      .then((res) => {
        const payload = res.data as unknown as { data?: EvolutionResponse };
        const body = payload.data ?? (res.data as unknown as EvolutionResponse);
        setData(Array.isArray(body?.items) ? body.items : []);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [studentId, commissionId]);

  if (loading) {
    return (
      <div className="flex min-h-[180px] items-center justify-center rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--color-accent-500)] border-t-transparent" />
        <span className="ml-3 text-xs text-[var(--color-text-secondary)]">Cargando evolucion...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
        <p className="text-xs text-[var(--color-error-600,#dc2626)]">{error}</p>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] p-6 text-center">
        <p className="text-sm text-[var(--color-text-tertiary)]">Sin sesiones registradas para graficar.</p>
      </div>
    );
  }

  const plotW = width;
  const plotH = CHART_H;
  const yTicks = [0, 25, 50, 75, 100];

  return (
    <div
      className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4"
      ref={containerRef}
    >
      <h3 className="mb-3 text-[0.8125rem] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
        Evolucion N1–N4
      </h3>

      <div className="relative">
        <svg
          viewBox={`0 0 ${plotW} ${plotH}`}
          width="100%"
          height={plotH}
          role="img"
          aria-label="Grafico de evolucion de niveles cognitivos N1 a N4"
          onMouseLeave={() => setTooltip(null)}
        >
          {/* Y-axis grid lines + labels */}
          {yTicks.map((tick) => {
            const y = toY(tick);
            return (
              <g key={tick}>
                <line
                  x1={CHART_PADDING.left}
                  y1={y}
                  x2={plotW - CHART_PADDING.right}
                  y2={y}
                  stroke="var(--color-border)"
                  strokeWidth={0.5}
                  strokeDasharray={tick === 0 ? '0' : '3 3'}
                />
                <text
                  x={CHART_PADDING.left - 6}
                  y={y + 4}
                  textAnchor="end"
                  fontSize={9}
                  fill="var(--color-text-tertiary)"
                  fontFamily="var(--font-mono)"
                >
                  {tick}
                </text>
              </g>
            );
          })}

          {/* X-axis labels */}
          {data.map((item, i) => {
            const x = toX(i, data.length, plotW);
            const y = plotH - CHART_PADDING.bottom + 14;
            return (
              <text
                key={item.session_id}
                x={x}
                y={y}
                textAnchor="middle"
                fontSize={9}
                fill="var(--color-text-tertiary)"
                fontFamily="var(--font-sans)"
              >
                {formatLabel(item)}
              </text>
            );
          })}

          {/* Lines */}
          {LINES.map(({ key, color }) => {
            const d = buildPath(data, key, plotW);
            if (!d) return null;
            return (
              <path
                key={key}
                d={d}
                fill="none"
                stroke={color}
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            );
          })}

          {/* Dots — interactive */}
          {LINES.map(({ key, color }) =>
            data.map((item, i) => {
              const v = item[key];
              if (v === null) return null;
              const cx = toX(i, data.length, plotW);
              const cy = toY(v);
              return (
                <circle
                  key={`${key}-${item.session_id}`}
                  cx={cx}
                  cy={cy}
                  r={4}
                  fill={color}
                  stroke="var(--color-surface)"
                  strokeWidth={1.5}
                  style={{ cursor: 'crosshair' }}
                  onMouseEnter={() => setTooltip({ x: cx, y: cy, item })}
                />
              );
            }),
          )}

          {/* Tooltip */}
          {tooltip && (() => {
            const { x, y, item } = tooltip;
            const boxW = 150;
            const boxH = 86;
            const pad = 8;
            const bx = Math.min(x + 10, plotW - boxW - pad);
            const by = Math.max(y - boxH - 8, CHART_PADDING.top);
            return (
              <g>
                <rect
                  x={bx}
                  y={by}
                  width={boxW}
                  height={boxH}
                  rx={6}
                  fill="var(--color-surface-elevated, #fff)"
                  stroke="var(--color-border)"
                  strokeWidth={1}
                  style={{ filter: 'drop-shadow(0 2px 6px rgba(0,0,0,0.12))' }}
                />
                <text x={bx + 8} y={by + 14} fontSize={9} fill="var(--color-text-tertiary)" fontFamily="var(--font-sans)">
                  {formatLabel(item)}
                </text>
                {LINES.map(({ key, label, color }, idx) => {
                  const v = item[key];
                  return (
                    <g key={key}>
                      <circle cx={bx + 12} cy={by + 26 + idx * 14} r={3} fill={color} />
                      <text x={bx + 20} y={by + 30 + idx * 14} fontSize={9} fill="var(--color-text-secondary)" fontFamily="var(--font-sans)">
                        {label}: <tspan fontWeight="600" fill="var(--color-text-primary)">{v != null ? v.toFixed(0) : '–'}</tspan>
                      </text>
                    </g>
                  );
                })}
              </g>
            );
          })()}
        </svg>
      </div>

      {/* Legend */}
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5">
        {LINES.map(({ key, label, color }) => (
          <div key={key} className="flex items-center gap-1.5">
            <span
              className="inline-block h-2 w-5 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span className="text-[0.6875rem] text-[var(--color-text-secondary)]">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
