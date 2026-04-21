import { useCallback, useRef } from 'react';
import { apiClient } from '@/shared/lib/api-client';

interface CognitiveEventPayload {
  event_type: string;
  exercise_id: string;
  payload: Record<string, unknown>;
}

function emitCognitiveEvent(data: CognitiveEventPayload): void {
  apiClient
    .post('/v1/student/cognitive-events', data)
    .catch(() => {});
}

/**
 * Tracks reading time on the problem statement.
 * Timer starts when focus is gained, emits on blur/tab-switch.
 * Skips if duration < 3000ms.
 */
export function useReadingTimeEmitter(exerciseId: string | undefined) {
  const startTimeRef = useRef<number | null>(null);
  const emittedRef = useRef(false);

  const onFocus = useCallback(() => {
    if (!exerciseId) return;
    startTimeRef.current = Date.now();
  }, [exerciseId]);

  const onBlur = useCallback(() => {
    if (!exerciseId || startTimeRef.current === null) return;
    const durationMs = Date.now() - startTimeRef.current;
    startTimeRef.current = null;

    if (durationMs < 3000) return;

    emitCognitiveEvent({
      event_type: 'problem.reading_time',
      exercise_id: exerciseId,
      payload: { duration_ms: durationMs },
    });
    emittedRef.current = true;
  }, [exerciseId]);

  return { onFocus, onBlur };
}

/**
 * Detects when a student returns to the problem statement after code activity.
 * Emits problem.reread when they re-focus the problem area after having written code.
 */
export function useRereadEmitter(exerciseId: string | undefined, hasCodeActivity: boolean) {
  const firstReadTsRef = useRef<number | null>(null);
  const codeLinesRef = useRef(0);

  const setCodeLines = useCallback((lines: number) => {
    codeLinesRef.current = lines;
  }, []);

  const onProblemView = useCallback(() => {
    if (!exerciseId) return;

    if (firstReadTsRef.current === null) {
      firstReadTsRef.current = Date.now();
      return;
    }

    if (!hasCodeActivity) return;

    const elapsedSinceFirstRead = Date.now() - firstReadTsRef.current;

    emitCognitiveEvent({
      event_type: 'problem.reread',
      exercise_id: exerciseId,
      payload: {
        elapsed_since_first_read: elapsedSinceFirstRead,
        code_lines_at_reread: codeLinesRef.current,
      },
    });
  }, [exerciseId, hasCodeActivity]);

  return { onProblemView, setCodeLines };
}

/**
 * Intercepts copy events from tutor chat code blocks.
 * Emits code.accepted_from_tutor when a student copies code from the tutor.
 */
export function useTutorClipboardEmitter(exerciseId: string | undefined) {
  const onCopyFromTutor = useCallback(
    (fragment: string, tutorMessageId: string | null) => {
      if (!exerciseId || !fragment || fragment.length < 5) return;

      emitCognitiveEvent({
        event_type: 'code.accepted_from_tutor',
        exercise_id: exerciseId,
        payload: {
          fragment_length: fragment.length,
          tutor_message_id: tutorMessageId,
          detection_method: 'clipboard',
        },
      });
    },
    [exerciseId],
  );

  return { onCopyFromTutor };
}
