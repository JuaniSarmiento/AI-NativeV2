import { useEffect, useState, type FormEvent } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useCoursesStore } from './store';
import { useAuthStore } from '@/features/auth/store';
import { apiClient } from '@/shared/lib/api-client';
import { useActivitiesStore } from '@/features/activities/store';
import Button from '@/shared/components/Button';
import Input from '@/shared/components/Input';
import Card from '@/shared/components/Card';
import Modal from '@/shared/components/Modal';
import type { Course, Commission } from './types';
import type { Activity } from '@/features/activities/types';

export default function CourseDetailPage() {
  const { courseId } = useParams<{ courseId: string }>();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const commissions = useCoursesStore((s) => s.commissions);
  const isLoading = useCoursesStore((s) => s.isLoading);
  const fetchCommissions = useCoursesStore((s) => s.fetchCommissions);
  const createCommission = useCoursesStore((s) => s.createCommission);
  const llmConfig = useActivitiesStore((s) => s.llmConfig);
  const fetchLLMConfig = useActivitiesStore((s) => s.fetchLLMConfig);
  const generateActivity = useActivitiesStore((s) => s.generateActivity);
  const isGenerating = useActivitiesStore((s) => s.isGenerating);

  const [course, setCourse] = useState<Course | null>(null);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [aiModalOpen, setAiModalOpen] = useState(false);
  const [aiPrompt, setAiPrompt] = useState('');
  const [aiError, setAiError] = useState<string | null>(null);
  const [formName, setFormName] = useState('');
  const [formYear, setFormYear] = useState(2026);
  const [formSemester, setFormSemester] = useState(1);
  const [submitting, setSubmitting] = useState(false);

  const canManage = user?.role === 'docente' || user?.role === 'admin';

  useEffect(() => {
    if (!courseId) return;
    apiClient.get<Course>(`/v1/courses/${courseId}`).then((res) => setCourse(res.data));
    fetchCommissions(courseId);
    fetchLLMConfig();
    // Fetch activities for this course
    apiClient.get<Activity[]>('/v1/activities').then((res) => {
      const all = Array.isArray(res.data) ? res.data : [];
      setActivities(all.filter((a) => a.course_id === courseId));
    });
  }, [courseId, fetchCommissions, fetchLLMConfig]);

  async function handleCreateCommission(e: FormEvent) {
    e.preventDefault();
    if (!courseId || !user) return;
    setSubmitting(true);
    try {
      await createCommission(courseId, {
        name: formName,
        teacher_id: user.id,
        year: formYear,
        semester: formSemester,
      });
      setModalOpen(false);
      setFormName('');
      await fetchCommissions(courseId);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGenerateActivity(e: FormEvent) {
    e.preventDefault();
    if (!courseId) return;
    setAiError(null);
    try {
      const activity = await generateActivity(courseId, aiPrompt);
      setAiModalOpen(false);
      setAiPrompt('');
      // Reload activities list
      apiClient.get<Activity[]>('/v1/activities').then((res) => {
        const all = Array.isArray(res.data) ? res.data : [];
        setActivities(all.filter((a) => a.course_id === courseId));
      });
      navigate(`/activities/${activity.id}`);
    } catch (err: any) {
      setAiError(err?.message || 'Error al generar. Verifica tu API key en Configuracion.');
    }
  }

  if (!course && !isLoading) {
    return (
      <div className="py-16 text-center">
        <p className="text-[var(--color-text-secondary)]">Curso no encontrado.</p>
        <Link to="/courses">
          <Button variant="secondary" size="sm" className="mt-4">Volver a cursos</Button>
        </Link>
      </div>
    );
  }

  return (
    <div>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-[0.8125rem] text-[var(--color-text-tertiary)]">
        <Link to="/courses" className="transition-colors duration-300 hover:text-[var(--color-text-primary)]">
          Cursos
        </Link>
        <span>/</span>
        <span className="text-[var(--color-text-primary)]">{course?.name ?? '...'}</span>
      </div>

      {/* Course header */}
      <div className="mt-6 flex items-start justify-between">
        <div>
          <h1 className="text-[1.75rem] font-bold tracking-tight text-[var(--color-text-primary)]">
            {course?.name}
          </h1>
          {course?.description && (
            <p className="mt-1.5 max-w-[55ch] text-[0.9375rem] leading-relaxed text-[var(--color-text-secondary)]">
              {course.description}
            </p>
          )}
        </div>
        {canManage && (
          <div className="flex gap-2 shrink-0">
            <Button variant="secondary" size="md" onClick={() => setModalOpen(true)}>
              Crear comision
            </Button>
          </div>
        )}
      </div>

      {/* Commissions */}
      <div className="mt-8">
        <h2 className="text-[0.8125rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
          Comisiones
        </h2>
        {commissions.length === 0 ? (
          <Card padding="md" className="mt-4">
            <div className="text-center py-6">
              <p className="text-[0.9375rem] font-medium text-[var(--color-text-primary)]">Sin comisiones</p>
              <p className="mt-1 text-[0.8125rem] text-[var(--color-text-tertiary)]">
                Este curso no tiene comisiones creadas todavia.
              </p>
            </div>
          </Card>
        ) : (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {commissions.map((c, i) => (
              <Card key={c.id} padding="md" hoverable
                className="animate-[slideIn_400ms_cubic-bezier(0.32,0.72,0,1)_both]"
                style={{ animationDelay: `${i * 60}ms` } as React.CSSProperties}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-[0.9375rem] font-semibold text-[var(--color-text-primary)]">{c.name}</p>
                    <p className="mt-1 text-[0.8125rem] text-[var(--color-text-tertiary)]">{c.year} — Semestre {c.semester}</p>
                  </div>
                  <span className="rounded-full bg-[var(--color-neutral-100)] px-2 py-0.5 text-[0.6875rem] font-medium text-[var(--color-text-secondary)] dark:bg-[var(--color-neutral-800)]">
                    Activa
                  </span>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Activities */}
      <div className="mt-12">
        <div className="flex items-center justify-between">
          <h2 className="text-[0.8125rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
            Actividades
          </h2>
          {canManage && courseId && (
            <Button variant="primary" size="sm" onClick={() => setAiModalOpen(true)}>
              Generar con IA
            </Button>
          )}
        </div>

        {activities.length === 0 ? (
          <Card padding="md" className="mt-4">
            <div className="text-center py-8">
              <p className="text-[1.0625rem] font-medium text-[var(--color-text-primary)]">
                Sin actividades
              </p>
              <p className="mt-1.5 text-[0.875rem] text-[var(--color-text-tertiary)]">
                Genera una actividad con IA. Cada actividad agrupa ejercicios que el alumno resuelve en orden.
              </p>
              {canManage && (
                <Button variant="primary" size="sm" className="mt-5" onClick={() => setAiModalOpen(true)}>
                  Generar primera actividad
                </Button>
              )}
            </div>
          </Card>
        ) : (
          <div className="mt-4 space-y-3">
            {activities.map((a, i) => (
              <Link
                key={a.id}
                to={`/activities/${a.id}`}
                className="block animate-[slideIn_400ms_cubic-bezier(0.32,0.72,0,1)_both]"
                style={{ animationDelay: `${i * 60}ms` }}
              >
                <Card padding="md" hoverable>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-[0.9375rem] font-semibold text-[var(--color-text-primary)]">
                          {a.title}
                        </p>
                        <span
                          className={`rounded-full px-2 py-0.5 text-[0.625rem] font-semibold uppercase tracking-wider ${
                            a.status === 'draft'
                              ? 'bg-[#FBF3DB] text-[#956400]'
                              : 'bg-[#EDF3EC] text-[#346538]'
                          }`}
                        >
                          {a.status}
                        </span>
                      </div>
                      {a.description && (
                        <p className="mt-1 text-[0.8125rem] text-[var(--color-text-tertiary)] line-clamp-1">
                          {a.description}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0 ml-4">
                      <span className="text-[0.75rem] font-mono text-[var(--color-text-tertiary)]">
                        {a.exercises?.length ?? 0} ej.
                      </span>
                      <svg className="h-4 w-4 text-[var(--color-text-tertiary)]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                      </svg>
                    </div>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* AI Generation Modal */}
      <Modal open={aiModalOpen} onClose={() => { setAiModalOpen(false); setAiError(null); }} title="Generar actividad con IA" maxWidth="max-w-xl">
        {!llmConfig?.has_key ? (
          <div className="text-center py-4">
            <p className="text-[0.9375rem] font-medium text-[var(--color-text-primary)]">
              Necesitas configurar tu API key
            </p>
            <p className="mt-1.5 text-[0.8125rem] text-[var(--color-text-tertiary)]">
              Anda a Configuracion para agregar tu clave.
            </p>
            <Button variant="primary" size="sm" className="mt-4" onClick={() => navigate('/settings')}>
              Ir a Configuracion
            </Button>
          </div>
        ) : (
          <form onSubmit={handleGenerateActivity} className="space-y-4">
            <div className="space-y-1.5">
              <label className="block text-[0.8125rem] font-medium text-[var(--color-text-primary)]">
                Describe la actividad que queres generar
              </label>
              <textarea
                required
                rows={4}
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                placeholder="Ej: Creame 3 ejercicios sobre funciones y listas, de dificultad progresiva. Que incluyan test cases ejecutables con input por stdin y output por stdout."
                className="w-full rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 text-[0.9375rem] text-[var(--color-text-primary)] outline-none transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-neutral-400)] focus:ring-2 focus:ring-[var(--color-neutral-400)]/10"
              />
              <p className="text-[0.75rem] text-[var(--color-text-tertiary)]">
                Usando: {llmConfig.provider} / {llmConfig.model_name} — con material de la catedra
              </p>
            </div>

            {aiError && (
              <div className="rounded-[8px] border border-[#9F2F2D]/20 bg-[#FDEBEC] px-4 py-3 text-[0.8125rem] text-[#9F2F2D]">
                {aiError}
              </div>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <Button variant="ghost" size="md" type="button" onClick={() => setAiModalOpen(false)}>
                Cancelar
              </Button>
              <Button variant="primary" size="md" type="submit" loading={isGenerating} disabled={!aiPrompt.trim()}>
                {isGenerating ? 'Generando...' : 'Generar actividad'}
              </Button>
            </div>
          </form>
        )}
      </Modal>

      {/* Create commission modal */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Crear comision">
        <form onSubmit={handleCreateCommission} className="space-y-4">
          <Input label="Nombre" placeholder="K1001" required value={formName} onChange={(e) => setFormName(e.target.value)} />
          <div className="grid grid-cols-2 gap-3">
            <Input label="Anio" type="number" min={2020} max={2100} required value={String(formYear)} onChange={(e) => setFormYear(Number(e.target.value))} />
            <Input label="Semestre" type="number" min={1} max={2} required value={String(formSemester)} onChange={(e) => setFormSemester(Number(e.target.value))} />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" size="md" type="button" onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button variant="primary" size="md" type="submit" loading={submitting}>Crear</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
