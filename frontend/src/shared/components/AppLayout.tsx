import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { useAuthStore } from '@/features/auth/store';
import { getNavItemsForRole } from '@/shared/lib/navigation';

/**
 * AppLayout — Premium utilitarian shell.
 *
 * Follows taste-skill + high-end-visual-design + minimalist-skill:
 * - Sidebar: fixed desktop, spring drawer on mobile with staggered nav items
 * - Hamburger: morphs to X with rotate transforms (not just disappear)
 * - Active nav: muted pastel bg from minimalist-skill palette
 * - Backdrop: blur on fixed overlay only (performance guardrail)
 * - All transitions: cubic-bezier(0.32, 0.72, 0, 1) — spring physics
 * - Border: 1px solid theme token, no `shadow-md`
 * - Spacing: generous, editorial
 */
export default function AppLayout() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const items = user ? getNavItemsForRole(user.role) : [];

  return (
    <div className="flex min-h-[100dvh] bg-[var(--color-surface)]">
      {/* ----------------------------------------------------------------
          Mobile backdrop — blur on fixed element only
          ---------------------------------------------------------------- */}
      {drawerOpen && (
        <div
          className="fixed inset-0 z-30 bg-[var(--color-neutral-950)]/40 backdrop-blur-sm md:hidden animate-[fadeIn_150ms_ease-out]"
          onClick={() => setDrawerOpen(false)}
          aria-hidden
        />
      )}

      {/* ----------------------------------------------------------------
          Sidebar
          ---------------------------------------------------------------- */}
      <aside
        className={[
          'fixed inset-y-0 left-0 z-40 flex w-[256px] flex-col',
          'border-r border-[var(--color-border)]',
          'bg-[var(--color-surface-alt)]',
          'transition-transform duration-500 ease-[cubic-bezier(0.32,0.72,0,1)]',
          'md:static md:translate-x-0',
          drawerOpen ? 'translate-x-0' : '-translate-x-full',
        ].join(' ')}
      >
        {/* Logo bar */}
        <div className="flex h-14 shrink-0 items-center border-b border-[var(--color-border)] px-5">
          <span className="text-[0.6875rem] font-bold tracking-[0.18em] uppercase text-[var(--color-text-tertiary)]">
            AI-Native
          </span>
        </div>

        {/* Navigation — staggered appearance via CSS cascade */}
        <nav className="flex-1 space-y-0.5 px-3 py-4">
          {items.map((item, i) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              onClick={() => setDrawerOpen(false)}
              style={{ animationDelay: `${i * 50}ms` }}
              className={({ isActive }) =>
                [
                  'flex h-9 items-center rounded-[6px] px-3',
                  'text-[0.8125rem] font-medium',
                  'transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]',
                  'animate-[slideIn_400ms_cubic-bezier(0.32,0.72,0,1)_both]',
                  isActive
                    ? 'bg-[var(--color-neutral-100)] text-[var(--color-text-primary)] dark:bg-[var(--color-neutral-800)]'
                    : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-neutral-50)] hover:text-[var(--color-text-primary)] dark:hover:bg-[var(--color-neutral-800)]/50',
                ].join(' ')
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* User footer */}
        <div className="border-t border-[var(--color-border)] px-4 py-3">
          <div className="flex items-center gap-3">
            {/* Avatar circle — initials, not generic icon (per taste-skill anti-pattern) */}
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--color-neutral-100)] text-[0.6875rem] font-bold uppercase text-[var(--color-text-secondary)] dark:bg-[var(--color-neutral-800)]">
              {user?.fullName
                ?.split(' ')
                .map((n) => n[0])
                .slice(0, 2)
                .join('')}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[0.8125rem] font-medium text-[var(--color-text-primary)]">
                {user?.fullName}
              </p>
              <p className="truncate text-[0.6875rem] text-[var(--color-text-tertiary)]">
                {user?.role}
              </p>
            </div>
            <button
              onClick={() => logout()}
              className="shrink-0 rounded-[6px] p-1.5 text-[var(--color-text-tertiary)] transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] hover:bg-[var(--color-neutral-100)] hover:text-[var(--color-text-primary)] active:scale-[0.92] dark:hover:bg-[var(--color-neutral-800)]"
              aria-label="Cerrar sesion"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9"
                />
              </svg>
            </button>
          </div>
        </div>
      </aside>

      {/* ----------------------------------------------------------------
          Main area
          ---------------------------------------------------------------- */}
      <div className="flex flex-1 flex-col">
        {/* Header */}
        <header className="flex h-14 shrink-0 items-center border-b border-[var(--color-border)] px-4 md:px-6">
          {/* Hamburger — morphs lines to X via rotate transforms (per high-end directive) */}
          <button
            onClick={() => setDrawerOpen((prev) => !prev)}
            className="relative mr-3 flex h-8 w-8 flex-col items-center justify-center gap-[5px] rounded-[6px] text-[var(--color-text-secondary)] transition-colors duration-200 hover:bg-[var(--color-neutral-100)] md:hidden dark:hover:bg-[var(--color-neutral-800)]"
            aria-label={drawerOpen ? 'Cerrar menu' : 'Abrir menu'}
          >
            <span
              className={[
                'block h-[1.5px] w-4 rounded-full bg-current',
                'transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]',
                'origin-center',
                drawerOpen ? 'translate-y-[3.25px] rotate-45' : '',
              ].join(' ')}
            />
            <span
              className={[
                'block h-[1.5px] w-4 rounded-full bg-current',
                'transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]',
                'origin-center',
                drawerOpen ? '-translate-y-[3.25px] -rotate-45' : '',
              ].join(' ')}
            />
          </button>

          <div className="flex-1" />

          {/* Role badge — pill, uppercase, wide tracking (per taste-skill eyebrow tag) */}
          <span className="rounded-full bg-[var(--color-neutral-100)] px-2.5 py-[3px] text-[0.625rem] font-semibold uppercase tracking-[0.12em] text-[var(--color-text-secondary)] dark:bg-[var(--color-neutral-800)]">
            {user?.role}
          </span>
        </header>

        {/* Content — generous editorial padding */}
        <main className="flex-1 overflow-y-auto px-4 py-8 md:px-10 md:py-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
