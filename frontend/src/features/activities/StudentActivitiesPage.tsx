import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '@/shared/lib/api-client';
import Card from '@/shared/components/Card';
import type { Activity } from './types';

interface ActivityWithCount extends Activity {
  exercise_count: number;
}

export default function StudentActivitiesPage() {
  const [activities, setActivities] = useState<ActivityWithCount[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    apiClient
      .get<ActivityWithCount[]>('/v1/student/activities')
      .then((res) => setActivities(Array.isArray(res.data) ? res.data : []))
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div>
      <span className="inline-block rounded-full bg-[var(--color-neutral-100)] px-3 py-1 text-[0.625rem] font-semibold uppercase tracking-[0.15em] text-[var(--color-text-secondary)] dark:bg-[var(--color-neutral-800)]">
        Mis actividades
      </span>
      <h1 className="mt-3 text-[1.75rem] font-bold tracking-tight text-[var(--color-text-primary)]">
        Actividades
      </h1>
      <p className="mt-1.5 text-[0.9375rem] text-[var(--color-text-secondary)]">
        Resolve las actividades de tus cursos. Cada actividad tiene ejercicios que se evaluan al final.
      </p>

      <div className="mt-8">
        {isLoading ? (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="h-24 animate-pulse rounded-[12px] bg-[var(--color-neutral-100)] dark:bg-[var(--color-neutral-800)]"
              />
            ))}
          </div>
        ) : activities.length === 0 ? (
          <Card padding="lg">
            <div className="text-center py-8">
              <p className="text-[1.0625rem] font-medium text-[var(--color-text-primary)]">
                Sin actividades disponibles
              </p>
              <p className="mt-1.5 text-[0.875rem] text-[var(--color-text-tertiary)]">
                Inscribite en un curso para ver las actividades asignadas.
              </p>
            </div>
          </Card>
        ) : (
          <div className="space-y-3">
            {activities.map((a, i) => (
              <Link
                key={a.id}
                to={`/actividades/${a.id}`}
                className="block animate-[slideIn_400ms_cubic-bezier(0.32,0.72,0,1)_both]"
                style={{ animationDelay: `${i * 60}ms` }}
              >
                <Card padding="md" hoverable>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-[0.9375rem] font-semibold text-[var(--color-text-primary)]">
                        {a.title}
                      </p>
                      {a.description && (
                        <p className="mt-1 text-[0.8125rem] text-[var(--color-text-tertiary)] line-clamp-1">
                          {a.description}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-3 shrink-0 ml-4">
                      <span className="text-[0.75rem] font-mono text-[var(--color-text-tertiary)]">
                        {a.exercise_count} ejercicios
                      </span>
                      <svg className="h-4 w-4 text-[var(--color-text-tertiary)]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                      </svg>
                    </div>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
