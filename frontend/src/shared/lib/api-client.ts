import { config } from '@/config';
import { createLogger } from '@/shared/lib/logger';
import type { ApiResponse } from '@/shared/types/api';

const logger = createLogger('api-client');

/** Token provider — replaced at auth store init */
let getAccessToken: () => string | null = () => null;

export function setTokenProvider(provider: () => string | null): void {
  getAccessToken = provider;
}

class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

async function attemptRefresh(): Promise<boolean> {
  if (isRefreshing && refreshPromise) {
    return refreshPromise;
  }

  isRefreshing = true;
  refreshPromise = (async () => {
    try {
      const res = await fetch(`${config.apiUrl}/v1/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!res.ok) return false;

      const json = await res.json();

      // Update auth store if available
      const { useAuthStore } = await import('@/features/auth/store');
      useAuthStore.getState().setFromTokenResponse(json.data);
      return true;
    } catch {
      return false;
    } finally {
      isRefreshing = false;
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  isRetry = false,
): Promise<ApiResponse<T>> {
  const url = `${config.apiUrl}${path}`;
  const token = getAccessToken();

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  logger.debug(`${method} ${url}`);

  const response = await fetch(url, {
    method,
    headers,
    credentials: 'include',
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  // Auto-refresh on 401 (once)
  if (response.status === 401 && !isRetry && !path.includes('/v1/auth/')) {
    const refreshed = await attemptRefresh();
    if (refreshed) {
      return request<T>(method, path, body, true);
    }

    // Refresh failed — clear auth and redirect
    try {
      const { useAuthStore } = await import('@/features/auth/store');
      useAuthStore.getState().clearAuth();
    } catch {
      // Store not available
    }
    window.location.href = '/login';
  }

  const json = (await response.json()) as ApiResponse<T>;

  if (!response.ok) {
    const firstError = json.errors?.[0];
    const message = firstError?.message ?? `HTTP ${response.status}`;
    const code = firstError?.code ?? String(response.status);
    logger.error(`${method} ${url} failed`, { status: response.status, code, message });
    throw new ApiError(response.status, code, message);
  }

  return json;
}

export const apiClient = {
  get<T>(path: string): Promise<ApiResponse<T>> {
    return request<T>('GET', path);
  },

  post<T>(path: string, body: unknown): Promise<ApiResponse<T>> {
    return request<T>('POST', path, body);
  },

  put<T>(path: string, body: unknown): Promise<ApiResponse<T>> {
    return request<T>('PUT', path, body);
  },

  patch<T>(path: string, body: unknown): Promise<ApiResponse<T>> {
    return request<T>('PATCH', path, body);
  },

  delete<T>(path: string): Promise<ApiResponse<T>> {
    return request<T>('DELETE', path);
  },
};

export { ApiError };
