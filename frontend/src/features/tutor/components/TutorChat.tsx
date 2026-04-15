import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { useShallow } from 'zustand/react/shallow';
import Card from '@/shared/components/Card';
import Button from '@/shared/components/Button';
import { useTutorStore } from '../store';
import { useWebSocketTutor } from '../hooks/useWebSocketTutor';
import ChatMessage from './ChatMessage';
import type { ConnectionStatus, TutorMessage } from '../types';

interface TutorChatProps {
  exerciseId: string;
}

const EMPTY_MESSAGES: TutorMessage[] = [];

/* Status dot color + label */
const STATUS_CONFIG: Record<ConnectionStatus, { color: string; label: string }> = {
  connecting: {
    color: 'bg-[var(--color-neutral-400)] animate-pulse',
    label: 'Conectando...',
  },
  connected: {
    color: 'bg-[#346538]',
    label: 'Conectado',
  },
  disconnected: {
    color: 'bg-[#9F2F2D]',
    label: 'Desconectado',
  },
  reconnecting: {
    color: 'bg-[#956400] animate-pulse',
    label: 'Reconectando...',
  },
};

/**
 * TutorChat — Minimal editorial chat panel.
 *
 * Double-bezel Card wrapper, clean message list, subtle input.
 * No gradients, no heavy shadows. Spring easing throughout.
 */
export default function TutorChat({ exerciseId }: TutorChatProps) {
  const messages = useTutorStore(useShallow((s) => s.messages)) ?? EMPTY_MESSAGES;
  const connectionStatus = useTutorStore((s) => s.connectionStatus);
  const isStreaming = useTutorStore((s) => s.isStreaming);
  const remainingMessages = useTutorStore((s) => s.remainingMessages);

  const { sendMessage } = useWebSocketTutor(exerciseId);

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming || connectionStatus !== 'connected') return;
    sendMessage(trimmed);
    setInput('');
  }, [input, isStreaming, connectionStatus, sendMessage]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const isDisabled =
    connectionStatus !== 'connected' || isStreaming || remainingMessages === 0;

  const status = STATUS_CONFIG[connectionStatus];

  return (
    <Card padding="sm" className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
        <div className="flex items-center gap-2.5">
          <h2 className="text-[0.8125rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
            Tutor IA
          </h2>
          <div className="flex items-center gap-1.5">
            <span className={`inline-block h-1.5 w-1.5 rounded-full ${status.color}`} />
            <span className="text-[0.6875rem] text-[var(--color-text-tertiary)]">
              {status.label}
            </span>
          </div>
        </div>
        {remainingMessages !== null && (
          <span className="text-[0.6875rem] text-[var(--color-text-tertiary)]">
            {remainingMessages} msg restantes
          </span>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 space-y-3 overflow-y-auto py-4">
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center">
            <p className="text-center text-[0.8125rem] text-[var(--color-text-tertiary)]">
              Escribile al tutor para empezar.
              <br />
              <span className="text-[0.75rem]">
                Te va a guiar sin darte la respuesta.
              </span>
            </p>
          </div>
        )}
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-[var(--color-border)] pt-3">
        {remainingMessages === 0 ? (
          <p className="text-center text-[0.8125rem] text-[var(--color-text-tertiary)]">
            Alcanzaste el limite de mensajes por hora
          </p>
        ) : (
          <div className="flex items-end gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Escribi tu pregunta..."
              disabled={isDisabled}
              rows={1}
              className={[
                'flex-1 resize-none rounded-[8px] border px-3.5 py-2.5',
                'bg-[var(--color-surface)] text-[0.875rem] text-[var(--color-text-primary)]',
                'outline-none',
                'transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]',
                'placeholder:text-[var(--color-text-tertiary)]',
                'border-[var(--color-border)]',
                'hover:border-[var(--color-neutral-300)]',
                'focus:border-[var(--color-neutral-400)] focus:ring-2 focus:ring-[var(--color-neutral-400)]/10',
                'disabled:opacity-40 disabled:pointer-events-none',
              ].join(' ')}
            />
            <Button
              size="md"
              onClick={handleSend}
              disabled={isDisabled || !input.trim()}
              icon={
                <svg
                  className="h-3.5 w-3.5"
                  viewBox="0 0 16 16"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M14.5 1.5L7 9M14.5 1.5L10 14.5L7 9M14.5 1.5L1.5 6L7 9"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              }
            >
              Enviar
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}
