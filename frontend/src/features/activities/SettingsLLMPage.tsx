import { useEffect, useState, type FormEvent } from 'react';
import { useActivitiesStore } from './store';
import { apiClient } from '@/shared/lib/api-client';
import Button from '@/shared/components/Button';
import Input from '@/shared/components/Input';
import Card from '@/shared/components/Card';
import type { LLMProvider } from './types';

const PROVIDERS: { value: LLMProvider; label: string; placeholder: string; defaultModel: string }[] = [
  { value: 'openai', label: 'OpenAI', placeholder: 'sk-...', defaultModel: 'gpt-4o-mini' },
  { value: 'anthropic', label: 'Anthropic', placeholder: 'sk-ant-...', defaultModel: 'claude-sonnet-4-20250514' },
  { value: 'mistral', label: 'Mistral', placeholder: 'your-mistral-key', defaultModel: 'mistral-small-latest' },
  { value: 'gemini', label: 'Google Gemini', placeholder: 'tu-api-key-de-google-ai-studio', defaultModel: 'gemini-2.0-flash' },
];

export default function SettingsLLMPage() {
  const llmConfig = useActivitiesStore((s) => s.llmConfig);
  const fetchLLMConfig = useActivitiesStore((s) => s.fetchLLMConfig);
  const saveLLMConfig = useActivitiesStore((s) => s.saveLLMConfig);

  const [provider, setProvider] = useState<LLMProvider>('openai');
  const [apiKey, setApiKey] = useState('');
  const [modelName, setModelName] = useState('gpt-4o-mini');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [editing, setEditing] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<'ok' | 'fail' | null>(null);

  useEffect(() => {
    fetchLLMConfig();
  }, [fetchLLMConfig]);

  useEffect(() => {
    if (llmConfig) {
      setProvider(llmConfig.provider);
      setModelName(llmConfig.model_name);
    }
  }, [llmConfig]);

  const hasKey = llmConfig?.has_key === true;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!apiKey) return;
    setSaving(true);
    setSaved(false);
    try {
      await saveLLMConfig({ provider, api_key: apiKey, model_name: modelName });
      setApiKey('');
      setEditing(false);
      setSaved(true);
      setTestResult(null);
      setTimeout(() => setSaved(false), 4000);
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await apiClient.post<{ status: string; message?: string }>(
        '/v1/settings/llm/test',
        {},
      );
      setTestResult(res.data.status === 'ok' ? 'ok' : 'fail');
    } catch {
      setTestResult('fail');
    }
    setTimeout(() => setTestResult(null), 5000);
  }

  const currentProvider = PROVIDERS.find((p) => p.value === provider);

  return (
    <div>
      <span className="inline-block rounded-full bg-[var(--color-neutral-100)] px-3 py-1 text-[0.625rem] font-semibold uppercase tracking-[0.15em] text-[var(--color-text-secondary)] dark:bg-[var(--color-neutral-800)]">
        Configuracion
      </span>
      <h1 className="mt-3 text-[1.75rem] font-bold tracking-tight text-[var(--color-text-primary)]">
        Proveedor de IA
      </h1>
      <p className="mt-1.5 text-[0.9375rem] text-[var(--color-text-secondary)]">
        Configura tu API key para generar actividades con inteligencia artificial.
      </p>

      {/* Current status card */}
      {hasKey && !editing && (
        <Card padding="md" className="mt-8 max-w-lg animate-[slideIn_400ms_cubic-bezier(0.32,0.72,0,1)]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#EDF3EC]">
                <svg className="h-4 w-4 text-[#346538]" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                </svg>
              </span>
              <div>
                <p className="text-[0.9375rem] font-semibold text-[var(--color-text-primary)]">
                  {PROVIDERS.find((p) => p.value === llmConfig?.provider)?.label ?? llmConfig?.provider}
                </p>
                <p className="text-[0.75rem] text-[var(--color-text-tertiary)]">
                  {llmConfig?.model_name} — API key configurada
                </p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setEditing(true)}
            >
              Cambiar
            </Button>
          </div>

          {saved && (
            <div className="mt-3 rounded-[8px] bg-[#EDF3EC] px-4 py-2 text-[0.8125rem] font-medium text-[#346538] animate-[fadeIn_200ms_ease-out]">
              Configuracion guardada correctamente
            </div>
          )}

          {/* Test connection */}
          <div className="mt-4 flex items-center gap-3 border-t border-[var(--color-border)] pt-4">
            <Button
              variant="secondary"
              size="sm"
              loading={testing}
              onClick={handleTest}
            >
              Testear conexion
            </Button>
            {testResult === 'ok' && (
              <span className="text-[0.8125rem] font-medium text-[#346538] animate-[fadeIn_200ms_ease-out]">
                Conexion exitosa
              </span>
            )}
            {testResult === 'fail' && (
              <span className="text-[0.8125rem] font-medium text-[#9F2F2D] animate-[fadeIn_200ms_ease-out]">
                Error — verifica tu API key
              </span>
            )}
          </div>
        </Card>
      )}

      {/* Edit form */}
      {(!hasKey || editing) && (
        <Card padding="lg" className="mt-8 max-w-lg animate-[slideIn_400ms_cubic-bezier(0.32,0.72,0,1)]">
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Provider */}
            <div className="space-y-1.5">
              <label className="block text-[0.8125rem] font-medium text-[var(--color-text-primary)]">
                Proveedor
              </label>
              <div className="grid grid-cols-2 gap-2">
                {PROVIDERS.map((p) => (
                  <button
                    key={p.value}
                    type="button"
                    onClick={() => {
                      setProvider(p.value);
                      setModelName(p.defaultModel);
                    }}
                    className={[
                      'flex items-center justify-center rounded-[8px] border py-2.5 text-[0.8125rem] font-medium',
                      'transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] active:scale-[0.98]',
                      provider === p.value
                        ? 'border-[var(--color-neutral-900)] bg-[var(--color-neutral-900)] text-white dark:border-[var(--color-neutral-100)] dark:bg-[var(--color-neutral-100)] dark:text-[var(--color-neutral-900)]'
                        : 'border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-[var(--color-neutral-300)]',
                    ].join(' ')}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {/* API Key */}
            <Input
              label="API Key"
              type="password"
              required
              placeholder={currentProvider?.placeholder}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />

            {/* Model */}
            <Input
              label="Modelo"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              helper={
                provider === 'openai'
                  ? 'Ej: gpt-4o-mini, gpt-4o'
                  : provider === 'anthropic'
                    ? 'Ej: claude-sonnet-4-20250514, claude-haiku-4-5-20251001'
                    : provider === 'gemini'
                      ? 'Ej: gemini-2.0-flash, gemini-2.5-pro, gemini-1.5-flash'
                      : 'Ej: mistral-small-latest, mistral-medium-latest, mistral-large-latest'
              }
            />

            <div className="flex items-center gap-3 pt-2">
              <Button
                variant="primary"
                size="md"
                type="submit"
                loading={saving}
                disabled={!apiKey}
              >
                Guardar
              </Button>
              {editing && (
                <Button
                  variant="ghost"
                  size="md"
                  type="button"
                  onClick={() => { setEditing(false); setApiKey(''); }}
                >
                  Cancelar
                </Button>
              )}
            </div>
          </form>
        </Card>
      )}
    </div>
  );
}
