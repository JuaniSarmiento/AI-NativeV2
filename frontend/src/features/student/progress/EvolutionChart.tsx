import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { ProgressSession } from './types';

interface EvolutionChartProps {
  sessions: ProgressSession[];
}

const LINE_CONFIG = [
  { key: 'n1_comprehension_score', name: 'Comprension', color: 'var(--color-accent-500)' },
  { key: 'n2_strategy_score', name: 'Estrategia', color: 'var(--color-success-500)' },
  { key: 'n3_validation_score', name: 'Validacion', color: 'var(--color-warning-500)' },
  { key: 'n4_ai_interaction_score', name: 'Interaccion IA', color: 'var(--color-error-400)' },
] as const;

function formatDate(iso: string | null): string {
  if (!iso) return '-';
  const d = new Date(iso);
  return `${d.getDate()}/${d.getMonth() + 1}`;
}

export default function EvolutionChart({ sessions }: EvolutionChartProps) {
  const data = sessions.map((s) => ({
    date: formatDate(s.computed_at),
    n1_comprehension_score: s.n1_comprehension_score,
    n2_strategy_score: s.n2_strategy_score,
    n3_validation_score: s.n3_validation_score,
    n4_ai_interaction_score: s.n4_ai_interaction_score,
  }));

  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
      <h3 className="mb-4 text-[0.8125rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-secondary)]">
        Evolucion N1-N4
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-neutral-200)" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: 'var(--color-text-tertiary)' }}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fontSize: 11, fill: 'var(--color-text-tertiary)' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.75rem',
            }}
          />
          <Legend wrapperStyle={{ fontSize: '0.75rem' }} />
          {LINE_CONFIG.map(({ key, name, color }) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              name={name}
              stroke={color}
              strokeWidth={2}
              dot={{ r: 3 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
