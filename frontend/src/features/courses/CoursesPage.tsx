import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useCoursesStore } from './store';
import { useAuthStore } from '@/features/auth/store';
import Button from '@/shared/components/Button';
import Input from '@/shared/components/Input';
import Card from '@/shared/components/Card';
import Modal from '@/shared/components/Modal';
import type { Course, CourseCreateData } from './types';

export default function CoursesPage() {
  const role = useAuthStore((s) => s.user?.role);
  const courses = useCoursesStore((s) => s.courses);
  const isLoading = useCoursesStore((s) => s.isLoading);
  const fetchCourses = useCoursesStore((s) => s.fetchCourses);
  const createCourse = useCoursesStore((s) => s.createCourse);
  const deleteCourse = useCoursesStore((s) => s.deleteCourse);

  const [modalOpen, setModalOpen] = useState(false);
  const [formName, setFormName] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const isAdmin = role === 'admin';
  const canManage = role === 'docente' || isAdmin;

  useEffect(() => {
    fetchCourses();
  }, [fetchCourses]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await createCourse({ name: formName, description: formDesc || undefined });
      setModalOpen(false);
      setFormName('');
      setFormDesc('');
      await fetchCourses();
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: string) {
    await deleteCourse(id);
    await fetchCourses();
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <span className="inline-block rounded-full bg-[var(--color-neutral-100)] px-3 py-1 text-[0.625rem] font-semibold uppercase tracking-[0.15em] text-[var(--color-text-secondary)] dark:bg-[var(--color-neutral-800)]">
            Gestion academica
          </span>
          <h1 className="mt-3 text-[1.75rem] font-bold tracking-tight text-[var(--color-text-primary)]">
            Cursos
          </h1>
        </div>
        {canManage && (
          <Button
            variant="primary"
            size="md"
            onClick={() => setModalOpen(true)}
            icon={
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
            }
            iconPosition="left"
          >
            Crear curso
          </Button>
        )}
      </div>

      {/* Course list — table with border-bottom separators (minimalist-skill: no cards for tabular data) */}
      <div className="mt-8">
        {isLoading && courses.length === 0 ? (
          /* Skeleton loader */
          <div className="space-y-0">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="flex items-center justify-between border-b border-[var(--color-border)] py-5"
                style={{ animationDelay: `${i * 80}ms` }}
              >
                <div className="space-y-2">
                  <div className="h-4 w-48 animate-pulse rounded bg-[var(--color-neutral-100)] dark:bg-[var(--color-neutral-800)]" />
                  <div className="h-3 w-72 animate-pulse rounded bg-[var(--color-neutral-50)] dark:bg-[var(--color-neutral-800)]/50" />
                </div>
                <div className="h-8 w-16 animate-pulse rounded bg-[var(--color-neutral-100)] dark:bg-[var(--color-neutral-800)]" />
              </div>
            ))}
          </div>
        ) : courses.length === 0 ? (
          /* Empty state */
          <Card padding="lg">
            <div className="text-center py-8">
              <p className="text-[1.0625rem] font-medium text-[var(--color-text-primary)]">
                No hay cursos creados
              </p>
              <p className="mt-1.5 text-[0.875rem] text-[var(--color-text-tertiary)]">
                {canManage
                  ? 'Crea el primer curso para empezar a organizar comisiones y ejercicios.'
                  : 'Todavia no hay cursos disponibles.'}
              </p>
              {canManage && (
                <Button
                  variant="secondary"
                  size="sm"
                  className="mt-5"
                  onClick={() => setModalOpen(true)}
                >
                  Crear primer curso
                </Button>
              )}
            </div>
          </Card>
        ) : (
          <div className="divide-y divide-[var(--color-border)]">
            {courses.map((course, i) => (
              <div
                key={course.id}
                className="flex items-center justify-between py-5 animate-[slideIn_400ms_cubic-bezier(0.32,0.72,0,1)_both]"
                style={{ animationDelay: `${i * 60}ms` }}
              >
                <Link
                  to={`/courses/${course.id}`}
                  className="group min-w-0 flex-1"
                >
                  <p className="text-[0.9375rem] font-semibold text-[var(--color-text-primary)] transition-colors duration-300 group-hover:text-[var(--color-accent-600)]">
                    {course.name}
                  </p>
                  {course.description && (
                    <p className="mt-0.5 truncate text-[0.8125rem] text-[var(--color-text-tertiary)]">
                      {course.description}
                    </p>
                  )}
                </Link>
                <div className="ml-4 flex items-center gap-2 shrink-0">
                  {isAdmin && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(course.id)}
                    >
                      Eliminar
                    </Button>
                  )}
                  <Link to={`/courses/${course.id}`}>
                    <Button variant="secondary" size="sm">
                      Ver
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create modal */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Crear curso">
        <form onSubmit={handleCreate} className="space-y-4">
          <Input
            label="Nombre del curso"
            placeholder="Programacion I"
            required
            value={formName}
            onChange={(e) => setFormName(e.target.value)}
          />
          <Input
            label="Descripcion"
            placeholder="Breve descripcion del curso (opcional)"
            value={formDesc}
            onChange={(e) => setFormDesc(e.target.value)}
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" size="md" type="button" onClick={() => setModalOpen(false)}>
              Cancelar
            </Button>
            <Button variant="primary" size="md" type="submit" loading={submitting}>
              Crear
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
