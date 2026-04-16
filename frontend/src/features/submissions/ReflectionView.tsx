import Card from '@/shared/components/Card';

interface Reflection {
  id: string;
  difficulty_perception: number;
  strategy_description: string;
  ai_usage_evaluation: string;
  what_would_change: string;
  confidence_level: number;
  created_at: string;
}

interface ReflectionViewProps {
  reflection: Reflection;
}

const DIFFICULTY_LABELS = ['Muy facil', 'Facil', 'Normal', 'Dificil', 'Muy dificil'];
const CONFIDENCE_LABELS = ['Nada seguro', 'Poco seguro', 'Normal', 'Bastante seguro', 'Muy seguro'];

/**
 * ReflectionView — Read-only display of a submitted reflection.
 *
 * Editorial layout: clean typography, minimal chrome, generous whitespace.
 * No interactive elements. Follows Card double-bezel pattern.
 */
export default function ReflectionView({ reflection }: ReflectionViewProps) {
  return (
    <div className="mx-auto max-w-[640px] animate-[fadeSlideIn_400ms_cubic-bezier(0.32,0.72,0,1)_both]">
      <h2 className="text-[1.25rem] font-bold tracking-tight text-[var(--color-text-primary)]">
        Tu reflexion
      </h2>
      <p className="mt-1 text-[0.75rem] text-[var(--color-text-tertiary)]">
        Enviada el{' '}
        {new Date(reflection.created_at).toLocaleDateString('es-AR', {
          day: 'numeric',
          month: 'long',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        })}
      </p>

      <div className="mt-6 space-y-4">
        <Card padding="sm">
          <dt className="text-[0.75rem] font-medium tracking-wide text-[var(--color-text-tertiary)]">
            Dificultad percibida
          </dt>
          <dd className="mt-1 flex items-center gap-2">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-[6px] bg-[var(--color-neutral-900)] text-[0.8125rem] font-medium text-white dark:bg-[var(--color-neutral-200)] dark:text-[var(--color-neutral-900)]">
              {reflection.difficulty_perception}
            </span>
            <span className="text-[0.875rem] text-[var(--color-text-secondary)]">
              {DIFFICULTY_LABELS[reflection.difficulty_perception - 1]}
            </span>
          </dd>
        </Card>

        <Card padding="sm">
          <dt className="text-[0.75rem] font-medium tracking-wide text-[var(--color-text-tertiary)]">
            Estrategia utilizada
          </dt>
          <dd className="mt-1.5 whitespace-pre-wrap text-[0.875rem] leading-relaxed text-[var(--color-text-primary)]">
            {reflection.strategy_description}
          </dd>
        </Card>

        <Card padding="sm">
          <dt className="text-[0.75rem] font-medium tracking-wide text-[var(--color-text-tertiary)]">
            Evaluacion del uso de la IA
          </dt>
          <dd className="mt-1.5 whitespace-pre-wrap text-[0.875rem] leading-relaxed text-[var(--color-text-primary)]">
            {reflection.ai_usage_evaluation}
          </dd>
        </Card>

        <Card padding="sm">
          <dt className="text-[0.75rem] font-medium tracking-wide text-[var(--color-text-tertiary)]">
            Que haria diferente
          </dt>
          <dd className="mt-1.5 whitespace-pre-wrap text-[0.875rem] leading-relaxed text-[var(--color-text-primary)]">
            {reflection.what_would_change}
          </dd>
        </Card>

        <Card padding="sm">
          <dt className="text-[0.75rem] font-medium tracking-wide text-[var(--color-text-tertiary)]">
            Nivel de confianza
          </dt>
          <dd className="mt-1 flex items-center gap-2">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-[6px] bg-[var(--color-neutral-900)] text-[0.8125rem] font-medium text-white dark:bg-[var(--color-neutral-200)] dark:text-[var(--color-neutral-900)]">
              {reflection.confidence_level}
            </span>
            <span className="text-[0.875rem] text-[var(--color-text-secondary)]">
              {CONFIDENCE_LABELS[reflection.confidence_level - 1]}
            </span>
          </dd>
        </Card>
      </div>
    </div>
  );
}
