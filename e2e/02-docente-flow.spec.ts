import { test, expect } from '@playwright/test';
import { registerUser, getToken, createCourse, createCommission, loginUI, logoutUI } from './helpers';

const TS = Date.now();
const DOCENTE_EMAIL = `docente-e2e-${TS}@test.com`;
const DOCENTE_PASS = 'Test1234!';
const DOCENTE_NAME = 'Docente E2E';

let courseId: string;
let commissionId: string;

test.describe('Docente Flow', () => {
  test.beforeAll(async () => {
    // Setup: register docente + create course + commission via API
    const user = await registerUser(DOCENTE_EMAIL, DOCENTE_PASS, DOCENTE_NAME, 'docente');
    const token = await getToken(DOCENTE_EMAIL, DOCENTE_PASS);
    const course = await createCourse(token, `Curso E2E ${TS}`);
    courseId = course.id;
    const commission = await createCommission(token, courseId, `K-${TS}`, user.id);
    commissionId = commission.id;
  });

  test('login and see docente sidebar', async ({ page }) => {
    await loginUI(page, DOCENTE_EMAIL, DOCENTE_PASS);

    await expect(page.getByText('Cursos')).toBeVisible();
    await expect(page.getByText('Configuracion')).toBeVisible();
    await expect(page.locator('header >> text=DOCENTE')).toBeVisible();
  });

  test('navigate to courses and see created course', async ({ page }) => {
    await loginUI(page, DOCENTE_EMAIL, DOCENTE_PASS);
    await page.getByRole('link', { name: 'Cursos' }).click();
    await expect(page.getByText(`Curso E2E ${TS}`)).toBeVisible();
  });

  test('open course and see commission with dashboard link', async ({ page }) => {
    await loginUI(page, DOCENTE_EMAIL, DOCENTE_PASS);
    await page.goto(`/courses/${courseId}`);
    await page.waitForTimeout(1000);

    await expect(page.getByText(`K-${TS}`)).toBeVisible();
    await expect(page.getByText('Ver Dashboard Cognitivo')).toBeVisible();
  });

  test('open dashboard with commission dropdown', async ({ page }) => {
    await loginUI(page, DOCENTE_EMAIL, DOCENTE_PASS);
    await page.goto(`/teacher/courses/${courseId}/dashboard?commission=${commissionId}`);
    await page.waitForTimeout(2000);

    await expect(page.getByText('Metricas de la Actividad')).toBeVisible();
    // Commission dropdown should be visible
    await expect(page.locator('select').first()).toBeVisible();
  });
});
