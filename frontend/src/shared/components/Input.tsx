import { forwardRef, type InputHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helper?: string;
}

/**
 * Input — Premium utilitarian design.
 *
 * Follows taste-skill + minimalist-skill directives:
 * - Label ABOVE input (Rule 6)
 * - Helper text optional, error text below
 * - Border: 1px solid using theme token, not generic gray
 * - Focus: subtle ring with spring easing, tinted to neutral
 * - Error: red border + inline message, no generic glow
 * - No `shadow-md`, no neon focus rings
 * - Transitions use cubic-bezier(0.32, 0.72, 0, 1)
 */
const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helper, id, className = '', ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');

    return (
      <div className="space-y-1.5">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-[0.8125rem] font-medium text-[var(--color-text-primary)]"
          >
            {label}
          </label>
        )}

        {/* Input with Double-Bezel–lite: outer subtle ring on focus, inner clean surface */}
        <input
          ref={ref}
          id={inputId}
          className={[
            'h-11 w-full rounded-[8px] border px-3.5',
            'bg-[var(--color-surface)] text-[0.9375rem] text-[var(--color-text-primary)]',
            'outline-none',
            'transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]',
            'placeholder:text-[var(--color-text-tertiary)]',
            error
              ? 'border-[#9F2F2D]/40 focus:border-[#9F2F2D] focus:ring-2 focus:ring-[#9F2F2D]/10'
              : [
                  'border-[var(--color-border)]',
                  'hover:border-[var(--color-neutral-300)]',
                  'focus:border-[var(--color-neutral-400)] focus:ring-2 focus:ring-[var(--color-neutral-400)]/10',
                ].join(' '),
            className,
          ].join(' ')}
          aria-invalid={!!error}
          aria-describedby={
            error ? `${inputId}-error` : helper ? `${inputId}-helper` : undefined
          }
          {...props}
        />

        {/* Error message — muted red from minimalist-skill palette */}
        {error && (
          <p
            id={`${inputId}-error`}
            className="text-[0.8125rem] text-[#9F2F2D]"
          >
            {error}
          </p>
        )}

        {/* Helper text — tertiary color, smaller than label */}
        {!error && helper && (
          <p
            id={`${inputId}-helper`}
            className="text-[0.75rem] text-[var(--color-text-tertiary)]"
          >
            {helper}
          </p>
        )}
      </div>
    );
  },
);

Input.displayName = 'Input';

export default Input;
export type { InputProps };
