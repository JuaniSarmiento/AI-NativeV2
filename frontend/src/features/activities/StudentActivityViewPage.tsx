import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useActivitiesStore } from './store';
import { useRunCode } from '@/features/sandbox/useRunCode';
import { useAutoSnapshot } from '@/features/submissions/useAutoSnapshot';
import { apiClient } from '@/shared/lib/api-client';
import Button from '@/shared/components/Button';
import Card from '@/shared/components/Card';
import Modal from '@/shared/components/Modal';
import TutorChat from '@/features/tutor/components/TutorChat';
import type { ExerciseDifficulty } from '@/features/exercises/types';

const DIFFICULTY_COLORS: Record<ExerciseDifficulty, { bg: string; text: string }> = {
  easy: { bg: 'bg-[#EDF3EC]', text: 'text-[#346538]' },
  medium: { bg: 'bg-[#FBF3DB]', text: 'text-[#956400]' },
  hard: { bg: 'bg-[#FDEBEC]', text: 'text-[#9F2F2D]' },
};

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  ok: { label: 'Ejecutado correctamente', color: 'text-[#346538]' },
  timeout: { label: 'Tiempo limite excedido (10s)', color: 'text-[#956400]' },
  memory_exceeded: { label: 'Memoria excedida (128MB)', color: 'text-[#956400]' },
  syntax_error: { label: 'Error de sintaxis', color: 'text-[#9F2F2D]' },
  runtime_error: { label: 'Error en ejecucion', color: 'text-[#9F2F2D]' },
  security_violation: { label: 'Import no permitido', color: 'text-[#9F2F2D]' },
};

