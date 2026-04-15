import { useCallback, useEffect, useRef } from 'react';
import { config } from '@/config';
import { createLogger } from '@/shared/lib/logger';
import { useAuthStore } from '@/features/auth/store';
import { useTutorStore } from '../store';
import type { WSIncoming, WSOutgoing } from '../types';

const logger = createLogger('ws-tutor');

const HEARTBEAT_INTERVAL_MS = 30_000;
const MAX_BACKOFF_MS = 30_000;
const INITIAL_BACKOFF_MS = 1_000;

export function useWebSocketTutor(exerciseId: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(INITIAL_BACKOFF_MS);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  // --- Connection lifecycle effect ---
  useEffect(() => {
    mountedRef.current = true;

    function connect() {
      const token = useAuthStore.getState().accessToken;
      if (!token) {
        logger.warn('No access token — skipping WS connection');
        return;
      }

      useTutorStore.getState().setConnectionStatus('connecting');
      useTutorStore.getState().setExerciseId(exerciseId);

      const url = `${config.wsUrl}/ws/tutor/chat?token=${token}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        logger.info('WebSocket connected');
        backoffRef.current = INITIAL_BACKOFF_MS;

        // Start heartbeat
        heartbeatRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, HEARTBEAT_INTERVAL_MS);
      };

      ws.onclose = (event) => {
        logger.info('WebSocket closed', { code: event.code, reason: event.reason });
        cleanup();

        if (!mountedRef.current) return;

        if (event.code === 4401 || event.code === 4403) {
          useTutorStore.getState().setConnectionStatus('disconnected');
          return;
        }

        // Reconnect with backoff
        useTutorStore.getState().setConnectionStatus('reconnecting');
        const delay = backoffRef.current;
        backoffRef.current = Math.min(delay * 2, MAX_BACKOFF_MS);
        logger.info('Reconnecting', { delay });
        reconnectRef.current = setTimeout(connect, delay);
      };

      ws.onerror = () => {
        logger.error('WebSocket error');
      };
    }

    function cleanup() {
      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current);
        heartbeatRef.current = null;
      }
    }

    connect();

    return () => {
      mountedRef.current = false;
      cleanup();
      if (reconnectRef.current) {
        clearTimeout(reconnectRef.current);
        reconnectRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
      useTutorStore.getState().setConnectionStatus('disconnected');
    };
  }, [exerciseId]);

  // --- Message handling effect ---
  useEffect(() => {
    const ws = wsRef.current;
    if (!ws) return;

    function handleMessage(event: MessageEvent) {
      let data: WSIncoming;
      try {
        data = JSON.parse(event.data as string) as WSIncoming;
      } catch {
        logger.error('Failed to parse WS message');
        return;
      }

      const store = useTutorStore.getState();

      switch (data.type) {
        case 'connected':
          store.setConnectionStatus('connected');
          break;

        case 'chat.token':
          store.appendToLastMessage(data.content);
          break;

        case 'chat.done':
          store.finishStreaming(data.interaction_id);
          break;

        case 'chat.error':
          store.setStreaming(false);
          logger.warn('Chat error', { code: data.code, message: data.message });
          if (data.code === 'RATE_LIMITED' && data.reset_at) {
            store.setRateLimit(0, data.reset_at);
          }
          break;

        case 'rate_limit':
          store.setRateLimit(data.remaining, data.reset_at);
          break;

        case 'chat.guardrail':
          store.addMessage({
            id: `guardrail-${Date.now()}`,
            role: 'assistant',
            content: data.corrective_message,
            timestamp: new Date().toISOString(),
            isGuardrail: true,
            violationType: data.violation_type,
          });
          break;

        case 'pong':
          break;
      }
    }

    ws.onmessage = handleMessage;

    return () => {
      if (ws) ws.onmessage = null;
    };
  });

  // --- Public API ---
  const sendMessage = useCallback(
    (content: string) => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        logger.warn('Cannot send — WS not open');
        return;
      }

      const store = useTutorStore.getState();

      // Add user message to store
      store.addMessage({
        id: `temp-${Date.now()}`,
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      });

      // Add placeholder assistant message for streaming
      store.addMessage({
        id: `streaming-${Date.now()}`,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        isStreaming: true,
      });

      store.setStreaming(true);

      const msg: WSOutgoing = {
        type: 'chat.message',
        content,
        exercise_id: exerciseId,
      };
      ws.send(JSON.stringify(msg));
    },
    [exerciseId],
  );

  return { sendMessage };
}
