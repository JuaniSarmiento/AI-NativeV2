import { useCallback } from 'react';
import type { TutorMessage } from '../types';

interface ChatMessageProps {
  message: TutorMessage;
  onCopyFromTutor?: (fragment: string, messageId: string | null) => void;
}

/**
 * ChatMessage — Minimal, editorial chat bubble.
 *
 * - Alumno: right-aligned, neutral-900 bg (dark on light)
 * - Tutor: left-aligned, surface-alt bg (subtle, recessive)
 * - Guardrail: left-aligned, amber left border, subtle bg — pedagogical note
 * - Streaming: blinking cursor at end
 * - No heavy borders, no gradients — just background differentiation
 * - Spring easing on entry
 */
export default function ChatMessage({ message, onCopyFromTutor }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const isGuardrail = message.isGuardrail === true;

  const handleCopy = useCallback(() => {
    if (isUser || !onCopyFromTutor) return;
    const selection = window.getSelection()?.toString() ?? '';
    if (selection.length >= 5) {
      onCopyFromTutor(selection, message.id ?? null);
    }
  }, [isUser, onCopyFromTutor, message.id]);

  if (isGuardrail) {
    return (
      <div className="flex w-full justify-start">
        <div
          className={[
            'max-w-[80%] rounded-r-[10px] border-l-2 border-amber-400 px-3.5 py-2.5',
            'text-[0.875rem] leading-relaxed',
            'animate-[fadeSlideIn_300ms_cubic-bezier(0.32,0.72,0,1)_both]',
            'bg-amber-50/60 text-[var(--color-text-primary)]',
            'dark:bg-amber-950/30',
          ].join(' ')}
        >
          <span className="mb-1 block text-[0.6875rem] font-medium tracking-wide text-amber-600 dark:text-amber-400">
            Nota pedagogica
          </span>
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
          <time className="mt-1 block text-[0.6875rem] text-[var(--color-text-tertiary)]">
            {new Date(message.timestamp).toLocaleTimeString('es-AR', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </time>
        </div>
      </div>
    );
  }

  return (
    <div
      className={[
        'flex w-full',
        isUser ? 'justify-end' : 'justify-start',
      ].join(' ')}
    >
      <div
        className={[
          'max-w-[80%] rounded-[10px] px-3.5 py-2.5',
          'text-[0.875rem] leading-relaxed',
          'animate-[fadeSlideIn_300ms_cubic-bezier(0.32,0.72,0,1)_both]',
          isUser
            ? 'bg-[var(--color-neutral-900)] text-white dark:bg-[var(--color-neutral-200)] dark:text-[var(--color-neutral-900)]'
            : 'bg-[var(--color-neutral-100)] text-[var(--color-text-primary)] dark:bg-[var(--color-neutral-800)]',
        ].join(' ')}
        onCopy={handleCopy}
      >
        <p className="whitespace-pre-wrap break-words">
          {message.content}
          {message.isStreaming && (
            <span className="ml-0.5 inline-block h-[1em] w-[2px] animate-pulse bg-current align-text-bottom" />
          )}
        </p>

        <time
          className={[
            'mt-1 block text-[0.6875rem]',
            isUser
              ? 'text-white/50 dark:text-[var(--color-neutral-900)]/50'
              : 'text-[var(--color-text-tertiary)]',
          ].join(' ')}
        >
          {new Date(message.timestamp).toLocaleTimeString('es-AR', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </time>
      </div>
    </div>
  );
}
