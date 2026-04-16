import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import type { DashboardData, StudentSummary, RadarDataPoint } from './types';
import { N4_LABELS } from './types';

interface N4RadarChartProps {
  dashboard: DashboardData;
  selectedStudent: StudentSummary | null;
}

function buildRadarData(
  avg: DashboardData,
  student: StudentSummary | null,
): RadarDataPoint[] {
  const dimensions = [
    { key: 'n1', avgField: 'avg_n1' as const, studentField: 'latest_n1' as const },
    { key: 'n2', avgField: 'avg_n2' as const, studentField: 'latest_n2' as const },
    { key: 'n3', avgField: 'avg_n3' as const, studentField: 'latest_n3' as const },
    { key: 'n4', avgField: 'avg_n4' as const, studentField: 'latest_n4' as const },
  ];

  return dimensions.map(({ key, avgField, studentField }) => ({
    dimension: N4_LABELS[key],
    score: avg[avgField] ?? 0,
    studentScore: student ? (student[studentField] ?? 0) : undefined,
    fullMark: 100 as const,
  }));
}

export default function N4RadarChart({ dashboard, selectedStudent }: N4RadarChartProps) {
  const data = buildRadarData(dashboard, selectedStudent);

  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
      <h3 className="mb-4 text-[0.8125rem] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-secondary)]">
        Perfil N1-N4
      </h3>
      <ResponsiveContainer width="100%" height={320}>
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="75%">
          <PolarGrid stroke="var(--color-neutral-200)" />
          <PolarAngleAxis
            dataKey="dimension"
            tick={{ fontSize: 12, fill: 'var(--color-text-secondary)' }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fontSize: 10, fill: 'var(--color-text-tertiary)' }}
          />
          <Radar
            name="Promedio comision"
            dataKey="score"
            stroke="var(--color-accent-600)"
            fill="var(--color-accent-600)"
            fillOpacity={0.15}
            strokeWidth={2}
          />
          {selectedStudent && (
            <Radar
              name="Alumno seleccionado"
              dataKey="studentScore"
              stroke="var(--color-warning-500)"
              fill="var(--color-warning-500)"
              fillOpacity={0.1}
              strokeWidth={2}
              strokeDasharray="4 4"
            />
          )}
          <Legend
            wrapperStyle={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
