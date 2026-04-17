export type ActivityStatus = 'draft' | 'published';
export type LLMProvider = 'openai' | 'anthropic' | 'mistral' | 'gemini';

export interface Activity {
  id: string;
  course_id: string;
  created_by: string;
  title: string;
  description: string | null;
  prompt_used: string | null;
  status: ActivityStatus;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  exercises?: import('@/features/exercises/types').Exercise[];
}

export interface LLMConfig {
  provider: LLMProvider;
  model_name: string;
  has_key: boolean;
}

export interface LLMConfigSaveData {
  provider: LLMProvider;
  api_key: string;
  model_name: string;
}
