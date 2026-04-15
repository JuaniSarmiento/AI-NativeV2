import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useExercisesStore } from './store';
import Button from '@/shared/components/Button';
import Card from '@/shared/components/Card';
import TutorChat from '@/features/tutor/components/TutorChat';
import type { ExerciseDifficulty } from './types';

const DIFFICULTY_COLORS: Record<ExerciseDifficulty, { bg: string; text: string }> = {
  easy: { bg: 'bg-[#EDF3EC]', text: 'text-[#346538]' },
  medium: { bg: 'bg-[#FBF3DB]', text: 'text-[#956400]' },
  hard: { bg: 'bg-[#FDEBEC]', text: 'text-[#9F2F2D]' },
};

export default function ExerciseDetailPage() {
  const { exerciseId } = useParams<{ exerciseId: string }>();
  const exercise = useExercisesStore((s) => s.currentExercise);
  const isLoading = useExercisesStore((s) => s.isLoading);
  const fetchExercise = useExercisesStore((s) => s.fetchExercise);
  const [chatOpen, setChatOpen] = useState(false);

  useEffect(() => {
    if (exerciseId) fetchExercise(exerciseId);
  }, [exerciseId, fetchExercise]);

  if (isLoading || !exercise) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-4 w-32 rounded bg-[var(--color-neutral-100)]" />
        <div className="h-8 w-96 rounded bg-[var(--color-neutral-100)]" />
        <div className="h-48 w-full rounded-[12px] bg-[var(--color-neutral-100)]" />
      </div>
    );
  }

  const colors = DIFFICULTY_COLORS[exercise.difficulty];

  return (
    <div className="flex gap-6">
      {/* Main content */}
      <div className="min-w-0 flex-1">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-[0.8125rem] text-[var(--color-text-tertiary)]">
        <Link
          to="/exercises"
          className="transition-colors duration-300 hover:text-[var(--color-text-primary)]"
        >
          Ejercicios
        </Link>
        <span>/</span>
        <span className="text-[var(--color-text-primary)]">{exercise.title}</span>
      </div>

      {/* Header */}
      <div className="mt-6 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[1.75rem] font-bold tracking-tight text-[var(--color-text-primary)]">
              {exercise.title}
            </h1>
            <span
              className={`rounded-full px-2.5 py-0.5 text-[0.6875rem] font-semibold uppercase tracking-wider ${colors.bg} ${colors.text}`}
            >
              {exercise.difficulty}
            </span>
          </div>
          {exercise.topic_tags.length > 0 && (
            <div className="mt-2 flex items-center gap-2">
              {exercise.topic_tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-[var(--color-neutral-100)] px-2 py-0.5 text-[0.6875rem] font-medium text-[var(--color-text-secondary)] dark:bg-[var(--color-neutral-800)]"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center gap-3 text-[0.75rem] text-[var(--color-text-tertiary)]">
          <span>{exercise.time_limit_minutes} min</span>
          <span className="h-1 w-1 rounded-full bg-[var(--color-neutral-300)]" />
          <span>{exercise.max_attempts} intentos</span>
        </div>
      </div>

      {/* Description — Double-Bezel Card */}
      <Card padding="lg" className="mt-8">
        <h2 className="text-[0.8125rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
          Enunciado
        </h2>
        <div className="mt-4 text-[0.9375rem] leading-relaxed text-[var(--color-text-primary)] whitespace-pre-wrap">
          {exercise.description}
        </div>
      </Card>

      {/* Starter code */}
      {exercise.starter_code && (
        <div className="mt-6">
          <h2 className="text-[0.8125rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
            Codigo inicial
          </h2>
          <pre className="mt-3 overflow-x-auto rounded-[8px] border border-[var(--color-border)] bg-[var(--color-neutral-950)] p-5 font-mono text-[0.8125rem] leading-relaxed text-[var(--color-neutral-300)]">
            <code>{exercise.starter_code}</code>
          </pre>
        </div>
      )}

      {/* Test cases (visible ones only) */}
      {exercise.test_cases?.cases?.filter((tc) => !tc.is_hidden).length > 0 && (
        <div className="mt-6">
          <h2 className="text-[0.8125rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
            Casos de prueba
          </h2>
          <div className="mt-3 divide-y divide-[var(--color-border)]">
            {exercise.test_cases.cases
              .filter((tc) => !tc.is_hidden)
              .map((tc) => (
                <div key={tc.id} className="py-3">
                  <p className="text-[0.8125rem] font-medium text-[var(--color-text-primary)]">
                    {tc.description}
                  </p>
                  <div className="mt-2 grid grid-cols-2 gap-3">
                    <div>
                      <span className="text-[0.6875rem] font-medium uppercase tracking-wider text-[var(--color-text-tertiary)]">
                        Entrada
                      </span>
                      <pre className="mt-1 rounded-[6px] bg-[var(--color-neutral-50)] px-3 py-2 font-mono text-[0.8125rem] text-[var(--color-text-primary)] dark:bg-[var(--color-neutral-800)]">
                        {tc.input || '(sin entrada)'}
                      </pre>
                    </div>
                    <div>
                      <span className="text-[0.6875rem] font-medium uppercase tracking-wider text-[var(--color-text-tertiary)]">
                        Salida esperada
                      </span>
                      <pre className="mt-1 rounded-[6px] bg-[var(--color-neutral-50)] px-3 py-2 font-mono text-[0.8125rem] text-[var(--color-text-primary)] dark:bg-[var(--color-neutral-800)]">
                        {tc.expected_output}
                      </pre>
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}
      </div>

      {/* Tutor Chat — right panel on desktop */}
      {exerciseId && (
        <>
          {/* Desktop: fixed side panel */}
          <div className="hidden md:block md:w-[360px] md:shrink-0">
            <div className="sticky top-6 h-[calc(100vh-8rem)]">
              <TutorChat exerciseId={exerciseId} />
            </div>
          </div>

          {/* Mobile: bottom sheet toggle */}
          <div className="fixed bottom-4 right-4 md:hidden z-40">
            <Button
              size="md"
              onClick={() => setChatOpen(!chatOpen)}
              icon={
                <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M2 3h12M2 7h8M2 11h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              }
            >
              Tutor
            </Button>
          </div>

          {/* Mobile: bottom sheet overlay */}
          {chatOpen && (
            <div className="fixed inset-0 z-50 md:hidden">
              <div
                className="absolute inset-0 bg-black/20 backdrop-blur-[2px]"
                onClick={() => setChatOpen(false)}
              />
              <div className="absolute bottom-0 left-0 right-0 h-[70vh] overflow-hidden rounded-t-[16px] bg-[var(--color-surface)]">
                {/* Handle */}
                <div className="flex justify-center py-2">
                  <div className="h-1 w-8 rounded-full bg-[var(--color-neutral-300)]" />
                </div>
                <div className="h-[calc(100%-24px)] px-3 pb-3">
                  <TutorChat exerciseId={exerciseId} />
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
