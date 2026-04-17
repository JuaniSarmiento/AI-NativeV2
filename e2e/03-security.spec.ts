import { test, expect } from '@playwright/test';
import { registerUser, getToken, apiRequest } from './helpers';

const TS = Date.now();
const ALUMNO_EMAIL = `sec-alumno-${TS}@test.com`;
const ALUMNO_PASS = 'Test1234!';

test.describe('Security Tests', () => {
  test.beforeAll(async () => {
    await registerUser(ALUMNO_EMAIL, ALUMNO_PASS, 'Security Alumno', 'alumno');
  });

  test('unauthenticated request returns 401', async () => {
    const res = await fetch('http://localhost:8001/api/v1/courses', {
      headers: { Authorization: 'Bearer invalid-token' },
    });
    expect(res.status).toBe(401);
  });

  test('alumno cannot access teacher endpoints (403)', async () => {
    const token = await getToken(ALUMNO_EMAIL, ALUMNO_PASS);

    const { status: risksStatus } = await apiRequest(
      token, 'GET', '/teacher/commissions/00000000-0000-0000-0000-000000000001/risks',
    );
    expect(risksStatus).toBe(403);

    const { status: sessionsStatus } = await apiRequest(
      token, 'GET', '/cognitive/sessions?commission_id=00000000-0000-0000-0000-000000000001',
    );
    expect(sessionsStatus).toBe(403);
  });

  test('alumno cannot access admin endpoints (403)', async () => {
    const token = await getToken(ALUMNO_EMAIL, ALUMNO_PASS);

    const { status: govStatus } = await apiRequest(token, 'GET', '/governance/events');
    expect(govStatus).toBe(403);

    const { status: promptsStatus } = await apiRequest(token, 'GET', '/governance/prompts');
    expect(promptsStatus).toBe(403);
  });

  test('login page is accessible without auth', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByText('Iniciar sesión')).toBeVisible();
  });

  test('protected routes redirect to login', async ({ page }) => {
    // Clear any existing session
    await page.context().clearCookies();
    await page.goto('/courses');
    await page.waitForTimeout(2000);
    // Should redirect to login
    expect(page.url()).toContain('/login');
  });
});
