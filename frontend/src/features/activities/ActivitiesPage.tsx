import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useActivitiesStore } from './store';
import Button from '@/shared/components/Button';

export default function ActivitiesPage() {
  const activities = useActivitiesStore((s) => s.activities);
  const isLoading = useActivitiesStore((s) => s.isLoading);
  const fetchActivities = useActivitiesStore((s) => s.fetchActivities);

  useEffect(() => {
    fetchActivities();
  }, [fetchActivities]);

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <span className="inline-block rounded-full bg-[var(--color-neutral-100)] px-3 py-1 text-[0.625rem] font-semibold uppercase tracking-[0.15em] text-[var(--color-text-secondary)] dark:bg-[var(--color-neutral-800)]">
            IA
          </span>
          <h1 className="mt-3 text-[1.75rem] font-bold tracking-tight text-[var(--color-text-primary)]">
            Actividades
          </h1>
        </div>
        <Link to="/activities/new">
          <Button
            variant="primary"
            size="md"
            icon={
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
            }
            iconPosition="left"
          >
            Generar actividad
          </Button>
        </Link>
      </div>

      <div className="mt-8">
        {isLoading && activities.length === 0 ? (
          <div className="space-y-0">
            {[0, 1, 2].map((i) => (
              <div key={i} className="flex items-center justify-between border-b border-[var(--color-border)] py-5">
                <div className="space-y-2">
                  <div className="h-4 w-56 animate-pulse rounded bg-[var(--color-neutral-100)]" />
                  <div className="h-3 w-32 animate-pulse rounded bg-[var(--color-neutral-50)]" />
                </div>
              </div>
            ))}
          </div>
        ) : activities.length === 0 ? (
          <div className="py-16 text-center">
            <p className="text-[1.0625rem] font-medium text-[var(--color-text-primary)]">
              Sin actividades
            </p>
            <p className="mt-1.5 text-[0.875rem] text-[var(--color-text-tertiary)]">
              Genera tu primera actividad con inteligencia artificial.
            </p>
            <Link to="/activities/new">
              <Button variant="secondary" size="sm" className="mt-5">
                Generar primera actividad
              </Button>
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-[var(--color-border)]">
            {activities.map((a, i) => (
              <Link
                key={a.id}
                to={`/activities/${a.id}`}
                className="group flex items-center justify-between py-4 animate-[slideIn_400ms_cubic-bezier(0.32,0.72,0,1)_both]"
                style={{ animationDelay: `${i * 50}ms` }}
              >
                <div>
                  <p className="text-[0.9375rem] font-semibold text-[var(--color-text-primary)] transition-colors duration-300 group-hover:text-[var(--color-accent-600)]">
                    {a.title}
                  </p>
                  {a.prompt_used && (
                    <p className="mt-0.5 text-[0.8125rem] text-[var(--color-text-tertiary)] truncate max-w-[400px]">
                      {a.prompt_used}
                    </p>
                  )}
                </div>
                <span
                  className={`shrink-0 rounded-full px-2.5 py-0.5 text-[0.6875rem] font-semibold uppercase tracking-wider ${
                    a.status === 'draft'
                      ? 'bg-[#FBF3DB] text-[#956400]'
                      : 'bg-[#EDF3EC] text-[#346538]'
                  }`}
                >
                  {a.status}
                </span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
