import type { RiskLevel } from './types';
import { RISK_LABELS } from './types';

interface RiskBadgeProps {
  level: RiskLevel;
}

const BADGE_CLASSES: Record<RiskLevel, string> = {
  critical:
    'bg-[var(--color-error-50)] text-[var(--color-error-700)] dark:bg-[var(--color-error-900)]/20 dark:text-[var(--color-error-400)]',
  high: 'bg-[var(--color-warning-50)] text-[var(--color-warning-700)] dark:bg-[var(--color-warning-900)]/20 dark:text-[var(--color-warning-400)]',
  medium:
    'bg-[var(--color-warning-50)] text-[var(--color-warning-600)] dark:bg-[var(--color-warning-900)]/10 dark:text-[var(--color-warning-300)]',
  low: 'bg-[var(--color-success-50)] text-[var(--color-success-700)] dark:bg-[var(--color-success-900)]/20 dark:text-[var(--color-success-400)]',
};

export default function RiskBadge({ level }: RiskBadgeProps) {
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-[0.625rem] font-semibold uppercase tracking-[0.08em] ${BADGE_CLASSES[level]}`}
    >
      {RISK_LABELS[level]}
    </span>
  );
}
