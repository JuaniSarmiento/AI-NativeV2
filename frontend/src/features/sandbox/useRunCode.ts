import { useState, useCallback } from 'react';
import { apiClient } from '@/shared/lib/api-client';
import type { RunResult } from './types';

export function useRunCode() {
  const [result, setResult] = useState<RunResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (exerciseId: string, code: string, stdin?: string) => {
    setIsRunning(true);
    setError(null);
    setResult(null);
    try {
      const res = await apiClient.post<RunResult>(
        `/v1/student/exercises/${exerciseId}/run`,
        { code, stdin: stdin || undefined },
      );
      setResult(res.data);
    } catch (err: any) {
      setError(err?.message || 'Error al ejecutar el codigo.');
    } finally {
      setIsRunning(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { result, isRunning, error, run, reset };
}
