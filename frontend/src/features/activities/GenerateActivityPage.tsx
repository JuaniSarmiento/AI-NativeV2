import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useActivitiesStore } from './store';
import { useCoursesStore } from '@/features/courses/store';
import Button from '@/shared/components/Button';
import Card from '@/shared/components/Card';
import type { ExerciseDifficulty } from '@/features/exercises/types';

const DIFFICULTY_COLORS: Record<ExerciseDifficulty, { bg: string; text: string }> = {
  easy: { bg: 'bg-[#EDF3EC]', text: 'text-[#346538]' },
  medium: { bg: 'bg-[#FBF3DB]', text: 'text-[#956400]' },
  hard: { bg: 'bg-[#FDEBEC]', text: 'text-[#9F2F2D]' },
};

export default function GenerateActivityPage() {
  const navigate = useNavigate();
  const llmConfig = useActivitiesStore((s) => s.llmConfig);
  const fetchLLMConfig = useActivitiesStore((s) => s.fetchLLMConfig);
  const generateActivity = useActivitiesStore((s) => s.generateActivity);
  const isGenerating = useActivitiesStore((s) => s.isGenerating);
  const courses = useCoursesStore((s) => s.courses);
  const fetchCourses = useCoursesStore((s) => s.fetchCourses);

  const [courseId, setCourseId] = useState('');
  const [prompt, setPrompt] = useState('');
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchLLMConfig();
    fetchCourses();
  }, [fetchLLMConfig, fetchCourses]);

  async function handleGenerate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    try {
      const activity = await generateActivity(courseId, prompt);
      setResult(activity);
    } catch (err: any) {
      setError(err?.message || 'Error al generar la actividad.');
    }
  }

  if (!llmConfig?.has_key) {
    return (
      <div>
        <h1 className="text-[1.75rem] font-bold tracking-tight text-[var(--color-text-primary)]">
          Generar actividad
        </h1>
        <Card padding="lg" className="mt-8 max-w-lg">
          <div className="text-center py-6">
            <p className="text-[1.0625rem] font-medium text-[var(--color-text-primary)]">
              Necesitas configurar tu API key
            </p>
            <p className="mt-1.5 text-[0.875rem] text-[var(--color-text-tertiary)]">
              Anda a Configuracion para agregar tu clave de OpenAI o Anthropic.
            </p>
            <Button
              variant="primary"
              size="md"
              className="mt-5"
              onClick={() => navigate('/settings')}
            >
              Ir a Configuracion
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <span className="inline-block rounded-full bg-[var(--color-neutral-100)] px-3 py-1 text-[0.625rem] font-semibold uppercase tracking-[0.15em] text-[var(--color-text-secondary)] dark:bg-[var(--color-neutral-800)]">
        IA
      </span>
      <h1 className="mt-3 text-[1.75rem] font-bold tracking-tight text-[var(--color-text-primary)]">
        Generar actividad
      </h1>
      <p className="mt-1.5 text-[0.9375rem] text-[var(--color-text-secondary)]">
        Describe que tipo de actividad queres y la IA la genera usando el material de la catedra.
      </p>

      {/* Generation form */}
      <Card padding="lg" className="mt-8 max-w-2xl">
        <form onSubmit={handleGenerate} className="space-y-5">
          {/* Course select */}
          <div className="space-y-1.5">
            <label className="block text-[0.8125rem] font-medium text-[var(--color-text-primary)]">
              Curso
            </label>
            <select
              value={courseId}
              onChange={(e) => setCourseId(e.target.value)}
              required
              className="h-11 w-full rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 text-[0.9375rem] text-[var(--color-text-primary)] outline-none transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] focus:border-[var(--color-neutral-400)] focus:ring-2 focus:ring-[var(--color-neutral-400)]/10"
            >
              <option value="">Selecciona un curso</option>
              {courses.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>

          {/* Prompt */}
          <div className="space-y-1.5">
            <label className="block text-[0.8125rem] font-medium text-[var(--color-text-primary)]">
              Instruccion
            </label>
            <textarea
              required
              rows={4}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Ej: Creame una actividad de 3 ejercicios sobre funciones y listas, de dificultad progresiva (facil, medio, dificil)"
              className="w-full rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 text-[0.9375rem] text-[var(--color-text-primary)] outline-none transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-neutral-400)] focus:ring-2 focus:ring-[var(--color-neutral-400)]/10"
            />
            <p className="text-[0.75rem] text-[var(--color-text-tertiary)]">
              Usando: {llmConfig.provider} / {llmConfig.model_name}
            </p>
          </div>

          {error && (
            <div className="rounded-[8px] border border-[#9F2F2D]/20 bg-[#FDEBEC] px-4 py-3 text-[0.8125rem] text-[#9F2F2D]">
              {error}
            </div>
          )}

          <Button
            variant="primary"
            size="lg"
            type="submit"
            loading={isGenerating}
            disabled={!courseId || !prompt}
            className="w-full"
          >
            {isGenerating ? 'Generando actividad...' : 'Generar con IA'}
          </Button>
        </form>
      </Card>

      {/* Result */}
      {result && (
        <div className="mt-10 max-w-2xl animate-[slideIn_500ms_cubic-bezier(0.32,0.72,0,1)]">
          <div className="flex items-center justify-between">
            <h2 className="text-[1.25rem] font-bold tracking-tight text-[var(--color-text-primary)]">
              {result.title}
            </h2>
            <span className="rounded-full bg-[#FBF3DB] px-2.5 py-0.5 text-[0.6875rem] font-semibold uppercase tracking-wider text-[#956400]">
              Draft
            </span>
          </div>
          {result.description && (
            <p className="mt-2 text-[0.9375rem] text-[var(--color-text-secondary)]">{result.description}</p>
          )}

          <div className="mt-6 divide-y divide-[var(--color-border)]">
            {result.exercises?.map((ex: any, i: number) => {
              const colors = DIFFICULTY_COLORS[ex.difficulty as ExerciseDifficulty] || DIFFICULTY_COLORS.medium;
              return (
                <div
                  key={ex.id || i}
                  className="py-4 animate-[slideIn_400ms_cubic-bezier(0.32,0.72,0,1)_both]"
                  style={{ animationDelay: `${i * 80}ms` }}
                >
                  <div className="flex items-center justify-between">
                    <p className="text-[0.9375rem] font-semibold text-[var(--color-text-primary)]">
                      {ex.title}
                    </p>
                    <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-[0.6875rem] font-semibold uppercase tracking-wider ${colors.bg} ${colors.text}`}>
                      {ex.difficulty}
                    </span>
                  </div>
                  <p className="mt-1.5 text-[0.8125rem] leading-relaxed text-[var(--color-text-secondary)] line-clamp-3">
                    {ex.description}
                  </p>
                </div>
              );
            })}
          </div>

          <div className="mt-6 flex gap-3">
            <Button
              variant="primary"
              size="md"
              onClick={() => navigate(`/activities/${result.id}`)}
            >
              Revisar y publicar
            </Button>
            <Button
              variant="secondary"
              size="md"
              onClick={() => { setResult(null); setPrompt(''); }}
            >
              Generar otra
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
