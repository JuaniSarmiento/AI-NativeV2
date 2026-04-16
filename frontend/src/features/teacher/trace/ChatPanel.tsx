import { useTraceStore } from './store';
import type { ChatMessage } from './types';

const EMPTY_MESSAGES: ChatMessage[] = [];

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('es-AR', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function ChatPanel() {
  const chatMessages = useTraceStore((s) => s.chatMessages);
  const items = chatMessages.length > 0 ? chatMessages : EMPTY_MESSAGES;

  if (items.length === 0) {
    return (
      <div className="rounded-[var(--radius-lg)] border border-dashed border-[var(--color-border)] p-8 text-center">
        <p className="text-[0.875rem] text-[var(--color-text-tertiary)]">Sin mensajes del tutor.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {items.map((msg) => {
        const isUser = msg.role === 'user';
        return (
          <div
            key={msg.id}
            className={`rounded-[var(--radius-md)] px-4 py-3 ${
              isUser
                ? 'ml-6 bg-[var(--color-accent-50)] dark:bg-[var(--color-accent-900)]/10'
                : 'mr-6 border border-[var(--color-border)] bg-[var(--color-surface)]'
            }`}
          >
            <div className="mb-1 flex items-center justify-between">
              <span className="text-[0.6875rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
                {isUser ? 'Alumno' : 'Tutor'}
              </span>
              <span className="font-mono text-[0.625rem] tabular-nums text-[var(--color-text-tertiary)]">
                {formatTime(msg.created_at)}
              </span>
            </div>
            <p className="whitespace-pre-wrap text-[0.8125rem] leading-relaxed text-[var(--color-text-primary)]">
              {msg.content}
            </p>
          </div>
        );
      })}
    </div>
  );
}
