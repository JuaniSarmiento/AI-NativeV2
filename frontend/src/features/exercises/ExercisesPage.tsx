import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useExercisesStore } from './store';
import { useAuthStore } from '@/features/auth/store';
import type { ExerciseDifficulty } from './types';

const DIFFICULTY_OPTIONS: { value: ExerciseDifficulty | 'all'; label: string }[] = [
  { value: 'all', label: 'Todas' },
  { value: 'easy', label: 'Facil' },
  { value: 'medium', label: 'Medio' },
  { value: 'hard', label: 'Dificil' },
];

const DIFFICULTY_COLORS: Record<ExerciseDifficulty, { bg: string; text: string }> = {
  easy: { bg: 'bg-[#EDF3EC]', text: 'text-[#346538]' },
  medium: { bg: 'bg-[#FBF3DB]', text: 'text-[#956400]' },
  hard: { bg: 'bg-[#FDEBEC]', text: 'text-[#9F2F2D]' },
};

export default function ExercisesPage() {
  const role = useAuthStore((s) => s.user?.role);
  const exercises = useExercisesStore((s) => s.exercises);
  const isLoading = useExercisesStore((s) => s.isLoading);
  const fetchStudentExercises = useExercisesStore((s) => s.fetchStudentExercises);

  const [difficulty, setDifficulty] = useState<ExerciseDifficulty | 'all'>('all');

  useEffect(() => {
    const d = difficulty === 'all' ? undefined : difficulty;
    fetchStudentExercises(1, d);
  }, [fetchStudentExercises, difficulty]);

  return (
    <div>
      {/* Header */}
      <span className="inline-block rounded-full bg-[var(--color-neutral-100)] px-3 py-1 text-[0.625rem] font-semibold uppercase tracking-[0.15em] text-[var(--color-text-secondary)] dark:bg-[var(--color-neutral-800)]">
        {role === 'alumno' ? 'Mis ejercicios' : 'Ejercicios'}
      </span>
      <h1 className="mt-3 text-[1.75rem] font-bold tracking-tight text-[var(--color-text-primary)]">
        Ejercicios
      </h1>

      {/* Filters — inline chips (minimalist-skill pattern) */}
      <div className="mt-6 flex items-center gap-2">
        {DIFFICULTY_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setDifficulty(opt.value)}
            className={[
              'rounded-full px-3 py-1 text-[0.75rem] font-medium',
              'transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]',
              'active:scale-[0.96]',
              difficulty === opt.value
                ? 'bg-[var(--color-neutral-900)] text-white dark:bg-[var(--color-neutral-100)] dark:text-[var(--color-neutral-900)]'
                : 'bg-[var(--color-neutral-100)] text-[var(--color-text-secondary)] hover:bg-[var(--color-neutral-200)] dark:bg-[var(--color-neutral-800)] dark:hover:bg-[var(--color-neutral-700)]',
            ].join(' ')}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Exercise list */}
      <div className="mt-6">
        {isLoading && exercises.length === 0 ? (
          <div className="space-y-0">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="flex items-center justify-between border-b border-[var(--color-border)] py-5"
              >
                <div className="space-y-2">
                  <div className="h-4 w-56 animate-pulse rounded bg-[var(--color-neutral-100)] dark:bg-[var(--color-neutral-800)]" />
                  <div className="h-3 w-32 animate-pulse rounded bg-[var(--color-neutral-50)] dark:bg-[var(--color-neutral-800)]/50" />
                </div>
              </div>
            ))}
          </div>
        ) : exercises.length === 0 ? (
          <div className="py-16 text-center">
            <p className="text-[1.0625rem] font-medium text-[var(--color-text-primary)]">
              Sin ejercicios
            </p>
            <p className="mt-1.5 text-[0.875rem] text-[var(--color-text-tertiary)]">
              {role === 'alumno'
                ? 'Inscribite en un curso para ver ejercicios disponibles.'
                : 'Crea ejercicios desde la pagina del curso.'}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-[var(--color-border)]">
            {exercises.map((ex, i) => {
              const colors = DIFFICULTY_COLORS[ex.difficulty];
              return (
                <Link
                  key={ex.id}
                  to={`/exercises/${ex.id}`}
                  className="group flex items-center justify-between py-4 animate-[slideIn_400ms_cubic-bezier(0.32,0.72,0,1)_both]"
                  style={{ animationDelay: `${i * 50}ms` }}
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-[0.9375rem] font-semibold text-[var(--color-text-primary)] transition-colors duration-300 group-hover:text-[var(--color-accent-600)]">
                      {ex.title}
                    </p>
                    <div className="mt-1 flex items-center gap-2">
                      {ex.topic_tags.slice(0, 3).map((tag) => (
                        <span
                          key={tag}
                          className="text-[0.6875rem] text-[var(--color-text-tertiary)]"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                  <span
                    className={`shrink-0 rounded-full px-2.5 py-0.5 text-[0.6875rem] font-semibold uppercase tracking-wider ${colors.bg} ${colors.text}`}
                  >
                    {ex.difficulty}
                  </span>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
