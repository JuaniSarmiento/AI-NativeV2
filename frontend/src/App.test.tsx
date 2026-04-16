import { render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from '@/App';
import { useAuthStore } from '@/features/auth/store';

function mockFetchResponse(ok: boolean, data: unknown) {
  return {
    ok,
    json: async () => data,
  } as unknown as Response;
}

describe('App', () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: null,
      user: null,
      isAuthenticated: false,
      isLoading: true,
    });

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mockFetchResponse(false, {})));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders without crashing', async () => {
    render(<App />);

    // Unauthenticated users are redirected to /login.
    expect(await screen.findByText('Iniciá sesión para continuar')).toBeInTheDocument();
  });

  it('renders the login page at root path when unauthenticated', async () => {
    render(<App />);

    expect(await screen.findByRole('button', { name: 'Iniciar sesión' })).toBeInTheDocument();
  });
});
