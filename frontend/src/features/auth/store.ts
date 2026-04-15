import { create } from 'zustand';
import { config } from '@/config';
import { apiClient, setTokenProvider } from '@/shared/lib/api-client';
import type { AuthUser, LoginCredentials, RegisterData, TokenResponse } from './types';

interface AuthState {
  accessToken: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<boolean>;
  initialize: () => Promise<void>;
  setFromTokenResponse: (data: TokenResponse) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => {
  // Wire up the token provider for apiClient
  setTokenProvider(() => get().accessToken);

  return {
    accessToken: null,
    user: null,
    isAuthenticated: false,
    isLoading: true,

    setFromTokenResponse: (data: TokenResponse) => {
      set({
        accessToken: data.access_token,
        user: {
          id: data.user.id,
          email: data.user.email,
          fullName: data.user.full_name,
          role: data.user.role,
        },
        isAuthenticated: true,
        isLoading: false,
      });
    },

    clearAuth: () => {
      set({
        accessToken: null,
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });
    },

    login: async (credentials: LoginCredentials) => {
      set({ isLoading: true });
      try {
        const res = await apiClient.post<TokenResponse>(
          '/v1/auth/login',
          credentials,
        );
        get().setFromTokenResponse(res.data);
      } catch {
        get().clearAuth();
        throw new Error('Login failed');
      }
    },

    register: async (data: RegisterData) => {
      await apiClient.post('/v1/auth/register', data);
    },

    logout: async () => {
      try {
        await apiClient.post('/v1/auth/logout', {});
      } catch {
        // Logout should succeed even if the API call fails
      }
      get().clearAuth();
    },

    refresh: async (): Promise<boolean> => {
      try {
        const res = await fetch(`${config.apiUrl}/v1/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
        });

        if (!res.ok) return false;

        const json = await res.json();
        get().setFromTokenResponse(json.data);
        return true;
      } catch {
        return false;
      }
    },

    initialize: async () => {
      set({ isLoading: true });
      const success = await get().refresh();
      if (!success) {
        get().clearAuth();
      }
    },
  };
});
