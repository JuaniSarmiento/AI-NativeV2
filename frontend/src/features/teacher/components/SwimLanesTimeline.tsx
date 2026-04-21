import { useRef, useState, useEffect } from 'react';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface TimelineEvent {
  event_type: string;
  n4_level: number | null;
  created_at: string;
  payload: Record<string, unknown>;
}

interface Props {
  events: TimelineEvent[];
  sessionStart: string;
  sessionEnd: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const LANES = [
  { level: 1, label: 'N1', subLabel: 'Comprension', color: 'var(--color-info-500, #3b82f6)', bgClass: 'bg-blue-50 dark:bg-blue-950/20' },
  { level: 2, label: 'N2', subLabel: 'Estrategia', color: 'var(--color-success-500, #22c55e)', bgClass: 'bg-emerald-50 dark:bg-emerald-950/20' },
  { level: 3, label: 'N3', subLabel: 'Validacion', color: 'var(--color-warning-500, #f59e0b)', bgClass: 'bg-amber-50 dark:bg-amber-950/20' },
  { level: 4, label: 'N4', subLabel: 'Interaccion IA', color: 'var(--color-accent-500, #8b5cf6)', bgClass: 'bg-violet-50 dark:bg-violet-950/20' },
];

const LANE_H = 44;
const LABEL_W = 88;
const DOT_R = 6;
const AXIS_H = 24;
const SVG_TOP_PAD = 8;

const EVENT_TYPE_LABELS: Record<string, string> = {
  reads_problem: 'Lectura del problema',
  'code.snapshot': 'Snapshot de codigo',
  'code.run': 'Ejecucion de codigo',
  'submission.created': 'Entrega',
  'tutor.question_asked': 'Pregunta al tutor',
  'tutor.response_received': 'Respuesta tutor',
  'session.started': 'Sesion iniciada',
  'session.closed': 'Sesion cerrada',
  'reflection.submitted': 'Reflexion',
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function toTimestamp(iso: string): number {
  return new Date(iso).getTime();
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('es-AR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

// ─── Tooltip ─────────────────────────────────────────────────────────────────

interface TooltipState {
  x: number;
  y: number;
  event: TimelineEvent;
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function SwimLanesTimeline({ events, sessionStart, sessionEnd }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(560);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  // Responsive
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

  const tStart = toTimestamp(sessionStart);
  const tEnd = toTimestamp(sessionEnd || new Date().toISOString());
  const tRange = Math.max(tEnd - tStart, 1);

  const plotW = width - LABEL_W;
  const totalH = SVG_TOP_PAD + LANES.length * LANE_H + AXIS_H;

  function toX(iso: string): number {
    const t = toTimestamp(iso);
    return LABEL_W + ((t - tStart) / tRange) * plotW;
  }

  function laneY(level: number): number {
    return SVG_TOP_PAD + (level - 1) * LANE_H;
  }

  // Time axis ticks — 4 evenly spaced
  const timeTicks = [0, 0.25, 0.5, 0.75, 1].map((frac) => ({
    x: LABEL_W + frac * plotW,
    label: formatTime(new Date(tStart + frac * tRange).toISOString()),
  }));

  const unclassifiedEvents = events.filter((e) => !e.n4_level);

  if (events.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-[var(--color-border)] p-6 text-center">
        <p className="text-xs text-[var(--color-text-tertiary)]">Sin eventos en esta sesion.</p>
      </div>
    );
  }

  return (
    <div
      className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4"
      ref={containerRef}
    >
      <h3 className="mb-3 text-[0.8125rem] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
        Swim Lanes — Proceso Cognitivo
      </h3>

      <div
        className="relative"
        onMouseLeave={() => setTooltip(null)}
      >
        <svg
          viewBox={`0 0 ${width} ${totalH}`}
          width="100%"
          height={totalH}
          role="img"
          aria-label="Timeline de eventos cognitivos por nivel N"
        >
          {/* Lane backgrounds */}
          {LANES.map(({ level, label, subLabel, color, bgClass }) => {
            const y = laneY(level);
            return (
              <g key={level}>
                {/* Lane background — alternating subtle */}
                <rect
                  x={0}
                  y={SVG_TOP_PAD + (level - 1) * LANE_H}
                  width={width}
                  height={LANE_H}
                  className={bgClass}
                  opacity={0.4}
                />
                {/* Lane divider */}
                <line
                  x1={0}
                  y1={y}
                  x2={width}
                  y2={y}
                  stroke="var(--color-border)"
                  strokeWidth={0.5}
                />
                {/* Label block */}
                <rect x={0} y={y} width={LABEL_W - 4} height={LANE_H} fill="var(--color-surface)" />
                <text
                  x={10}
                  y={y + LANE_H / 2 - 5}
                  fontSize={11}
                  fontWeight="700"
                  fill={color}
                  fontFamily="var(--font-mono)"
                >
                  {label}
                </text>
                <text
                  x={10}
                  y={y + LANE_H / 2 + 8}
                  fontSize={8.5}
                  fill="var(--color-text-tertiary)"
                  fontFamily="var(--font-sans)"
                >
                  {subLabel}
                </text>
              </g>
            );
          })}

          {/* Bottom lane border */}
          <line
            x1={0}
            y1={SVG_TOP_PAD + LANES.length * LANE_H}
            x2={width}
            y2={SVG_TOP_PAD + LANES.length * LANE_H}
            stroke="var(--color-border)"
            strokeWidth={0.5}
          />

          {/* Time axis */}
          {timeTicks.map(({ x, label }, i) => (
            <g key={i}>
              <line
                x1={x}
                y1={SVG_TOP_PAD}
                x2={x}
                y2={SVG_TOP_PAD + LANES.length * LANE_H}
                stroke="var(--color-border)"
                strokeWidth={0.5}
                strokeDasharray="2 4"
              />
              <text
                x={x}
                y={totalH - 4}
                textAnchor="middle"
                fontSize={8}
                fill="var(--color-text-tertiary)"
                fontFamily="var(--font-mono)"
              >
                {label}
              </text>
            </g>
          ))}

          {/* Unclassified events — small grey ticks at bottom */}
          {unclassifiedEvents.map((evt, i) => {
            const x = toX(evt.created_at);
            const y = SVG_TOP_PAD + LANES.length * LANE_H;
            return (
              <line
                key={`unc-${i}`}
                x1={x}
                y1={y}
                x2={x}
                y2={y + 6}
                stroke="var(--color-text-tertiary)"
                strokeWidth={1}
              />
            );
          })}

          {/* Classified events — dots in lane */}
          {LANES.map(({ level, color }) => {
            const laneEvents = events.filter((e) => e.n4_level === level);
            const centerY = laneY(level) + LANE_H / 2;
            return laneEvents.map((evt, i) => {
              const x = toX(evt.created_at);
              return (
                <circle
                  key={`${level}-${i}`}
                  cx={x}
                  cy={centerY}
                  r={DOT_R}
                  fill={color}
                  opacity={0.85}
                  stroke="var(--color-surface)"
                  strokeWidth={1.5}
                  style={{ cursor: 'pointer' }}
                  onMouseEnter={() => setTooltip({ x, y: centerY, event: evt })}
                />
              );
            });
          })}

          {/* Tooltip */}
          {tooltip && (() => {
            const { x, y, event } = tooltip;
            const boxW = 180;
            const boxH = 52;
            const bx = Math.min(x + 10, width - boxW - 4);
            const by = Math.max(y - boxH - 8, 4);
            const label = EVENT_TYPE_LABELS[event.event_type] ?? event.event_type;
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
                  style={{ filter: 'drop-shadow(0 2px 6px rgba(0,0,0,0.1))' }}
                />
                <text x={bx + 8} y={by + 16} fontSize={10} fontWeight="600" fill="var(--color-text-primary)" fontFamily="var(--font-sans)">
                  {label}
                </text>
                <text x={bx + 8} y={by + 32} fontSize={9} fill="var(--color-text-tertiary)" fontFamily="var(--font-mono)">
                  {formatTime(event.created_at)}
                </text>
                {event.n4_level && (
                  <text x={bx + 8} y={by + 46} fontSize={9} fill="var(--color-text-secondary)" fontFamily="var(--font-sans)">
                    Nivel N{event.n4_level}
                  </text>
                )}
              </g>
            );
          })()}
        </svg>
      </div>

      {/* Unclassified count hint */}
      {unclassifiedEvents.length > 0 && (
        <p className="mt-2 text-[0.625rem] text-[var(--color-text-tertiary)]">
          + {unclassifiedEvents.length} evento{unclassifiedEvents.length > 1 ? 's' : ''} sin clasificar (marcados en eje)
        </p>
      )}
    </div>
  );
}
