import type { ScoreBreakdown as ScoreBreakdownType, ScoreCondition } from './types';

interface ScoreBreakdownProps {
  breakdown: ScoreBreakdownType | null;
}

const LEVEL_LABELS: Record<string, string> = {
  n1: 'N1 Comprension',
  n2: 'N2 Estrategia',
  n3: 'N3 Validacion',
  n4: 'N4 Interaccion IA',
  qe: 'Qe Calidad Epistemica',
};

const LEVELS = ['n1', 'n2', 'n3', 'n4', 'qe'] as const;
type LevelKey = (typeof LEVELS)[number];

function ConditionItem({ item }: { item: ScoreCondition }) {
  return (
    <li className="flex items-start gap-1.5 text-sm">
      <span
        className={`mt-0.5 shrink-0 font-semibold ${
          item.met
            ? 'text-[var(--color-success-600)] dark:text-[var(--color-success-400)]'
            : 'text-[var(--color-error-600)] dark:text-[var(--color-error-400)]'
        }`}
        aria-hidden="true"
      >
        {item.met ? '✓' : '✗'}
      </span>
      <span className="text-[var(--color-text-secondary)]">
        {item.condition}
        {item.points !== 0 && (
          <span className="ml-1 text-[0.6875rem] text-[var(--color-text-tertiary)]">
            ({item.points > 0 ? '+' : ''}
            {item.points} pts)
          </span>
        )}
      </span>
    </li>
  );
}

export function ScoreBreakdown({ breakdown }: ScoreBreakdownProps) {
  if (!breakdown) {
    return (
      <p className="py-2 text-sm text-[var(--color-text-tertiary)]">Sin desglose disponible</p>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 py-3 md:grid-cols-2">
      {LEVELS.map((level) => {
        const items = breakdown[level as LevelKey];
        if (!items || items.length === 0) return null;
        return (
          <div key={level}>
            <h4 className="mb-1 text-sm font-semibold text-[var(--color-text-primary)]">
              {LEVEL_LABELS[level]}
            </h4>
            <ul className="space-y-0.5">
              {items.map((item, idx) => (
                <ConditionItem key={`${level}-${idx}`} item={item} />
              ))}
            </ul>
          </div>
        );
      })}
    </div>
  );
}
