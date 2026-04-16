interface StrategyDistributionProps {
  n2Scores: number[];
}

const RANGES = [
  { label: '0-25', min: 0, max: 25 },
  { label: '25-50', min: 25, max: 50 },
  { label: '50-75', min: 50, max: 75 },
  { label: '75-100', min: 75, max: 100 },
];

export default function StrategyDistribution({ n2Scores }: StrategyDistributionProps) {
  const total = n2Scores.length;
  const counts = RANGES.map((r) => n2Scores.filter((s) => s >= r.min && s < (r.max === 100 ? 101 : r.max)).length);
  const maxCount = Math.max(...counts, 1);

  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <h3 className="mb-4 text-[0.8125rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-secondary)]">
        Distribucion N2 (Estrategia)
      </h3>
      {total === 0 ? (
        <p className="text-[0.875rem] text-[var(--color-text-tertiary)]">Sin datos</p>
      ) : (
        <div className="space-y-2">
          {RANGES.map((r, i) => {
            const pct = (counts[i] / maxCount) * 100;
            return (
              <div key={r.label} className="flex items-center gap-3">
                <span className="w-12 text-right font-mono text-[0.75rem] text-[var(--color-text-tertiary)]">
                  {r.label}
                </span>
                <div className="flex-1">
                  <div className="h-5 overflow-hidden rounded-[var(--radius-sm)] bg-[var(--color-neutral-100)] dark:bg-[var(--color-neutral-800)]">
                    <div
                      className="h-full rounded-[var(--radius-sm)] bg-[var(--color-success-500)] transition-all duration-500 ease-[cubic-bezier(0.32,0.72,0,1)]"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
                <span className="w-6 text-right font-mono text-[0.75rem] tabular-nums text-[var(--color-text-tertiary)]">
                  {counts[i]}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
