import type { ScoreCardData } from './types';

interface ScoreCardProps {
  data: ScoreCardData;
}

function trendIndicator(current: number | null, previous: number | null): string {
  if (current === null || previous === null) return '';
  const diff = current - previous;
  if (diff > 2) return '\u2191';
  if (diff < -2) return '\u2193';
  return '\u2192';
}

function trendColor(current: number | null, previous: number | null): string {
  if (current === null || previous === null) return 'text-[var(--color-text-tertiary)]';
  const diff = current - previous;
  if (diff > 2) return 'text-[var(--color-success-600)]';
  if (diff < -2) return 'text-[var(--color-error-500)]';
  return 'text-[var(--color-text-tertiary)]';
}

export default function ScoreCard({ data }: ScoreCardProps) {
  const { label, score, previousScore } = data;
  const trend = trendIndicator(score, previousScore);
  const color = trendColor(score, previousScore);

  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <p className="text-[0.6875rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
        {label}
      </p>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-[2rem] font-bold tabular-nums tracking-tight text-[var(--color-text-primary)]">
          {score !== null ? score.toFixed(1) : '-'}
        </span>
        {trend && (
          <span className={`text-[1.25rem] font-medium ${color}`}>{trend}</span>
        )}
      </div>
    </div>
  );
}
