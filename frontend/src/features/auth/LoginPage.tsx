import { useState, type FormEvent } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { useAuthStore } from './store';

export default function LoginPage() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isLoading = useAuthStore((s) => s.isLoading);
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated && !isLoading) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login({ email, password });
      navigate('/', { replace: true });
    } catch {
      setError('Credenciales incorrectas. Revisá tu email y contraseña.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid min-h-[100dvh] md:grid-cols-2">
      {/* Left — Brand panel */}
      <div className="hidden md:flex flex-col justify-between bg-[var(--color-neutral-950)] px-12 py-10">
        <div>
          <span className="text-[0.8125rem] font-semibold tracking-[0.15em] uppercase text-[var(--color-neutral-400)]">
            AI-Native
          </span>
        </div>
        <div className="max-w-[420px]">
          <h1 className="text-[2.75rem] font-bold leading-[1.1] tracking-tight text-white">
            Aprendé a programar con inteligencia artificial socrática.
          </h1>
          <p className="mt-5 text-[1.0625rem] leading-relaxed text-[var(--color-neutral-400)]">
            La plataforma que observa tu proceso cognitivo, no solo tu código final.
          </p>
        </div>
        <p className="text-[0.75rem] text-[var(--color-neutral-600)]">
          UTN FRM — Cátedra de Programación
        </p>
      </div>

      {/* Right — Form panel */}
      <div className="flex flex-col items-center justify-center px-6 py-12 md:px-16 bg-[var(--color-surface)]">
        {/* Mobile logo */}
        <div className="mb-10 md:hidden">
          <span className="text-[0.75rem] font-semibold tracking-[0.15em] uppercase text-[var(--color-text-tertiary)]">
            AI-Native
          </span>
        </div>

        <div className="w-full max-w-[380px]">
          <div className="mb-8">
            <h2 className="text-[1.75rem] font-bold tracking-tight text-[var(--color-text-primary)]">
              Iniciar sesión
            </h2>
            <p className="mt-1.5 text-[0.9375rem] text-[var(--color-text-secondary)]">
              Ingresá tus credenciales para continuar
            </p>
          </div>

          {/* Form — Double-Bezel container */}
          <div className="rounded-[var(--radius-2xl)] bg-[var(--color-border-subtle)] p-[1px] ring-1 ring-[var(--color-border)]">
            <form
              onSubmit={handleSubmit}
              className="rounded-[calc(var(--radius-2xl)-1px)] bg-[var(--color-surface-alt)] p-7 shadow-[0_20px_40px_-15px_rgba(0,0,0,0.04)]"
            >
              {error && (
                <div className="mb-5 rounded-[var(--radius-md)] border border-red-200 bg-red-50 px-4 py-3 text-[0.8125rem] text-red-600 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-400">
                  {error}
                </div>
              )}

              <div className="space-y-4">
                {/* Email */}
                <div>
                  <label
                    htmlFor="email"
                    className="mb-1.5 block text-[0.8125rem] font-medium text-[var(--color-text-primary)]"
                  >
                    Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    required
                    autoComplete="email"
                    autoFocus
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="nombre@universidad.edu"
                    className="h-11 w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 text-[0.9375rem] text-[var(--color-text-primary)] outline-none transition-all duration-300 ease-[var(--ease-spring)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-accent-500)] focus:ring-2 focus:ring-[var(--color-accent-500)]/15"
                  />
                </div>

                {/* Password */}
                <div>
                  <label
                    htmlFor="password"
                    className="mb-1.5 block text-[0.8125rem] font-medium text-[var(--color-text-primary)]"
                  >
                    Contraseña
                  </label>
                  <input
                    id="password"
                    type="password"
                    required
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;"
                    className="h-11 w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 text-[0.9375rem] text-[var(--color-text-primary)] outline-none transition-all duration-300 ease-[var(--ease-spring)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-accent-500)] focus:ring-2 focus:ring-[var(--color-accent-500)]/15"
                  />
                </div>
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={submitting}
                className="group mt-6 flex h-11 w-full items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--color-accent-600)] text-[0.9375rem] font-semibold text-white transition-all duration-500 ease-[var(--ease-out-expo)] hover:bg-[var(--color-accent-700)] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {submitting ? (
                  <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                ) : (
                  <>
                    Continuar
                    <svg
                      className="h-4 w-4 transition-transform duration-500 ease-[var(--ease-out-expo)] group-hover:translate-x-0.5"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={2}
                      stroke="currentColor"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                    </svg>
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Footer */}
          <p className="mt-6 text-center text-[0.8125rem] text-[var(--color-text-secondary)]">
            Sin cuenta?{' '}
            <Link
              to="/register"
              className="font-medium text-[var(--color-accent-600)] transition-colors duration-300 hover:text-[var(--color-accent-700)]"
            >
              Registrate
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
