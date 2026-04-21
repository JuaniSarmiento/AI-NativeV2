import { useCallback, useEffect, useRef } from 'react';

interface SubstantialChangeConfig {
  /** Minimum lines-changed delta to trigger a snapshot (default: 10) */
  lineThreshold: number;
  /** Minimum elapsed ms since last snapshot to trigger time-based snapshot (default: 180000 = 3 min) */
  timeThresholdMs: number;
  /** Minimum ms between any two auto snapshot emissions (default: 30000 = 30s) */
  debounceMs: number;
}

export interface AutoSnapshotPayload {
  trigger: 'lines_changed' | 'time_elapsed';
  lines_changed?: number;
  elapsed_ms?: number;
  code: string;
}

const DEFAULT_CONFIG: SubstantialChangeConfig = {
  lineThreshold: 10,
  timeThresholdMs: 180_000,
  debounceMs: 30_000,
};

/**
 * Monitors editor content and calls `onAutoSnapshot` when substantial change
 * thresholds are met. Debounced to prevent rapid-fire emissions.
 *
 * Triggers:
 * - `lines_changed`: absolute line count delta exceeds `lineThreshold`
 * - `time_elapsed`: code changed and `timeThresholdMs` has passed since last snapshot
 */
export function useSubstantialChangeDetector(
  currentCode: string,
  onAutoSnapshot: (payload: AutoSnapshotPayload) => void,
  config: Partial<SubstantialChangeConfig> = {},
): void {
  const { lineThreshold, timeThresholdMs, debounceMs } = { ...DEFAULT_CONFIG, ...config };

  const lastSnapshotCodeRef = useRef<string>(currentCode);
  const lastSnapshotTimeRef = useRef<number>(Date.now());
  const lastEmitTimeRef = useRef<number>(0);

  const checkAndEmit = useCallback(() => {
    const now = Date.now();

    // Debounce: don't emit more than once per debounceMs
    if (now - lastEmitTimeRef.current < debounceMs) return;

    const prevLines = lastSnapshotCodeRef.current.split('\n').length;
    const currLines = currentCode.split('\n').length;
    const linesChanged = Math.abs(currLines - prevLines);
    const elapsed = now - lastSnapshotTimeRef.current;

    // Line threshold check
    if (linesChanged > lineThreshold) {
      onAutoSnapshot({
        trigger: 'lines_changed',
        lines_changed: linesChanged,
        code: currentCode,
      });
      lastSnapshotCodeRef.current = currentCode;
      lastSnapshotTimeRef.current = now;
      lastEmitTimeRef.current = now;
      return;
    }

    // Time threshold check — only if code actually changed
    if (elapsed > timeThresholdMs && currentCode !== lastSnapshotCodeRef.current) {
      onAutoSnapshot({
        trigger: 'time_elapsed',
        elapsed_ms: elapsed,
        code: currentCode,
      });
      lastSnapshotCodeRef.current = currentCode;
      lastSnapshotTimeRef.current = now;
      lastEmitTimeRef.current = now;
    }
  }, [currentCode, onAutoSnapshot, lineThreshold, timeThresholdMs, debounceMs]);

  // Check on every code change
  useEffect(() => {
    checkAndEmit();
  }, [checkAndEmit]);

  // Periodic check to catch time-based threshold between keystrokes
  useEffect(() => {
    const interval = setInterval(checkAndEmit, 30_000);
    return () => clearInterval(interval);
  }, [checkAndEmit]);
}
