import type { HTMLAttributes, ReactNode } from 'react';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  padding?: 'sm' | 'md' | 'lg';
  hoverable?: boolean;
}

const paddingMap = {
  sm: 'p-5',
  md: 'p-7',
  lg: 'p-10',
};

/**
 * Card — Double-Bezel (Doppelrand) architecture.
 *
 * Per high-end-visual-design directive Section 4.A:
 * - Outer Shell: subtle background, hairline ring, padding for the "tray" effect
 * - Inner Core: distinct bg, inner highlight shadow, concentric smaller radius
 * - Shadow: ultra-diffuse, tinted warm (< 0.05 opacity) per minimalist-skill
 * - Hover: subtle shadow shift + micro-translate, never just color change
 * - Border-radius: crisp 12px outer, 10px inner (concentric)
 * - No `shadow-md`, no `shadow-lg`, no harsh borders
 */
export default function Card({
  children,
  padding = 'md',
  hoverable = false,
  className = '',
  ...props
}: CardProps) {
  return (
    /* Outer Shell — the "aluminum tray" */
    <div
      className={[
        'rounded-[12px] p-[1px]',
        'bg-[var(--color-neutral-100)] dark:bg-[var(--color-neutral-800)]',
        'ring-1 ring-[var(--color-border)]',
        hoverable
          ? 'transition-all duration-500 ease-[cubic-bezier(0.32,0.72,0,1)] hover:-translate-y-[1px] hover:shadow-[0_4px_16px_rgba(0,0,0,0.04)]'
          : '',
        className,
      ].join(' ')}
      {...props}
    >
      {/* Inner Core — the "glass plate" */}
      <div
        className={[
          'rounded-[11px]',
          'bg-[var(--color-surface-alt)]',
          'shadow-[0_1px_3px_rgba(0,0,0,0.02),inset_0_1px_0_rgba(255,255,255,0.6)]',
          'dark:shadow-[0_1px_3px_rgba(0,0,0,0.1),inset_0_1px_0_rgba(255,255,255,0.04)]',
          paddingMap[padding],
        ].join(' ')}
      >
        {children}
      </div>
    </div>
  );
}

export type { CardProps };
