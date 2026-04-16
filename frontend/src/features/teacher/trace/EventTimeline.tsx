import { useTraceStore } from './store';
import { N4_LEVEL_COLORS, N4_LEVEL_LABELS, EVENT_TYPE_LABELS } from './types';
import type { TraceEvent } from './types';

const EMPTY_EVENTS: TraceEvent[] = [];

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('es-AR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function getEventSummary(event: TraceEvent): string {
  const payload = event.payload;
  if (event.event_type === 'tutor.question_asked' && typeof payload.content === 'string') {
    return payload.content.length > 80 ? payload.content.slice(0, 80) + '...' : payload.content;
  }
  if (event.event_type === 'code.run') {
    return payload.status === 'error' ? 'Error en ejecucion' : 'Ejecucion exitosa';
  }
  return '';
}

export default function EventTimeline() {
  const events = useTraceStore((s) => s.events);
  const items = events.length > 0 ? events : EMPTY_EVENTS;

  if (items.length === 0) {
    return (
      <div className="rounded-[var(--radius-lg)] border border-dashed border-[var(--color-border)] p-8 text-center">
        <p className="text-[0.875rem] text-[var(--color-text-tertiary)]">Sin eventos registrados.</p>
      </div>
    );
  }

  return (
    <div className="relative space-y-0">
      {/* Vertical line */}
      <div className="absolute left-4 top-0 h-full w-px bg-[var(--color-border)]" />

      {items.map((event) => {
        const color = event.n4_level ? N4_LEVEL_COLORS[event.n4_level] ?? 'var(--color-neutral-400)' : 'var(--color-neutral-400)';
        const label = EVENT_TYPE_LABELS[event.event_type] ?? event.event_type;
        const n4Label = event.n4_level ? N4_LEVEL_LABELS[event.n4_level] : null;
        const summary = getEventSummary(event);

        return (
          <div key={event.id} className="relative flex items-start gap-4 py-3 pl-10">
            {/* Dot */}
            <div
              className="absolute left-2.5 top-4 h-3 w-3 rounded-full border-2 border-[var(--color-surface)]"
              style={{ backgroundColor: color }}
            />

            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-[0.8125rem] font-medium text-[var(--color-text-primary)]">
                  {label}
                </span>
                {n4Label && (
                  <span
                    className="rounded-full px-2 py-0.5 text-[0.625rem] font-semibold uppercase tracking-[0.08em] text-white"
                    style={{ backgroundColor: color }}
                  >
                    {n4Label}
                  </span>
                )}
              </div>
              {summary && (
                <p className="mt-0.5 text-[0.75rem] text-[var(--color-text-secondary)]">
                  {summary}
                </p>
              )}
              <p className="mt-0.5 font-mono text-[0.6875rem] tabular-nums text-[var(--color-text-tertiary)]">
                {formatTime(event.created_at)} — seq #{event.sequence_number}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
