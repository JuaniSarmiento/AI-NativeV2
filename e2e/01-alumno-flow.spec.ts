import { test, expect } from '@playwright/test';
import { registerUser, loginUI } from './helpers';

const TS = Date.now();
const ALUMNO_EMAIL = `alumno-e2e-${TS}@test.com`;
const ALUMNO_PASS = 'Test1234!';
const ALUMNO_NAME = 'Alumno E2E';

test.describe('Alumno Flow', () => {
  test.beforeAll(async () => {
    await registerUser(ALUMNO_EMAIL, ALUMNO_PASS, ALUMNO_NAME, 'alumno');
  });

  test('login and see alumno sidebar', async ({ page }) => {
    await loginUI(page, ALUMNO_EMAIL, ALUMNO_PASS);

    await expect(page.getByText('Mis Cursos')).toBeVisible();
    await expect(page.getByText('Actividades')).toBeVisible();
    await expect(page.getByText('Mi Progreso')).toBeVisible();
    await expect(page.locator('header >> text=ALUMNO')).toBeVisible();
  });

  test('navigate to Mis Cursos', async ({ page }) => {
    await loginUI(page, ALUMNO_EMAIL, ALUMNO_PASS);
    await page.getByRole('link', { name: 'Mis Cursos' }).click();
    await expect(page.getByText('Cursos inscriptos')).toBeVisible();
  });

  test('navigate to Actividades', async ({ page }) => {
    await loginUI(page, ALUMNO_EMAIL, ALUMNO_PASS);
    await page.getByRole('link', { name: 'Actividades' }).click();
    await page.waitForTimeout(1000);
    await expect(page.locator('main')).toBeVisible();
  });

  test('navigate to Mi Progreso', async ({ page }) => {
    await loginUI(page, ALUMNO_EMAIL, ALUMNO_PASS);
    await page.getByRole('link', { name: 'Mi Progreso' }).click();
    await page.waitForTimeout(1000);
    await expect(page.locator('main')).toBeVisible();
  });
});
