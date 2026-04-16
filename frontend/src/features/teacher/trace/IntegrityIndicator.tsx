import { useTraceStore } from './store';

export default function IntegrityIndicator() {
  const verification = useTraceStore((s) => s.verification);
  const session = useTraceStore((s) => s.session);

  if (!session || session.status === 'open') {
    return (
      <span className="text-[0.75rem] text-[var(--color-text-tertiary)]">
        Verificacion pendiente (sesion abierta)
      </span>
    );
  }

  if (!verification) {
    return (
      <span className="text-[0.75rem] text-[var(--color-text-tertiary)]">
        Verificando...
      </span>
    );
  }

  if (verification.valid) {
    return (
      <div className="flex items-center gap-2">
        <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-[var(--color-success-100)] text-[var(--color-success-600)] dark:bg-[var(--color-success-900)]/30">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M2.5 6L5 8.5L9.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
        <span className="text-[0.8125rem] font-medium text-[var(--color-success-700)] dark:text-[var(--color-success-400)]">
          Cadena integra ({verification.events_checked} eventos verificados)
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-[var(--color-error-100)] text-[var(--color-error-600)] dark:bg-[var(--color-error-900)]/30">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path d="M3 3L9 9M9 3L3 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </span>
      <span className="text-[0.8125rem] font-medium text-[var(--color-error-700)] dark:text-[var(--color-error-400)]">
        Cadena comprometida en evento #{verification.failed_at_sequence}
      </span>
    </div>
  );
}
