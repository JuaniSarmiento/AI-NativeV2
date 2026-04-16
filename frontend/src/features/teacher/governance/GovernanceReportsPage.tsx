import { useEffect, useState } from 'react';
import { useGovernanceStore } from './store';
import GovernanceEventsTable from './GovernanceEventsTable';
import PromptHistoryTable from './PromptHistoryTable';

type Tab = 'events' | 'prompts';

export default function GovernanceReportsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('events');
  const [eventTypeFilter, setEventTypeFilter] = useState('');
  const fetchEvents = useGovernanceStore((s) => s.fetchEvents);
  const fetchPrompts = useGovernanceStore((s) => s.fetchPrompts);

  useEffect(() => {
    fetchEvents(1, eventTypeFilter || undefined);
  }, [fetchEvents, eventTypeFilter]);

  useEffect(() => {
    if (activeTab === 'prompts') {
      fetchPrompts();
    }
  }, [activeTab, fetchPrompts]);

  const handleFilterChange = (value: string) => {
    setEventTypeFilter(value);
  };

  return (
    <div className="space-y-6">
      <div>
        <span className="inline-block rounded-full bg-[var(--color-accent-50)] px-3 py-1 text-[0.6875rem] font-semibold uppercase tracking-[0.15em] text-[var(--color-accent-700)] dark:bg-[var(--color-accent-900)]/20 dark:text-[var(--color-accent-400)]">
          Governance
        </span>
        <h1 className="mt-3 text-[1.75rem] font-bold tracking-tight text-[var(--color-text-primary)]">
          Reportes de Gobernanza
        </h1>
        <p className="mt-1 text-[0.875rem] text-[var(--color-text-secondary)]">
          Eventos de auditoria, historial de prompts y alertas de integridad.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-neutral-50)] p-1 dark:bg-[var(--color-neutral-900)]">
        {(['events', 'prompts'] as Tab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 rounded-[var(--radius-md)] px-4 py-2 text-[0.8125rem] font-medium transition-all duration-300 ${
              activeTab === tab
                ? 'bg-[var(--color-surface)] text-[var(--color-text-primary)] shadow-sm'
                : 'text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]'
            }`}
          >
            {tab === 'events' ? 'Eventos' : 'Prompts'}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'events' && (
        <GovernanceEventsTable eventTypeFilter={eventTypeFilter} onFilterChange={handleFilterChange} />
      )}
      {activeTab === 'prompts' && <PromptHistoryTable />}
    </div>
  );
}
