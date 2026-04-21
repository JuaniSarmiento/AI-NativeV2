interface CoherenceTrafficLightProps {
  temporal: number | null;
  codeDiscourse: number | null;
  interIteration: number | null;
}

interface LightProps {
  value: number | null;
  label: string;
}

function circleColor(value: number | null): {
  bg: string;
  border: string;
  text: string;
} {
  if (value === null) {
    return {
      bg: 'bg-[var(--color-neutral-200)] dark:bg-[var(--color-neutral-700)]',
      border: 'border-[var(--color-neutral-300)] dark:border-[var(--color-neutral-600)]',
      text: 'text-[var(--color-text-tertiary)]',
    };
  }
  if (value >= 70) {
    return {
      bg: 'bg-[var(--color-success-100)] dark:bg-[var(--color-success-900)]/30',
      border: 'border-[var(--color-success-400)] dark:border-[var(--color-success-600)]',
      text: 'text-[var(--color-success-700)] dark:text-[var(--color-success-400)]',
    };
  }
  if (value >= 40) {
    return {
      bg: 'bg-[var(--color-warning-100)] dark:bg-[var(--color-warning-900)]/30',
      border: 'border-[var(--color-warning-400)] dark:border-[var(--color-warning-600)]',
      text: 'text-[var(--color-warning-700)] dark:text-[var(--color-warning-400)]',
    };
  }
  return {
    bg: 'bg-[var(--color-error-100)] dark:bg-[var(--color-error-900)]/30',
    border: 'border-[var(--color-error-400)] dark:border-[var(--color-error-600)]',
    text: 'text-[var(--color-error-700)] dark:text-[var(--color-error-400)]',
  };
}

function TrafficLight({ value, label }: LightProps) {
  const colors = circleColor(value);

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div
        className={`flex h-12 w-12 items-center justify-center rounded-full border-2 ${colors.bg} ${colors.border}`}
        title={value !== null ? `${label}: ${value.toFixed(0)}` : `${label}: sin datos`}
      >
        <span className={`text-sm font-bold tabular-nums ${colors.text}`}>
          {value !== null ? value.toFixed(0) : '—'}
        </span>
      </div>
      <span className="text-center text-[0.5625rem] font-medium leading-tight text-[var(--color-text-tertiary)]">
        {label}
      </span>
    </div>
  );
}

export default function CoherenceTrafficLight({
  temporal,
  codeDiscourse,
  interIteration,
}: CoherenceTrafficLightProps) {
  return (
    <div className="space-y-2">
      <span className="text-[0.625rem] font-semibold uppercase tracking-wider text-[var(--color-text-tertiary)]">
        Coherencia
      </span>
      <div className="flex items-start justify-around gap-4">
        <TrafficLight value={temporal} label="Temporal" />
        <TrafficLight value={codeDiscourse} label="Code-Disc" />
        <TrafficLight value={interIteration} label="Inter-iter" />
      </div>
    </div>
  );
}
