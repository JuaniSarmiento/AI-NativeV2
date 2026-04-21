interface CoherenceSemaphoresProps {
  temporal: number | null;
  codeDiscourse: number | null;
  interIteration: number | null;
}

function getSemaphoreColor(score: number | null): string {
  if (score === null) return 'bg-[var(--color-neutral-300)] dark:bg-[var(--color-neutral-600)]';
  if (score >= 70) return 'bg-[var(--color-success-500)]';
  if (score >= 40) return 'bg-[var(--color-warning-500)]';
  return 'bg-[var(--color-error-500)]';
}

function getTooltip(label: string, score: number | null): string {
  if (score === null) return `${label}: Sin datos`;
  return `${label}: ${score.toFixed(1)}`;
}

export function CoherenceSemaphores({
  temporal,
  codeDiscourse,
  interIteration,
}: CoherenceSemaphoresProps) {
  const items = [
    { label: 'Temporal', score: temporal },
    { label: 'Codigo-Discurso', score: codeDiscourse },
    { label: 'Inter-iteracion', score: interIteration },
  ];

  return (
    <div className="flex items-center gap-1.5" aria-label="Coherencia cognitiva">
      {items.map(({ label, score }) => (
        <div
          key={label}
          className={`h-3 w-3 rounded-full ${getSemaphoreColor(score)}`}
          title={getTooltip(label, score)}
          role="img"
          aria-label={getTooltip(label, score)}
        />
      ))}
    </div>
  );
}
