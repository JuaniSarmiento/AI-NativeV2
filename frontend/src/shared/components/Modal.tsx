import { useEffect, useRef, useCallback, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  title?: string;
  /** Width constraint. Defaults to max-w-lg. */
  maxWidth?: string;
}

/**
 * Modal — Double-Bezel + portal + spring animation.
 *
 * Per high-end-visual-design directive:
 * - Backdrop: heavy blur on fixed element only (never scrolling content)
 * - Content: Double-Bezel (outer ring + inner core with inset highlight)
 * - Entry: spring scale-up animation via cubic-bezier(0.32, 0.72, 0, 1)
 * - Close: escape key, backdrop click
 * - Accessibility: role=dialog, aria-modal, focus trap, body scroll lock
 * - No `shadow-md`, no `linear` easing
 */
export default function Modal({
  open,
  onClose,
  children,
  title,
  maxWidth = 'max-w-lg',
}: ModalProps) {
  const contentRef = useRef<HTMLDivElement>(null);

  const handleClose = useCallback(() => onClose(), [onClose]);

  /* Close on Escape */
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') handleClose();
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, handleClose]);

  /* Focus content on open, restore on close */
  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    contentRef.current?.focus();
    return () => {
      prev?.focus();
    };
  }, [open]);

  /* Lock body scroll */
  useEffect(() => {
    if (!open) return;
    const scrollY = window.scrollY;
    document.body.style.position = 'fixed';
    document.body.style.top = `-${scrollY}px`;
    document.body.style.left = '0';
    document.body.style.right = '0';
    return () => {
      document.body.style.position = '';
      document.body.style.top = '';
      document.body.style.left = '';
      document.body.style.right = '';
      window.scrollTo(0, scrollY);
    };
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4 py-6"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      {/* Backdrop — blur on fixed element only (performance guardrail) */}
      <div
        className="absolute inset-0 bg-[var(--color-neutral-950)]/50 backdrop-blur-sm animate-[fadeIn_200ms_ease-out]"
        onClick={handleClose}
        aria-hidden
      />

      {/* Double-Bezel Content */}
      <div
        ref={contentRef}
        tabIndex={-1}
        className={[
          'relative z-10 w-full outline-none',
          maxWidth,
          /* Outer Shell */
          'rounded-[16px] p-[1px]',
          'bg-[var(--color-neutral-100)] dark:bg-[var(--color-neutral-800)]',
          'ring-1 ring-[var(--color-border)]',
          /* Spring entry animation */
          'animate-[modalIn_350ms_cubic-bezier(0.32,0.72,0,1)]',
        ].join(' ')}
      >
        {/* Inner Core */}
        <div
          className={[
            'rounded-[15px]',
            'bg-[var(--color-surface-alt)]',
            'shadow-[0_25px_50px_-12px_rgba(0,0,0,0.08),inset_0_1px_0_rgba(255,255,255,0.6)]',
            'dark:shadow-[0_25px_50px_-12px_rgba(0,0,0,0.3),inset_0_1px_0_rgba(255,255,255,0.04)]',
          ].join(' ')}
        >
          {/* Header */}
          {title && (
            <div className="flex items-center justify-between border-b border-[var(--color-border)] px-6 py-4">
              <h2 className="text-[0.9375rem] font-semibold tracking-tight text-[var(--color-text-primary)]">
                {title}
              </h2>
              <button
                onClick={handleClose}
                className="flex h-7 w-7 items-center justify-center rounded-[6px] text-[var(--color-text-tertiary)] transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] hover:bg-[var(--color-neutral-100)] hover:text-[var(--color-text-primary)] active:scale-[0.92] dark:hover:bg-[var(--color-neutral-800)]"
                aria-label="Cerrar"
              >
                <svg
                  className="h-3.5 w-3.5"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6 18 18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          )}

          {/* Body */}
          <div className="p-6">{children}</div>
        </div>
      </div>
    </div>,
    document.body,
  );
}

export type { ModalProps };
