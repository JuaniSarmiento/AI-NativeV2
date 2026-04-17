import { type Page, expect } from '@playwright/test';

const API = 'http://localhost:8001/api/v1';

/** Register a user via API and return the user data */
export async function registerUser(
  email: string,
  password: string,
  fullName: string,
  role: 'alumno' | 'docente' | 'admin',
) {
  const res = await fetch(`${API}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: fullName, role }),
  });
  const json = await res.json();
  return json.data;
}

/** Login via API and return the access_token */
export async function getToken(email: string, password: string): Promise<string> {
  const res = await fetch(`${API}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const json = await res.json();
  return json.data.access_token;
}

/** Create a course via API */
export async function createCourse(token: string, name: string) {
  const res = await fetch(`${API}/courses`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ name, description: 'E2E test course' }),
  });
  return (await res.json()).data;
}

/** Create a commission via API */
export async function createCommission(token: string, courseId: string, name: string, teacherId: string) {
  const res = await fetch(`${API}/courses/${courseId}/commissions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ name, year: 2026, semester: 1, teacher_id: teacherId }),
  });
  const json = await res.json();
  return json.data;
}

/** Enroll student in commission */
export async function enrollStudent(token: string, commissionId: string) {
  const res = await fetch(`${API}/commissions/${commissionId}/enroll`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
  return (await res.json());
}

/** Login via the UI */
export async function loginUI(page: Page, email: string, password: string) {
  await page.goto('/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Contraseña').fill(password);
  await page.getByRole('button', { name: 'Continuar' }).click();
  await page.waitForURL('/');
  await expect(page.getByText('Bienvenido')).toBeVisible();
}

/** Logout via the UI */
export async function logoutUI(page: Page) {
  await page.getByRole('button', { name: 'Cerrar sesion' }).click();
  await page.waitForURL('/login');
}

/** Make an authenticated API request */
export async function apiRequest(
  token: string,
  method: string,
  path: string,
  body?: unknown,
) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  return { status: res.status, json: await res.json() };
}
