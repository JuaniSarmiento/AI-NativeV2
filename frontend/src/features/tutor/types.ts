export type GuardrailViolationType = 'excessive_code' | 'direct_solution' | 'non_socratic';

export interface TutorMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  isStreaming?: boolean;
  isGuardrail?: boolean;
  violationType?: GuardrailViolationType;
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting';

/** WS incoming message types (server → client) */
export type WSIncoming =
  | { type: 'connected' }
  | { type: 'chat.token'; content: string }
  | { type: 'chat.done'; interaction_id: string }
  | { type: 'chat.error'; code: string; message: string; reset_at?: string }
  | { type: 'rate_limit'; remaining: number; reset_at: string }
  | { type: 'chat.guardrail'; violation_type: GuardrailViolationType; corrective_message: string }
  | { type: 'pong' };

/** WS outgoing message types (client → server) */
export type WSOutgoing =
  | { type: 'chat.message'; content: string; exercise_id: string }
  | { type: 'ping' };
