## 1. Setup

- [x] 1.1 Install Playwright and create config in project root
- [x] 1.2 Create e2e/ directory with helpers (login, API seed utilities)

## 2. Alumno Flow E2E

- [x] 2.1 Test: register → login → dashboard shows alumno sidebar
- [x] 2.2 Test: navigate to Mis Cursos, Actividades, Mi Progreso
- [x] 2.3 Test: write code → execute → see output (covered in alumno flow)
- [x] 2.4 Test: submit activity → reflection form → confirmation (covered in alumno flow)

## 3. Docente Flow E2E

- [x] 3.1 Test: login docente → courses → see course with commission and dashboard link
- [x] 3.2 Test: open dashboard with commission dropdown
- [x] 3.3 Test: alumno sees grade after docente confirms (covered in flow)

## 4. Security Tests

- [x] 4.1 Test: unauthenticated API request → 401
- [x] 4.2 Test: alumno accessing teacher/admin endpoint → 403

## 5. Smoke Test Script

- [x] 5.1 Create npm script to run all E2E tests with one command (`npm run test:e2e`)
