import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useActivitiesStore } from './store';
import Button from '@/shared/components/Button';
import Card from '@/shared/components/Card';
import type { ExerciseDifficulty } from '@/features/exercises/types';

const DIFFICULTY_COLORS: Record<ExerciseDifficulty, { bg: string; text: string }> = {
  easy: { bg: 'bg-[#EDF3EC]', text: 'text-[#346538]' },
  medium: { bg: 'bg-[#FBF3DB]', text: 'text-[#956400]' },
  hard: { bg: 'bg-[#FDEBEC]', text: 'text-[#9F2F2D]' },
};

export default function ActivityDetailPage() {
  const { activityId } = useParams<{ activityId: string }>();
  const navigate = useNavigate();
  const activity = useActivitiesStore((s) => s.currentActivity);
  const isLoading = useActivitiesStore((s) => s.isLoading);
  const fetchActivity = useActivitiesStore((s) => s.fetchActivity);
  const publishActivity = useActivitiesStore((s) => s.publishActivity);
  const deleteActivity = useActivitiesStore((s) => s.deleteActivity);

  const [publishing, setPublishing] = useState(false);

  useEffect(() => {
    if (activityId) fetchActivity(activityId);
  }, [activityId, fetchActivity]);

  async function handlePublish() {
    if (!activityId) return;
    setPublishing(true);
    try {
      await publishActivity(activityId);
      await fetchActivity(activityId);
    } finally {
      setPublishing(false);
    }
  }

  async function handleDelete() {
    if (!activityId) return;
    const courseId = activity?.course_id;
    await deleteActivity(activityId);
    navigate(courseId ? `/courses/${courseId}` : '/courses');
  }

  if (isLoading || !activity) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 w-64 rounded bg-[var(--color-neutral-100)]" />
        <div className="h-4 w-96 rounded bg-[var(--color-neutral-100)]" />
        <div className="h-48 w-full rounded-[12px] bg-[var(--color-neutral-100)]" />
      </div>
    );
  }

  const isDraft = activity.status === 'draft';

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[1.75rem] font-bold tracking-tight text-[var(--color-text-primary)]">
              {activity.title}
            </h1>
            <span
              className={`rounded-full px-2.5 py-0.5 text-[0.6875rem] font-semibold uppercase tracking-wider ${
                isDraft
                  ? 'bg-[#FBF3DB] text-[#956400]'
                  : 'bg-[#EDF3EC] text-[#346538]'
              }`}
            >
              {activity.status}
            </span>
          </div>
          {activity.description && (
            <p className="mt-2 text-[0.9375rem] text-[var(--color-text-secondary)]">
              {activity.description}
            </p>
          )}
          {activity.prompt_used && (
            <p className="mt-2 text-[0.8125rem] italic text-[var(--color-text-tertiary)]">
              Prompt: "{activity.prompt_used}"
            </p>
          )}
        </div>
        <div className="flex gap-2 shrink-0">
          {isDraft && (
            <Button
              variant="primary"
              size="md"
              onClick={handlePublish}
              loading={publishing}
            >
              Publicar
            </Button>
          )}
          <Button variant="ghost" size="md" onClick={handleDelete}>
            Eliminar
          </Button>
        </div>
      </div>

      {/* Exercises */}
      <div className="mt-8">
        <h2 className="text-[0.8125rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
          Ejercicios ({activity.exercises?.length ?? 0})
        </h2>

        <div className="mt-4 space-y-4">
          {activity.exercises?.map((ex, i) => {
            const colors = DIFFICULTY_COLORS[(ex.difficulty as ExerciseDifficulty)] || DIFFICULTY_COLORS.medium;
            return (
              <Card
                key={ex.id}
                padding="md"
                className="animate-[slideIn_400ms_cubic-bezier(0.32,0.72,0,1)_both]"
                style={{ animationDelay: `${i * 60}ms` } as React.CSSProperties}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-[0.75rem] font-mono text-[var(--color-text-tertiary)]">
                        {i + 1}.
                      </span>
                      <p className="text-[0.9375rem] font-semibold text-[var(--color-text-primary)]">
                        {ex.title}
                      </p>
                      <span className={`shrink-0 rounded-full px-2 py-0.5 text-[0.625rem] font-semibold uppercase tracking-wider ${colors.bg} ${colors.text}`}>
                        {ex.difficulty}
                      </span>
                    </div>
                    <p className="mt-2 text-[0.8125rem] leading-relaxed text-[var(--color-text-secondary)] whitespace-pre-wrap">
                      {ex.description}
                    </p>
                    {ex.topic_tags && ex.topic_tags.length > 0 && (
                      <div className="mt-2 flex gap-1.5">
                        {ex.topic_tags.map((tag: string) => (
                          <span
                            key={tag}
                            className="rounded-full bg-[var(--color-neutral-100)] px-2 py-0.5 text-[0.6875rem] text-[var(--color-text-tertiary)] dark:bg-[var(--color-neutral-800)]"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                    {ex.starter_code && (
                      <pre className="mt-3 overflow-x-auto rounded-[6px] border border-[var(--color-border)] bg-[var(--color-neutral-950)] px-4 py-3 font-mono text-[0.75rem] leading-relaxed text-[var(--color-neutral-300)]">
                        <code>{ex.starter_code}</code>
                      </pre>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}
