import { useTraceStore } from './store';
import type { CodeSnapshot } from './types';

const EMPTY_SNAPSHOTS: CodeSnapshot[] = [];

function computeDiff(oldCode: string, newCode: string): { type: 'same' | 'add' | 'del'; text: string }[] {
  const oldLines = oldCode.split('\n');
  const newLines = newCode.split('\n');
  const result: { type: 'same' | 'add' | 'del'; text: string }[] = [];

  const maxLen = Math.max(oldLines.length, newLines.length);
  for (let i = 0; i < maxLen; i++) {
    const o = oldLines[i];
    const n = newLines[i];
    if (o === undefined) {
      result.push({ type: 'add', text: n });
    } else if (n === undefined) {
      result.push({ type: 'del', text: o });
    } else if (o === n) {
      result.push({ type: 'same', text: n });
    } else {
      result.push({ type: 'del', text: o });
      result.push({ type: 'add', text: n });
    }
  }
  return result;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('es-AR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

const LINE_CLASSES = {
  same: 'text-[var(--color-text-secondary)]',
  add: 'bg-[var(--color-success-50)] text-[var(--color-success-700)] dark:bg-[var(--color-success-900)]/20 dark:text-[var(--color-success-400)]',
  del: 'bg-[var(--color-error-50)] text-[var(--color-error-700)] dark:bg-[var(--color-error-900)]/20 dark:text-[var(--color-error-400)]',
};

const PREFIX = { same: ' ', add: '+', del: '-' };

export default function CodeEvolutionPanel() {
  const snapshots = useTraceStore((s) => s.snapshots);
  const items = snapshots.length > 0 ? snapshots : EMPTY_SNAPSHOTS;

  if (items.length === 0) {
    return (
      <div className="rounded-[var(--radius-lg)] border border-dashed border-[var(--color-border)] p-8 text-center">
        <p className="text-[0.875rem] text-[var(--color-text-tertiary)]">Sin snapshots de codigo.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {items.map((snap, idx) => {
        const prev = idx > 0 ? items[idx - 1] : null;
        const diff = prev ? computeDiff(prev.code, snap.code) : null;

        return (
          <div
            key={snap.snapshot_id ?? idx}
            className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)]"
          >
            <div className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-2">
              <span className="text-[0.75rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
                Snapshot #{idx + 1}
              </span>
              <span className="font-mono text-[0.6875rem] tabular-nums text-[var(--color-text-tertiary)]">
                {formatTime(snap.snapshot_at)}
              </span>
            </div>
            <div className="max-h-[300px] overflow-auto p-4">
              {diff ? (
                <pre className="font-mono text-[0.75rem] leading-relaxed">
                  {diff.map((line, li) => (
                    <div key={li} className={`${LINE_CLASSES[line.type]} px-1`}>
                      <span className="mr-2 select-none opacity-50">{PREFIX[line.type]}</span>
                      {line.text}
                    </div>
                  ))}
                </pre>
              ) : (
                <pre className="font-mono text-[0.75rem] leading-relaxed text-[var(--color-text-primary)]">
                  {snap.code}
                </pre>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
