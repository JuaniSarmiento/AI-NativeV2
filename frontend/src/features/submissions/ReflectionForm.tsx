import { useState } from 'react';
import { apiClient } from '@/shared/lib/api-client';
import Button from '@/shared/components/Button';
import Card from '@/shared/components/Card';

interface ReflectionFormProps {
  activitySubmissionId: string;
  onComplete: () => void;
  onSkip: () => void;
}

const DIFFICULTY_LABELS = ['Muy facil', 'Facil', 'Normal', 'Dificil', 'Muy dificil'];
const CONFIDENCE_LABELS = ['Nada seguro', 'Poco seguro', 'Normal', 'Bastante seguro', 'Muy seguro'];

/**
 * ReflectionForm — Guided metacognitive reflection post-submission.
 *
 * Minimal editorial form: clean labels, subtle sliders, generous spacing.
 * All fields required. Follows design-system Card double-bezel pattern.
 * Spring easing on entry, no gradients, no emojis.
 */
export default function ReflectionForm({ activitySubmissionId, onComplete, onSkip }: ReflectionFormProps) {
  const [difficulty, setDifficulty] = useState(3);
  const [strategy, setStrategy] = useState('');
  const [aiUsage, setAiUsage] = useState('');
  const [whatWouldChange, setWhatWouldChange] = useState('');
  const [confidence, setConfidence] = useState(3);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isValid =
    strategy.trim().length >= 10 &&
    aiUsage.trim().length >= 10 &&
    whatWouldChange.trim().length >= 10;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isValid) return;

    setSubmitting(true);
    setError(null);

    try {
      await apiClient.post(`/v1/submissions/${activitySubmissionId}/reflection`, {
        difficulty_perception: difficulty,
        strategy_description: strategy.trim(),
        ai_usage_evaluation: aiUsage.trim(),
        what_would_change: whatWouldChange.trim(),
        confidence_level: confidence,
      });
      onComplete();
    } catch (err: any) {
      const msg = err?.response?.data?.errors?.[0]?.message || 'Error al enviar la reflexion';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-[640px] animate-[fadeSlideIn_400ms_cubic-bezier(0.32,0.72,0,1)_both]">
      <h2 className="text-[1.25rem] font-bold tracking-tight text-[var(--color-text-primary)]">
        Reflexion sobre tu trabajo
      </h2>
      <p className="mt-1.5 text-[0.875rem] text-[var(--color-text-secondary)]">
        Antes de irte, reflexiona brevemente sobre tu proceso. Esto nos ayuda a entender mejor como aprendes.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-6">
        {/* Difficulty perception */}
        <Card padding="sm">
          <label className="block text-[0.8125rem] font-medium text-[var(--color-text-primary)]">
            Que tan dificil te parecio esta actividad?
          </label>
          <div className="mt-3 flex items-center gap-3">
            {[1, 2, 3, 4, 5].map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setDifficulty(v)}
                className={[
                  'flex h-10 w-10 items-center justify-center rounded-[8px] text-[0.8125rem] font-medium transition-all duration-200',
                  'active:scale-[0.95]',
                  v === difficulty
                    ? 'bg-[var(--color-neutral-900)] text-white dark:bg-[var(--color-neutral-200)] dark:text-[var(--color-neutral-900)]'
                    : 'bg-[var(--color-neutral-100)] text-[var(--color-text-secondary)] hover:bg-[var(--color-neutral-200)] dark:bg-[var(--color-neutral-800)] dark:hover:bg-[var(--color-neutral-700)]',
                ].join(' ')}
              >
                {v}
              </button>
            ))}
          </div>
          <span className="mt-1.5 block text-[0.75rem] text-[var(--color-text-tertiary)]">
            {DIFFICULTY_LABELS[difficulty - 1]}
          </span>
        </Card>

        {/* Strategy description */}
        <Card padding="sm">
          <label
            htmlFor="strategy"
            className="block text-[0.8125rem] font-medium text-[var(--color-text-primary)]"
          >
            Que estrategia usaste para resolver los ejercicios?
          </label>
          <textarea
            id="strategy"
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            rows={3}
            placeholder="Describe como encaraste la resolucion..."
            className={[
              'mt-2 w-full resize-none rounded-[8px] border px-3 py-2',
              'text-[0.875rem] leading-relaxed text-[var(--color-text-primary)]',
              'bg-[var(--color-surface)] placeholder:text-[var(--color-text-tertiary)]',
              'border-[var(--color-border)] focus:border-[var(--color-neutral-400)] focus:outline-none focus:ring-1 focus:ring-[var(--color-neutral-400)]/20',
              'transition-colors duration-200',
            ].join(' ')}
          />
          {strategy.length > 0 && strategy.trim().length < 10 && (
            <span className="mt-1 block text-[0.75rem] text-[#9F2F2D]">Minimo 10 caracteres</span>
          )}
        </Card>

        {/* AI usage evaluation */}
        <Card padding="sm">
          <label
            htmlFor="ai-usage"
            className="block text-[0.8125rem] font-medium text-[var(--color-text-primary)]"
          >
            Como evaluarias tu uso del tutor IA?
          </label>
          <textarea
            id="ai-usage"
            value={aiUsage}
            onChange={(e) => setAiUsage(e.target.value)}
            rows={3}
            placeholder="Te ayudo a pensar o solo le pediste respuestas?..."
            className={[
              'mt-2 w-full resize-none rounded-[8px] border px-3 py-2',
              'text-[0.875rem] leading-relaxed text-[var(--color-text-primary)]',
              'bg-[var(--color-surface)] placeholder:text-[var(--color-text-tertiary)]',
              'border-[var(--color-border)] focus:border-[var(--color-neutral-400)] focus:outline-none focus:ring-1 focus:ring-[var(--color-neutral-400)]/20',
              'transition-colors duration-200',
            ].join(' ')}
          />
          {aiUsage.length > 0 && aiUsage.trim().length < 10 && (
            <span className="mt-1 block text-[0.75rem] text-[#9F2F2D]">Minimo 10 caracteres</span>
          )}
        </Card>

        {/* What would change */}
        <Card padding="sm">
          <label
            htmlFor="what-change"
            className="block text-[0.8125rem] font-medium text-[var(--color-text-primary)]"
          >
            Que harias diferente la proxima vez?
          </label>
          <textarea
            id="what-change"
            value={whatWouldChange}
            onChange={(e) => setWhatWouldChange(e.target.value)}
            rows={3}
            placeholder="Si pudieras volver atras, que cambiarias?..."
            className={[
              'mt-2 w-full resize-none rounded-[8px] border px-3 py-2',
              'text-[0.875rem] leading-relaxed text-[var(--color-text-primary)]',
              'bg-[var(--color-surface)] placeholder:text-[var(--color-text-tertiary)]',
              'border-[var(--color-border)] focus:border-[var(--color-neutral-400)] focus:outline-none focus:ring-1 focus:ring-[var(--color-neutral-400)]/20',
              'transition-colors duration-200',
            ].join(' ')}
          />
          {whatWouldChange.length > 0 && whatWouldChange.trim().length < 10 && (
            <span className="mt-1 block text-[0.75rem] text-[#9F2F2D]">Minimo 10 caracteres</span>
          )}
        </Card>

        {/* Confidence level */}
        <Card padding="sm">
          <label className="block text-[0.8125rem] font-medium text-[var(--color-text-primary)]">
            Que tan seguro estas de que tu solucion es correcta?
          </label>
          <div className="mt-3 flex items-center gap-3">
            {[1, 2, 3, 4, 5].map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setConfidence(v)}
                className={[
                  'flex h-10 w-10 items-center justify-center rounded-[8px] text-[0.8125rem] font-medium transition-all duration-200',
                  'active:scale-[0.95]',
                  v === confidence
                    ? 'bg-[var(--color-neutral-900)] text-white dark:bg-[var(--color-neutral-200)] dark:text-[var(--color-neutral-900)]'
                    : 'bg-[var(--color-neutral-100)] text-[var(--color-text-secondary)] hover:bg-[var(--color-neutral-200)] dark:bg-[var(--color-neutral-800)] dark:hover:bg-[var(--color-neutral-700)]',
                ].join(' ')}
              >
                {v}
              </button>
            ))}
          </div>
          <span className="mt-1.5 block text-[0.75rem] text-[var(--color-text-tertiary)]">
            {CONFIDENCE_LABELS[confidence - 1]}
          </span>
        </Card>

        {error && (
          <p className="text-[0.8125rem] text-[#9F2F2D]">{error}</p>
        )}

        <div className="flex items-center justify-between pt-2">
          <button
            type="button"
            onClick={onSkip}
            className="text-[0.8125rem] text-[var(--color-text-tertiary)] transition-colors duration-200 hover:text-[var(--color-text-primary)]"
          >
            Saltar reflexion
          </button>
          <Button
            type="submit"
            variant="primary"
            size="md"
            loading={submitting}
            disabled={!isValid || submitting}
          >
            Enviar reflexion
          </Button>
        </div>
      </form>
    </div>
  );
}
