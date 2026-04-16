export interface GovernanceEvent {
  id: string;
  event_type: string;
  actor_id: string;
  target_type: string | null;
  target_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface PromptHistory {
  id: string;
  name: string;
  version: string;
  sha256_hash: string;
  is_active: boolean;
  created_at: string;
}
