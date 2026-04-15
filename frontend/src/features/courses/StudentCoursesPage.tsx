import { useEffect, useState } from 'react';
import { useCoursesStore } from './store';
import Button from '@/shared/components/Button';
import Card from '@/shared/components/Card';
import type { Course, Commission } from './types';
import { apiClient } from '@/shared/lib/api-client';

export default function StudentCoursesPage() {
  const studentCourses = useCoursesStore((s) => s.studentCourses);
  const isLoading = useCoursesStore((s) => s.isLoading);
  const fetchStudentCourses = useCoursesStore((s) => s.fetchStudentCourses);
  const enroll = useCoursesStore((s) => s.enroll);

  const [allCourses, setAllCourses] = useState<Course[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<string | null>(null);
  const [commissions, setCommissions] = useState<Commission[]>([]);
  const [enrolling, setEnrolling] = useState<string | null>(null);

  useEffect(() => {
    fetchStudentCourses();
    apiClient.get<Course[]>('/v1/courses?page=1&per_page=50').then((res) => {
      setAllCourses(Array.isArray(res.data) ? res.data : []);
    });
  }, [fetchStudentCourses]);

  async function loadCommissions(courseId: string) {
    setSelectedCourse(courseId);
    const res = await apiClient.get<Commission[]>(
      `/v1/courses/${courseId}/commissions?page=1&per_page=50`,
    );
    setCommissions(Array.isArray(res.data) ? res.data : []);
  }

  async function handleEnroll(commissionId: string) {
    setEnrolling(commissionId);
    try {
      await enroll(commissionId);
      await fetchStudentCourses();
    } finally {
      setEnrolling(null);
    }
  }

  const enrolledCommissionIds = new Set(studentCourses.map((sc) => sc.commission_id));

  return (
    <div>
      {/* Header */}
      <span className="inline-block rounded-full bg-[var(--color-neutral-100)] px-3 py-1 text-[0.625rem] font-semibold uppercase tracking-[0.15em] text-[var(--color-text-secondary)] dark:bg-[var(--color-neutral-800)]">
        Mis cursos
      </span>
      <h1 className="mt-3 text-[1.75rem] font-bold tracking-tight text-[var(--color-text-primary)]">
        Cursos inscriptos
      </h1>

      {/* Enrolled courses */}
      {isLoading && studentCourses.length === 0 ? (
        <div className="mt-6 grid gap-3 md:grid-cols-2">
          {[0, 1].map((i) => (
            <div
              key={i}
              className="h-28 animate-pulse rounded-[12px] bg-[var(--color-neutral-100)] dark:bg-[var(--color-neutral-800)]"
            />
          ))}
        </div>
      ) : studentCourses.length === 0 ? (
        <Card padding="lg" className="mt-6">
          <div className="text-center py-6">
            <p className="text-[1.0625rem] font-medium text-[var(--color-text-primary)]">
              No estas inscripto en ningun curso
            </p>
            <p className="mt-1.5 text-[0.875rem] text-[var(--color-text-tertiary)]">
              Explora los cursos disponibles abajo y elegí una comision.
            </p>
          </div>
        </Card>
      ) : (
        <div className="mt-6 grid gap-3 md:grid-cols-2">
          {studentCourses.map((sc, i) => (
            <Card
              key={`${sc.commission_id}`}
              padding="md"
              className="animate-[slideIn_400ms_cubic-bezier(0.32,0.72,0,1)_both]"
              style={{ animationDelay: `${i * 60}ms` } as React.CSSProperties}
            >
              <p className="text-[0.9375rem] font-semibold text-[var(--color-text-primary)]">
                {sc.course_name}
              </p>
              <div className="mt-2 flex items-center gap-3 text-[0.8125rem] text-[var(--color-text-tertiary)]">
                <span>{sc.commission_name}</span>
                <span className="h-1 w-1 rounded-full bg-[var(--color-neutral-300)]" />
                <span>{sc.teacher_name}</span>
                <span className="h-1 w-1 rounded-full bg-[var(--color-neutral-300)]" />
                <span>{sc.year} S{sc.semester}</span>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Available courses for enrollment */}
      <div className="mt-12">
        <h2 className="text-[0.8125rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
          Cursos disponibles
        </h2>

        <div className="mt-4 divide-y divide-[var(--color-border)]">
          {allCourses.map((course) => (
            <div key={course.id} className="py-4">
              <button
                onClick={() => loadCommissions(course.id)}
                className="w-full text-left transition-colors duration-300"
              >
                <p className="text-[0.9375rem] font-semibold text-[var(--color-text-primary)]">
                  {course.name}
                </p>
                {course.description && (
                  <p className="mt-0.5 text-[0.8125rem] text-[var(--color-text-tertiary)]">
                    {course.description}
                  </p>
                )}
              </button>

              {/* Commissions dropdown */}
              {selectedCourse === course.id && commissions.length > 0 && (
                <div className="mt-3 space-y-2 pl-4 border-l-2 border-[var(--color-border)]">
                  {commissions.map((c) => {
                    const isEnrolled = enrolledCommissionIds.has(c.id);
                    return (
                      <div
                        key={c.id}
                        className="flex items-center justify-between rounded-[8px] bg-[var(--color-surface-alt)] px-4 py-3"
                      >
                        <div>
                          <p className="text-[0.875rem] font-medium text-[var(--color-text-primary)]">
                            {c.name}
                          </p>
                          <p className="text-[0.75rem] text-[var(--color-text-tertiary)]">
                            {c.year} — Semestre {c.semester}
                          </p>
                        </div>
                        {isEnrolled ? (
                          <span className="rounded-full bg-[#EDF3EC] px-2.5 py-0.5 text-[0.6875rem] font-semibold text-[#346538]">
                            Inscripto
                          </span>
                        ) : (
                          <Button
                            variant="primary"
                            size="sm"
                            loading={enrolling === c.id}
                            onClick={() => handleEnroll(c.id)}
                          >
                            Inscribirme
                          </Button>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
