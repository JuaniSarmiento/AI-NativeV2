import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: ReactNode;
  iconPosition?: 'left' | 'right';
}

/*
 * Variant styling — no `shadow-md`, no neon glows, no generic borders.
 * Primary uses off-black (#18181b) per minimalist-skill directive.
 * All interactive states use spring easing + tactile scale feedback.
 */
const variantClasses: Record<ButtonVariant, string> = {
  primary: [
    'bg-[var(--color-neutral-900)] text-white',
    'hover:bg-[var(--color-neutral-800)]',
    'focus-visible:ring-[var(--color-neutral-400)]/25',
  ].join(' '),
  secondary: [
    'border border-[var(--color-border)] bg-[var(--color-surface-alt)] text-[var(--color-text-primary)]',
    'shadow-[0_1px_2px_rgba(0,0,0,0.04)]',
    'hover:border-[var(--color-neutral-300)] hover:shadow-[0_2px_8px_rgba(0,0,0,0.04)]',
    'focus-visible:ring-[var(--color-neutral-400)]/20',
  ].join(' '),
  ghost: [
    'text-[var(--color-text-secondary)]',
    'hover:bg-[var(--color-neutral-100)] hover:text-[var(--color-text-primary)]',
    'dark:hover:bg-[var(--color-neutral-800)]',
    'focus-visible:ring-[var(--color-neutral-400)]/20',
  ].join(' '),
  danger: [
    'bg-[#9F2F2D] text-white',
    'hover:bg-[#862826]',
    'focus-visible:ring-[#9F2F2D]/25',
  ].join(' '),
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-[0.8125rem] gap-1.5 rounded-[6px]',
  md: 'h-10 px-4 text-[0.875rem] gap-2 rounded-[8px]',
  lg: 'h-12 px-6 text-[0.9375rem] gap-2.5 rounded-[8px]',
};

/**
 * Button — Premium utilitarian design.
 *
 * Follows taste-skill directives:
 * - Spring easing on all transitions (cubic-bezier(0.32, 0.72, 0, 1))
 * - Tactile `active:scale-[0.98]` press feedback
 * - Button-in-Button trailing icon wrapped in its own circular container
 * - No neon glows, no `shadow-md`, no `linear` easing
 * - Loading state replaces content with spinner (no layout shift)
 */
const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      icon,
      iconPosition = 'right',
      disabled,
      children,
      className = '',
      ...props
    },
    ref,
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={[
          'group inline-flex items-center justify-center font-semibold',
          'transition-all duration-500 ease-[cubic-bezier(0.32,0.72,0,1)]',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1',
          'active:scale-[0.98]',
          'disabled:pointer-events-none disabled:opacity-40',
          variantClasses[variant],
          sizeClasses[size],
          className,
        ].join(' ')}
        {...props}
      >
        {loading ? (
          <span
            className="inline-block h-4 w-4 animate-spin rounded-full border-[1.5px] border-current/25 border-t-current"
            aria-label="Cargando"
          />
        ) : (
          <>
            {/* Left icon — plain, no wrapper */}
            {icon && iconPosition === 'left' && (
              <span className="shrink-0 transition-transform duration-500 ease-[cubic-bezier(0.32,0.72,0,1)] group-hover:-translate-x-0.5">
                {icon}
              </span>
            )}

            {children}

            {/* Right icon — Button-in-Button pattern per high-end-visual-design directive */}
            {icon && iconPosition === 'right' && (
              <span
                className={[
                  'inline-flex shrink-0 items-center justify-center rounded-full',
                  'transition-all duration-500 ease-[cubic-bezier(0.32,0.72,0,1)]',
                  'group-hover:translate-x-0.5 group-hover:-translate-y-[1px] group-hover:scale-105',
                  size === 'sm' ? 'ml-0.5 h-5 w-5' : 'ml-1 h-6 w-6',
                  variant === 'primary'
                    ? 'bg-white/10'
                    : variant === 'danger'
                      ? 'bg-white/10'
                      : 'bg-[var(--color-neutral-900)]/5 dark:bg-white/10',
                ].join(' ')}
              >
                {icon}
              </span>
            )}
          </>
        )}
      </button>
    );
  },
);

Button.displayName = 'Button';

export default Button;
export type { ButtonProps, ButtonVariant, ButtonSize };
