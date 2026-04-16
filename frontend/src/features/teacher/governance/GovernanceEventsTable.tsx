import { useGovernanceStore } from './store';
import type { GovernanceEvent } from './types';

const EMPTY_EVENTS: GovernanceEvent[] = [];

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function summarizeDetails(details: Record<string, unknown>): string {
  const entries = Object.entries(details).slice(0, 3);
  return entries.map(([k, v]) => `${k}: ${String(v).slice(0, 40)}`).join(', ');
}

interface GovernanceEventsTableProps {
  eventTypeFilter: string;
  onFilterChange: (value: string) => void;
}

export default function GovernanceEventsTable({ eventTypeFilter, onFilterChange }: GovernanceEventsTableProps) {
  const events = useGovernanceStore((s) => s.events);
  const isLoading = useGovernanceStore((s) => s.isLoadingEvents);
  const items = events.length > 0 ? events : EMPTY_EVENTS;

  if (isLoading) {
    return <p className="text-[0.875rem] text-[var(--color-text-tertiary)]">Cargando eventos...</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <label className="text-[0.6875rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
          Filtrar tipo
        </label>
        <select
          value={eventTypeFilter}
          onChange={(e) => onFilterChange(e.target.value)}
          className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-[0.8125rem] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent-500)]"
        >
          <option value="">Todos</option>
          <option value="guardrail.triggered">Guardrail violations</option>
          <option value="prompt.activated">Prompt activado</option>
          <option value="prompt.created">Prompt creado</option>
        </select>
      </div>

      {items.length === 0 ? (
        <div className="rounded-[var(--radius-lg)] border border-dashed border-[var(--color-border)] p-8 text-center">
          <p className="text-[0.875rem] text-[var(--color-text-tertiary)]">Sin eventos de governance.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)]">
          <table className="w-full text-left text-[0.8125rem]">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">Tipo</th>
                <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">Actor</th>
                <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">Target</th>
                <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">Detalles</th>
                <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">Fecha</th>
              </tr>
            </thead>
            <tbody>
              {items.map((ev) => (
                <tr key={ev.id} className="border-b border-[var(--color-border)]/50">
                  <td className="px-4 py-3">
                    <span className="rounded-full bg-[var(--color-neutral-100)] px-2 py-0.5 text-[0.6875rem] font-medium text-[var(--color-text-secondary)] dark:bg-[var(--color-neutral-800)]">
                      {ev.event_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-[0.75rem] text-[var(--color-text-tertiary)]">
                    {ev.actor_id.slice(0, 8)}
                  </td>
                  <td className="px-4 py-3 text-[0.75rem] text-[var(--color-text-tertiary)]">
                    {ev.target_type ?? '-'}
                  </td>
                  <td className="max-w-[250px] truncate px-4 py-3 text-[0.75rem] text-[var(--color-text-secondary)]">
                    {summarizeDetails(ev.details)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-[0.6875rem] tabular-nums text-[var(--color-text-tertiary)]">
                    {formatDate(ev.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
