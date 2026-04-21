import { useTraceStore } from './store';
import type { TraceAnomaly } from './types';

const EMPTY_ANOMALIES: TraceAnomaly[] = [];

const SEVERITY_CLASSES: Record<string, string> = {
  high: 'border-l-[var(--color-error-500,#ef4444)] bg-[var(--color-error-50,#fef2f2)] dark:bg-[var(--color-error-900,#450a0a)]/20',
  medium: 'border-l-[var(--color-warning-500,#f59e0b)] bg-[var(--color-warning-50,#fffbeb)] dark:bg-[var(--color-warning-900,#451a03)]/20',
  low: 'border-l-amber-400 bg-amber-50 dark:bg-amber-950/20',
};

const SEVERITY_TEXT: Record<string, string> = {
  high: 'text-[var(--color-error-700,#b91c1c)] dark:text-[var(--color-error-400,#f87171)]',
  medium: 'text-[var(--color-warning-700,#b45309)] dark:text-[var(--color-warning-400,#fbbf24)]',
  low: 'text-amber-700 dark:text-amber-400',
};

export default function AnomalyBanners() {
  const anomalies = useTraceStore((s) => s.anomalies);
  const items = anomalies.length > 0 ? anomalies : EMPTY_ANOMALIES;

  if (items.length === 0) return null;

  return (
    <div className="space-y-2" role="alert" aria-label="Anomalias detectadas">
      {items.map((anomaly, i) => {
        const sev = anomaly.severity ?? 'low';
        const containerClass = SEVERITY_CLASSES[sev] ?? SEVERITY_CLASSES.low;
        const textClass = SEVERITY_TEXT[sev] ?? SEVERITY_TEXT.low;

        return (
          <div
            key={`${anomaly.code}-${i}`}
            className={`flex items-start gap-2.5 rounded-r-lg border-l-[3px] px-3 py-2.5 ${containerClass}`}
          >
            {/* Warning icon */}
            <svg
              className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${textClass}`}
              viewBox="0 0 16 16"
              fill="currentColor"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M6.457 1.047c.659-1.234 2.427-1.234 3.086 0l6.082 11.378A1.75 1.75 0 0 1 14.082 15H1.918a1.75 1.75 0 0 1-1.543-2.575L6.457 1.047ZM9 11a1 1 0 1 1-2 0 1 1 0 0 1 2 0Zm-.25-5.25a.75.75 0 0 0-1.5 0v2.5a.75.75 0 0 0 1.5 0v-2.5Z"
                clipRule="evenodd"
              />
            </svg>

            <div className="min-w-0 flex-1">
              <span className={`text-[0.75rem] font-medium leading-snug ${textClass}`}>
                {anomaly.message}
              </span>
              {anomaly.code && (
                <span className="ml-2 font-mono text-[0.625rem] opacity-60">
                  [{anomaly.code}]
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
