import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import LoginPage from '@/features/auth/LoginPage';
import RegisterPage from '@/features/auth/RegisterPage';
import ProtectedRoute from '@/features/auth/ProtectedRoute';
import AppLayout from '@/shared/components/AppLayout';
import { useAuthStore } from '@/features/auth/store';
import CoursesPage from '@/features/courses/CoursesPage';
import CourseDetailPage from '@/features/courses/CourseDetailPage';
import StudentCoursesPage from '@/features/courses/StudentCoursesPage';
import ExerciseDetailPage from '@/features/exercises/ExerciseDetailPage';
import ActivityDetailPage from '@/features/activities/ActivityDetailPage';
import StudentActivitiesPage from '@/features/activities/StudentActivitiesPage';
import StudentActivityViewPage from '@/features/activities/StudentActivityViewPage';
import SettingsLLMPage from '@/features/activities/SettingsLLMPage';
import TeacherDashboard from '@/features/teacher/dashboard/TeacherDashboard';
import TracePage from '@/features/teacher/trace/TracePage';
import ExercisePatternsPage from '@/features/teacher/patterns/ExercisePatternsPage';
import GovernanceReportsPage from '@/features/teacher/governance/GovernanceReportsPage';
import GradingPage from '@/features/teacher/grading/GradingPage';
import StudentProgress from '@/features/student/progress/StudentProgress';

/* ---------------------------------------------------------------
   Placeholder pages — replaced by real features in future EPICs
   --------------------------------------------------------------- */

function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  return (
    <div>
      <span className="inline-block rounded-full bg-[var(--color-accent-50)] px-3 py-1 text-[0.6875rem] font-semibold uppercase tracking-[0.15em] text-[var(--color-accent-700)] dark:bg-[var(--color-accent-900)]/20 dark:text-[var(--color-accent-400)]">
        Dashboard
      </span>
      <h1 className="mt-4 text-[1.75rem] font-bold tracking-tight text-[var(--color-text-primary)]">
        Bienvenido, {user?.fullName?.split(' ')[0]}
      </h1>
      <p className="mt-2 max-w-[50ch] text-[0.9375rem] leading-relaxed text-[var(--color-text-secondary)]">
        Esta seccion se va a expandir con el dashboard de tu rol. Por ahora, tu sesion esta activa.
      </p>
    </div>
  );
}

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div>
      <h1 className="text-[1.75rem] font-bold tracking-tight text-[var(--color-text-primary)]">
        {title}
      </h1>
      <p className="mt-2 text-[0.9375rem] text-[var(--color-text-secondary)]">
        Proximamente.
      </p>
    </div>
  );
}

function CoursesRouteSwitch() {
  const role = useAuthStore((s) => s.user?.role);
  if (role === 'alumno') return <StudentCoursesPage />;
  return <CoursesPage />;
}

function NotFoundPage() {
  return (
    <div className="flex min-h-[100dvh] flex-col items-center justify-center bg-[var(--color-surface)] px-6">
      <span className="text-[6rem] font-bold leading-none tracking-tighter text-[var(--color-neutral-200)]">
        404
      </span>
      <p className="mt-3 text-[1.0625rem] text-[var(--color-text-secondary)]">
        Esta pagina no existe.
      </p>
      <a
        href="/"
        className="mt-6 rounded-[var(--radius-md)] bg-[var(--color-accent-600)] px-5 py-2.5 text-[0.875rem] font-semibold text-white transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-[var(--color-accent-700)] active:scale-[0.98]"
      >
        Volver al inicio
      </a>
    </div>
  );
}

/* ---------------------------------------------------------------
   App root
   --------------------------------------------------------------- */

export default function App() {
  const initialize = useAuthStore((s) => s.initialize);

  useEffect(() => {
    initialize();
  }, [initialize]);

  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Protected — inside App Shell */}
        <Route
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="courses" element={<CoursesRouteSwitch />} />
          <Route path="courses/:courseId" element={<CourseDetailPage />} />
          <Route path="actividades" element={<StudentActivitiesPage />} />
          <Route path="actividades/:activityId" element={<StudentActivityViewPage />} />
          <Route path="activities/:activityId" element={<ActivityDetailPage />} />
          <Route path="exercises/:exerciseId" element={<ExerciseDetailPage />} />
          <Route path="teacher/courses/:courseId/dashboard" element={<TeacherDashboard />} />
          <Route path="teacher/trace/:sessionId" element={<TracePage />} />
          <Route path="teacher/courses/:courseId/exercises/:exerciseId/patterns" element={<ExercisePatternsPage />} />
          <Route path="teacher/activities/:activityId/grading" element={<GradingPage />} />
          <Route path="admin/governance" element={<GovernanceReportsPage />} />
          <Route path="student/progress" element={<StudentProgress />} />
          <Route path="students" element={<PlaceholderPage title="Alumnos" />} />
          <Route path="reports" element={<PlaceholderPage title="Reportes" />} />
          <Route path="settings" element={<SettingsLLMPage />} />
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}
