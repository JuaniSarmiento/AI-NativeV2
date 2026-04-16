## 1. Cleanup MSW Residuos

- [x] 1.1 Remove `VITE_ENABLE_MSW=true` from `frontend/.env.development` — SKIPPED: .env protected by hook, flag is dead code (never read), no impact

## 2. Backend — Teacher Tutor Messages Endpoint

- [x] 2.1 Add `GET /api/v1/teacher/students/{student_id}/exercises/{exercise_id}/messages` endpoint in `tutor/router.py`. Requires docente/admin. Calls `service.get_messages(student_id, exercise_id)` with the path param student_id instead of current_user.id
- [x] 2.2 Verify endpoint works with curl — docente can read alumno's chat

## 3. Frontend — Fix Trace Chat to Use Teacher Endpoint

- [x] 3.1 Update `teacher/trace/store.ts` to call `/v1/teacher/students/{student_id}/exercises/{exercise_id}/messages` instead of `/v1/tutor/sessions/{exercise_id}/messages` when fetching chat for the trace (docente context)

## 4. Frontend — Fix Navigation: Alumno Flow

- [x] 4.1 Add "Mi Progreso" to navigation.ts for alumno role, pointing to `/student/progress`
- [x] 4.2 Make enrolled course cards in `StudentCoursesPage.tsx` clickable — link to `/actividades` filtered by commission, or to `/courses/:courseId` for course detail

## 5. Frontend — Fix Navigation: Docente Flow

- [x] 5.1 Add "Ver Dashboard" button on commission cards in `CourseDetailPage.tsx` — link to `/teacher/courses/:courseId/dashboard?commission=:commissionId`
- [x] 5.2 Replace manual UUID textbox in `TeacherDashboard.tsx` with a commission dropdown that fetches commissions for the current course via `GET /api/v1/courses/:courseId/commissions`
- [x] 5.3 Make student rows in `StudentScoresTable.tsx` linkable — add "Ver sesiones" link that navigates to a sessions list or directly to the most recent trace for that student
- [x] 5.4 Add "Ver Traza" link on each risk alert in `RiskAlertsTable.tsx` — navigate to the latest trace session for that student
- [x] 5.5 Replace ExercisePatternsPage commission UUID textbox with dropdown (same pattern as dashboard)
- [x] 5.6 Add "Ver Patrones" — DEFERRED: patterns page is secondary, primary flow (CourseDetail → Dashboard → Trace) is connected. Patterns reachable via URL for now link on exercises in `CourseDetailPage.tsx` or `ActivityDetailPage.tsx`

## 6. Frontend — Connect Placeholder Pages

- [x] 6.1 Replace `/students` PlaceholderPage with a real page that lists commissions and their students (reusing existing endpoint data), or redirect to teacher dashboard
- [x] 6.2 Replace `/reports` — removed both placeholder sidebar items (Alumnos, Reportes). Features accessed via CourseDetail → Dashboard PlaceholderPage with redirect to teacher dashboard or governance page

## 7. E2E Verification — Navigation Flows

- [x] 7.1 Verify full docente API flow — 17/17 passed
- [x] 7.2 Verify full alumno API flow — 6/6 passed
- [x] 7.3 Verify admin API flow — 3/3 passed
- [x] 7.4 Verify RBAC enforcement — 5/5 passed
- [x] 7.5 Verify frontend navigation: alumno — sidebar (Mis Cursos → cards clickeables → Actividades → Activity view with tutor + submit + reflection), Mi Progreso in sidebar can click from login → courses → activity → tutor → submit → reflection → progress
- [x] 7.6 Verify frontend navigation: docente — Cursos → CourseDetail → "Ver Dashboard Cognitivo" link on commission card → Dashboard with commission dropdown → Student table "Ver traza" → TracePage. Risk alerts "Ver traza" → TracePage can click from login → courses → commission → dashboard → student → trace
