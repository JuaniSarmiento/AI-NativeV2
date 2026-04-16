import { useGovernanceStore } from './store';
import type { PromptHistory } from './types';

const EMPTY_PROMPTS: PromptHistory[] = [];

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function PromptHistoryTable() {
  const prompts = useGovernanceStore((s) => s.prompts);
  const isLoading = useGovernanceStore((s) => s.isLoadingPrompts);
  const items = prompts.length > 0 ? prompts : EMPTY_PROMPTS;

  if (isLoading) {
    return <p className="text-[0.875rem] text-[var(--color-text-tertiary)]">Cargando prompts...</p>;
  }

  if (items.length === 0) {
    return (
      <div className="rounded-[var(--radius-lg)] border border-dashed border-[var(--color-border)] p-8 text-center">
        <p className="text-[0.875rem] text-[var(--color-text-tertiary)]">Sin prompts registrados.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)]">
      <table className="w-full text-left text-[0.8125rem]">
        <thead>
          <tr className="border-b border-[var(--color-border)]">
            <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">Nombre</th>
            <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">Version</th>
            <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">SHA-256</th>
            <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">Estado</th>
            <th className="px-4 py-3 font-semibold text-[var(--color-text-secondary)]">Creado</th>
          </tr>
        </thead>
        <tbody>
          {items.map((p) => (
            <tr
              key={p.id}
              className={`border-b border-[var(--color-border)]/50 ${
                p.is_active ? 'bg-[var(--color-success-50)]/30 dark:bg-[var(--color-success-900)]/10' : ''
              }`}
            >
              <td className="px-4 py-3 font-medium text-[var(--color-text-primary)]">{p.name}</td>
              <td className="px-4 py-3 text-[var(--color-text-secondary)]">{p.version}</td>
              <td className="px-4 py-3 font-mono text-[0.6875rem] text-[var(--color-text-tertiary)]">
                {p.sha256_hash.slice(0, 16)}...
              </td>
              <td className="px-4 py-3">
                {p.is_active ? (
                  <span className="inline-block rounded-full bg-[var(--color-success-50)] px-2.5 py-0.5 text-[0.6875rem] font-semibold uppercase tracking-[0.08em] text-[var(--color-success-700)] dark:bg-[var(--color-success-900)]/20 dark:text-[var(--color-success-400)]">
                    Activo
                  </span>
                ) : (
                  <span className="text-[0.75rem] text-[var(--color-text-tertiary)]">Inactivo</span>
                )}
              </td>
              <td className="whitespace-nowrap px-4 py-3 font-mono text-[0.6875rem] tabular-nums text-[var(--color-text-tertiary)]">
                {formatDate(p.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
