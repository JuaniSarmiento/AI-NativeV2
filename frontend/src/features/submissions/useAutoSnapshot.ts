import { useEffect, useRef, useCallback } from 'react';
import { apiClient } from '@/shared/lib/api-client';

const SNAPSHOT_INTERVAL_MS = 30_000;

/**
 * Auto-saves code snapshots every 30s if the code changed.
 * Also exposes `saveNow()` to save before execution.
 */
export function useAutoSnapshot(exerciseId: string | undefined, code: string) {
  const lastSavedCode = useRef<string>('');
  const exerciseIdRef = useRef(exerciseId);
  exerciseIdRef.current = exerciseId;

  const saveSnapshot = useCallback(async (codeToSave: string) => {
    if (!exerciseIdRef.current || !codeToSave.trim()) return;
    if (codeToSave === lastSavedCode.current) return;

    try {
      await apiClient.post(`/v1/student/exercises/${exerciseIdRef.current}/snapshot`, {
        code: codeToSave,
      });
      lastSavedCode.current = codeToSave;
    } catch {
      // Fire-and-forget — don't block the student
    }
  }, []);

  // Auto-save interval
  useEffect(() => {
    if (!exerciseId) return;

    const interval = setInterval(() => {
      saveSnapshot(code);
    }, SNAPSHOT_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [exerciseId, code, saveSnapshot]);

  // Save now (before execution)
  const saveNow = useCallback(() => {
    saveSnapshot(code);
  }, [code, saveSnapshot]);

  return { saveNow };
}