export default function StudentActivityViewPage() {
  const { activityId } = useParams<{ activityId: string }>();
  const navigate = useNavigate();
  const activity = useActivitiesStore((s) => s.currentActivity);
  const isLoading = useActivitiesStore((s) => s.isLoading);
  const fetchActivity = useActivitiesStore((s) => s.fetchActivity);
  const { result: runResult, isRunning, error: runError, run, reset } = useRunCode();

  const [currentIndex, setCurrentIndex] = useState(0);
  const [codes, setCodes] = useState<Record<string, string>>({});
  const [stdinInputs, setStdinInputs] = useState<Record<string, string>>({});
  const [submitModalOpen, setSubmitModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);

  // Hooks must be called before any early return
  const activeExercises = (activity?.exercises ?? []).filter((e) => e.is_active);
  const currentExercise = activeExercises[currentIndex] ?? null;
  const currentCodeForSnapshot = codes[currentExercise?.id ?? ''] ?? '';
  const { saveNow } = useAutoSnapshot(currentExercise?.id, currentCodeForSnapshot);

  useEffect(() => {
    if (activityId) {
      fetchActivity(activityId);
      // Check if already submitted
      apiClient
        .get<any[]>(`/v1/student/activities/${activityId}/submissions`)
        .then((res) => {
          const subs = Array.isArray(res.data) ? res.data : [];
          if (subs.length > 0) setSubmitted(true);
        })
        .catch(() => {});
    }
  }, [activityId, fetchActivity]);

  useEffect(() => {
    if (!activity?.exercises) return;
    const initialCodes: Record<string, string> = {};
    const initialStdins: Record<string, string> = {};
    for (const ex of activity.exercises) {
      if (ex.is_active && !codes[ex.id]) {
        initialCodes[ex.id] = ex.starter_code || '';
        // Pre-fill stdin with first visible test case input
        const firstVisible = ex.test_cases?.cases?.find((tc: any) => !tc.is_hidden);
        if (firstVisible?.input) {
          initialStdins[ex.id] = firstVisible.input;
        }
      }
    }
    if (Object.keys(initialCodes).length > 0) {
      setCodes((prev) => ({ ...initialCodes, ...prev }));
      setStdinInputs((prev) => ({ ...initialStdins, ...prev }));
    }
  }, [activity]);

  function handleNavigate(index: number) {
    setCurrentIndex(index);
    reset();
  }

  if (isLoading || !activity) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 w-64 rounded bg-[var(--color-neutral-100)]" />
        <div className="h-64 w-full rounded-[12px] bg-[var(--color-neutral-100)]" />
      </div>
    );
  }

  const totalExercises = activeExercises.length;
  const currentCode = currentCodeForSnapshot;

  // Submit activity handler
  async function handleSubmitActivity() {
    if (!activityId) return;
    setSubmitting(true);
    try {
      const exercisesPayload = activeExercises.map((ex) => ({
        exercise_id: ex.id,
        code: codes[ex.id] || ex.starter_code || '',
      }));
      await apiClient.post(`/v1/student/activities/${activityId}/submit`, {
        exercises: exercisesPayload,
      });
      setSubmitModalOpen(false);
      setSubmitted(true);
      // Redirect to activities list after short delay
      setTimeout(() => navigate('/actividades'), 1500);
    } catch {
      // Error handling
    } finally {
      setSubmitting(false);
    }
  }

  // Save snapshot before execution
  function handleRun() {
    if (!currentExercise) return;
    saveNow();
    run(currentExercise.id, codes[currentExercise.id] ?? '', stdinInputs[currentExercise.id] ?? '');
  }

  if (!currentExercise) {
    return (
      <div className="py-16 text-center">
        <p className="text-[var(--color-text-secondary)]">Esta actividad no tiene ejercicios.</p>
        <Link to="/actividades"><Button variant="secondary" size="sm" className="mt-4">Volver</Button></Link>
      </div>
    );
  }

  // Already submitted — show confirmation instead of editor
  if (submitted && !submitting) {
    return (
      <div className="py-16 text-center animate-[slideIn_400ms_cubic-bezier(0.32,0.72,0,1)]">
        <span className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-[#EDF3EC]">
          <svg className="h-8 w-8 text-[#346538]" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
          </svg>
        </span>
        <h1 className="mt-5 text-[1.5rem] font-bold tracking-tight text-[var(--color-text-primary)]">
          Actividad enviada
        </h1>
        <p className="mt-2 text-[0.9375rem] text-[var(--color-text-secondary)]">
          Tu codigo fue enviado. El docente va a revisarlo y vas a recibir una nota.
        </p>
        <Link to="/actividades">
          <Button variant="secondary" size="md" className="mt-6">
            Volver a actividades
          </Button>
        </Link>
      </div>
    );
  }

  const currentStdin = stdinInputs[currentExercise.id] ?? '';
  const colors = DIFFICULTY_COLORS[(currentExercise.difficulty as ExerciseDifficulty)] || DIFFICULTY_COLORS.medium;
  const statusInfo = runResult ? STATUS_LABELS[runResult.status] || STATUS_LABELS.ok : null;

  return (
    <div className="flex gap-6">
      {/* Main content */}
      <div className="min-w-0 flex-1">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link to="/actividades" className="text-[0.8125rem] text-[var(--color-text-tertiary)] transition-colors duration-300 hover:text-[var(--color-text-primary)]">
            Actividades
          </Link>
          <h1 className="mt-2 text-[1.5rem] font-bold tracking-tight text-[var(--color-text-primary)]">
            {activity.title}
          </h1>
        </div>
        <div className="text-right shrink-0">
          <span className="text-[0.75rem] font-mono text-[var(--color-text-tertiary)]">
            Ejercicio {currentIndex + 1} de {totalExercises}
          </span>
          <div className="mt-1.5 h-1.5 w-32 rounded-full bg-[var(--color-neutral-100)] dark:bg-[var(--color-neutral-800)]">
            <div
              className="h-full rounded-full bg-[var(--color-accent-500)] transition-all duration-500 ease-[cubic-bezier(0.32,0.72,0,1)]"
              style={{ width: `${((currentIndex + 1) / totalExercises) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Navigation dots */}
      <div className="mt-6 flex items-center gap-2">
        {activeExercises.map((_, i) => (
          <button
            key={i}
            onClick={() => handleNavigate(i)}
            className={[
              'h-2.5 rounded-full transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]',
              i === currentIndex ? 'w-8 bg-[var(--color-accent-500)]' : 'w-2.5 bg-[var(--color-neutral-200)] hover:bg-[var(--color-neutral-300)] dark:bg-[var(--color-neutral-700)]',
            ].join(' ')}
            aria-label={`Ejercicio ${i + 1}`}
          />
        ))}
      </div>

      {/* Exercise */}
      <div className="mt-8" key={currentExercise.id}>
        <div className="flex items-center gap-3">
          <h2 className="text-[1.25rem] font-bold tracking-tight text-[var(--color-text-primary)]">
            {currentExercise.title}
          </h2>
          <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-[0.6875rem] font-semibold uppercase tracking-wider ${colors.bg} ${colors.text}`}>
            {currentExercise.difficulty}
          </span>
        </div>

        {/* Enunciado */}
        <Card padding="md" className="mt-5">
          <div className="text-[0.9375rem] leading-relaxed text-[var(--color-text-primary)] whitespace-pre-wrap">
            {currentExercise.description}
          </div>
        </Card>

        {/* Code editor */}
        <div className="mt-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[0.8125rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
              Tu codigo
            </span>
            <Button
              variant="primary"
              size="sm"
              loading={isRunning}
              onClick={handleRun}
              icon={
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" />
                </svg>
              }
              iconPosition="left"
            >
              Ejecutar
            </Button>
          </div>
          <textarea
            value={currentCode}
            onChange={(e) => setCodes((prev) => ({ ...prev, [currentExercise.id]: e.target.value }))}
            rows={14}
            spellCheck={false}
            className="w-full rounded-[8px] border border-[var(--color-border)] bg-[var(--color-neutral-950)] px-5 py-4 font-mono text-[0.8125rem] leading-relaxed text-[var(--color-neutral-200)] outline-none transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] placeholder:text-[var(--color-neutral-600)] focus:border-[var(--color-neutral-600)] focus:ring-2 focus:ring-[var(--color-neutral-600)]/10 resize-y"
            placeholder="# Escribi tu codigo aca..."
          />
        </div>

        {/* Stdin input */}
        <div className="mt-3">
          <span className="text-[0.75rem] font-medium text-[var(--color-text-tertiary)]">
            Entrada del programa — lo que el usuario escribe cuando se ejecuta (cada linea es un input)
          </span>
          <textarea
            value={currentStdin}
            onChange={(e) => setStdinInputs((prev) => ({ ...prev, [currentExercise.id]: e.target.value }))}
            rows={2}
            spellCheck={false}
            className="mt-1.5 w-full rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2 font-mono text-[0.8125rem] text-[var(--color-text-primary)] outline-none transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-neutral-400)] focus:ring-2 focus:ring-[var(--color-neutral-400)]/10 resize-y"
            placeholder="Ej: 5&#10;3"
          />
        </div>

        {/* Terminal output */}
        {(runResult || runError) && (
          <div className="mt-4 animate-[slideIn_300ms_cubic-bezier(0.32,0.72,0,1)]">
            {runError && (
              <div className="rounded-[8px] border border-[#9F2F2D]/20 bg-[#FDEBEC] px-4 py-3 text-[0.8125rem] text-[#9F2F2D]">
                {runError}
              </div>
            )}

            {runResult && (
              <div className="overflow-hidden rounded-[8px] border border-[var(--color-border)]">
                {/* Terminal header */}
                <div className="flex items-center justify-between border-b border-[var(--color-neutral-800)] bg-[var(--color-neutral-900)] px-4 py-2">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-[var(--color-neutral-700)]" />
                    <span className="h-2.5 w-2.5 rounded-full bg-[var(--color-neutral-700)]" />
                    <span className="h-2.5 w-2.5 rounded-full bg-[var(--color-neutral-700)]" />
                  </div>
                  <div className="flex items-center gap-3">
                    {statusInfo && (
                      <span className={`text-[0.6875rem] font-medium ${statusInfo.color}`}>
                        {statusInfo.label}
                      </span>
                    )}
                    <span className="text-[0.6875rem] font-mono text-[var(--color-neutral-500)]">
                      {runResult.runtime_ms}ms
                    </span>
                  </div>
                </div>

                {/* Terminal body */}
                <div className="bg-[var(--color-neutral-950)] p-4 min-h-[80px]">
                  {runResult.stdout && (
                    <pre className="font-mono text-[0.8125rem] leading-relaxed text-[var(--color-neutral-200)] whitespace-pre-wrap">
                      {runResult.stdout}
                    </pre>
                  )}
                  {runResult.stderr && (
                    <pre className="font-mono text-[0.8125rem] leading-relaxed text-red-400 whitespace-pre-wrap">
                      {runResult.stderr}
                    </pre>
                  )}
                  {!runResult.stdout && !runResult.stderr && (
                    <span className="text-[0.75rem] text-[var(--color-neutral-600)]">
                      (sin salida)
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Navigation */}
        <div className="mt-8 flex items-center justify-between">
          <Button variant="ghost" size="md" disabled={currentIndex === 0} onClick={() => handleNavigate(currentIndex - 1)}>
            Anterior
          </Button>
          <span className="text-[0.8125rem] text-[var(--color-text-tertiary)]">{currentIndex + 1} / {totalExercises}</span>
          {currentIndex < totalExercises - 1 ? (
            <Button variant="primary" size="md" onClick={() => handleNavigate(currentIndex + 1)}>
              Siguiente
            </Button>
          ) : submitted ? (
            <span className="rounded-full bg-[#EDF3EC] px-4 py-2 text-[0.8125rem] font-semibold text-[#346538]">
              Actividad enviada
            </span>
          ) : (
            <Button variant="primary" size="md" onClick={() => setSubmitModalOpen(true)}>
              Enviar actividad
            </Button>
          )}
        </div>
      </div>

      {/* Submit confirmation modal */}
      <Modal open={submitModalOpen} onClose={() => setSubmitModalOpen(false)} title="Enviar actividad">
        <div className="space-y-4">
          <p className="text-[0.9375rem] text-[var(--color-text-primary)]">
            Vas a enviar tu codigo para los <strong>{totalExercises} ejercicios</strong> de esta actividad.
            Despues de enviar, el docente va a poder ver tu trabajo.
          </p>
          <div className="space-y-2">
            {activeExercises.map((ex, i) => {
              const hasCode = (codes[ex.id] || '').trim().length > 0;
              return (
                <div key={ex.id} className="flex items-center gap-2 text-[0.8125rem]">
                  {hasCode ? (
                    <svg className="h-4 w-4 text-[#346538]" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                    </svg>
                  ) : (
                    <svg className="h-4 w-4 text-[#9F2F2D]" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
                    </svg>
                  )}
                  <span className={hasCode ? 'text-[var(--color-text-primary)]' : 'text-[#9F2F2D]'}>
                    {ex.title} {!hasCode && '— sin codigo'}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" size="md" onClick={() => setSubmitModalOpen(false)}>
              Cancelar
            </Button>
            <Button variant="primary" size="md" onClick={handleSubmitActivity} loading={submitting}>
              Confirmar envio
            </Button>
          </div>
        </div>
      </Modal>
      </div>

      {/* Tutor Chat — right panel */}
      {currentExercise && (
        <>
          {/* Desktop: side panel */}
          <div className="hidden md:block md:w-[360px] md:shrink-0">
            <div className="sticky top-6 h-[calc(100vh-8rem)]">
              <TutorChat exerciseId={currentExercise.id} />
            </div>
          </div>

          {/* Mobile: FAB toggle */}
          <div className="fixed bottom-4 right-4 md:hidden z-40">
            <Button
              size="md"
              onClick={() => setChatOpen(!chatOpen)}
              icon={
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              }
              iconPosition="left"
            >
              Tutor
            </Button>
          </div>

          {/* Mobile: bottom sheet */}
          {chatOpen && (
            <div className="fixed inset-0 z-50 md:hidden">
              <div
                className="absolute inset-0 bg-black/20 backdrop-blur-[2px]"
                onClick={() => setChatOpen(false)}
              />
              <div className="absolute bottom-0 left-0 right-0 h-[70vh] overflow-hidden rounded-t-[16px] bg-[var(--color-surface)]">
                <div className="flex justify-center py-2">
                  <div className="h-1 w-8 rounded-full bg-[var(--color-neutral-300)]" />
                </div>
                <div className="h-[calc(100%-24px)] px-3 pb-3">
                  <TutorChat exerciseId={currentExercise.id} />
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
