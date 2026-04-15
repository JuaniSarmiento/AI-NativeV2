import { useState, type FormEvent } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { useAuthStore } from './store';
import type { UserRole } from './types';

const ROLES: { value: UserRole; label: string; description: string }[] = [
  { value: 'alumno', label: 'Alumno', description: 'Accedé a ejercicios y tutoría IA' },
  { value: 'docente', label: 'Docente', description: 'Monitoreá el progreso cognitivo de tu comisión' },
];

export default function RegisterPage() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isLoading = useAuthStore((s) => s.isLoading);
  const register = useAuthStore((s) => s.register);
  const navigate = useNavigate();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<UserRole>('alumno');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated && !isLoading) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres.');
      return;
    }
    setSubmitting(true);
    try {
      await register({ email, password, full_name: fullName, role });
      navigate('/login', { replace: true });
    } catch {
      setError('No se pudo completar el registro. El email podria estar en uso.');
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
            El tutor que guia sin dar respuestas.
          </h1>
          <p className="mt-5 text-[1.0625rem] leading-relaxed text-[var(--color-neutral-400)]">
            Evaluamos tu razonamiento, no solo si tu codigo compila. Cada interaccion con la IA queda registrada en tu perfil cognitivo.
          </p>
        </div>
        <p className="text-[0.75rem] text-[var(--color-neutral-600)]">
          UTN FRM — Catedra de Programacion
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
              Crear cuenta
            </h2>
            <p className="mt-1.5 text-[0.9375rem] text-[var(--color-text-secondary)]">
              Registrate para acceder a la plataforma
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
                {/* Full name */}
                <div>
                  <label
                    htmlFor="fullName"
                    className="mb-1.5 block text-[0.8125rem] font-medium text-[var(--color-text-primary)]"
                  >
                    Nombre completo
                  </label>
                  <input
                    id="fullName"
                    type="text"
                    required
                    autoFocus
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Maria Gonzalez"
                    className="h-11 w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 text-[0.9375rem] text-[var(--color-text-primary)] outline-none transition-all duration-300 ease-[var(--ease-spring)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-accent-500)] focus:ring-2 focus:ring-[var(--color-accent-500)]/15"
                  />
                </div>

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
                    autoComplete="new-password"
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Minimo 8 caracteres"
                    className="h-11 w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 text-[0.9375rem] text-[var(--color-text-primary)] outline-none transition-all duration-300 ease-[var(--ease-spring)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-accent-500)] focus:ring-2 focus:ring-[var(--color-accent-500)]/15"
                  />
                </div>

                {/* Role selector — segmented control */}
                <div>
                  <label className="mb-2 block text-[0.8125rem] font-medium text-[var(--color-text-primary)]">
                    Rol
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    {ROLES.map((r) => (
                      <button
                        key={r.value}
                        type="button"
                        onClick={() => setRole(r.value)}
                        className={`group flex flex-col items-start rounded-[var(--radius-lg)] border p-3.5 text-left transition-all duration-300 ease-[var(--ease-spring)] ${
                          role === r.value
                            ? 'border-[var(--color-accent-500)] bg-[var(--color-accent-50)] ring-1 ring-[var(--color-accent-500)]/20 dark:bg-[var(--color-accent-900)]/10'
                            : 'border-[var(--color-border)] bg-[var(--color-surface)] hover:border-[var(--color-neutral-300)]'
                        }`}
                      >
                        <span
                          className={`text-[0.875rem] font-semibold ${
                            role === r.value
                              ? 'text-[var(--color-accent-700)] dark:text-[var(--color-accent-400)]'
                              : 'text-[var(--color-text-primary)]'
                          }`}
                        >
                          {r.label}
                        </span>
                        <span className="mt-0.5 text-[0.75rem] leading-snug text-[var(--color-text-tertiary)]">
                          {r.description}
                        </span>
                      </button>
                    ))}
                  </div>
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
                    Crear cuenta
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
            Ya tenes cuenta?{' '}
            <Link
              to="/login"
              className="font-medium text-[var(--color-accent-600)] transition-colors duration-300 hover:text-[var(--color-accent-700)]"
            >
              Inicia sesion
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
